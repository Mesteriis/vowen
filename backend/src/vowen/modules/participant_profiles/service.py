from copy import deepcopy
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from vowen.core.errors import AppError
from vowen.modules.identity.models import User, UserPreferences
from vowen.modules.participant_profiles.models import (
    LINK_TABLES,
    LINK_TARGETS,
    PracticePreference,
    Profile,
    ProfileDraft,
    ProfileSectionReader,
)
from vowen.modules.participant_profiles.policy import direct_partners, direct_relationships
from vowen.modules.participant_profiles.schemas import (
    IdentitySection,
    ProfileDocument,
    ProfileDraftPatch,
    ProfileDraftView,
    ProfileProgress,
    ProfilePublish,
    ProfileView,
    SharedProfileView,
)
from vowen.modules.references import models as refs

REF_MODELS = {
    model.__tablename__: model
    for model in (
        refs.BiologicalSex,
        refs.Gender,
        refs.Practice,
        refs.Device,
        refs.BodyPart,
        refs.Material,
        refs.RoleScenario,
        refs.Venue,
        refs.HealthCondition,
        refs.Allergen,
        refs.RelationshipType,
        refs.ParticipantComposition,
        refs.InteractionFormat,
    )
}


def section_for(key: str) -> str:
    if key in ("biological_sex_uid", "gender_uid"):
        return "identity"
    if key in (
        "sex_preference",
        "gender_preference",
        "relationship_type_uids",
        "composition_uids",
        "interaction_format_uids",
    ):
        return "dynamics"
    if key in ("condition_uids", "allergen_uids", "care_practice_uids"):
        return "health"
    return "preferences"


def selections(document: dict, key: str) -> list[dict]:
    value = document[section_for(key)][key]
    if key in ("biological_sex_uid", "gender_uid"):
        return [{"uid": value}] if value else []
    if key in ("sex_preference", "gender_preference"):
        return [{"uid": uid} for uid in value["uids"]]
    if key.endswith("_uids"):
        return [{"uid": uid} for uid in value]
    return value


async def locked_account(db: AsyncSession, owner: UUID) -> tuple[User, UserPreferences, Profile]:
    user = await db.scalar(select(User).where(User.id == owner).with_for_update())
    if user is None or not user.is_active:
        raise AppError(401, "INVALID_AUTH")
    prefs = await db.get(UserPreferences, owner, with_for_update=True)
    if prefs is None:
        raise AppError(503, "UNAVAILABLE")
    profile = await db.get(Profile, owner)
    if profile is None:
        profile = Profile(user_id=owner)
        db.add(profile)
        await db.flush()
    return user, prefs, profile


async def published_document(
    db: AsyncSession, user: User, prefs: UserPreferences, profile: Profile
) -> ProfileDocument:
    document = ProfileDocument(identity=IdentitySection(display_name=user.display_name)).model_dump(
        mode="json"
    )
    document.update(deepcopy(profile.content))
    document["identity"]["display_name"] = user.display_name
    document["dynamics"]["profile_labels"] = prefs.profile_labels
    for key, table in LINK_TABLES.items():
        rows = (
            (
                await db.execute(
                    select(table).where(table.c.owner_id == user.id).order_by(table.c.uid)
                )
            )
            .mappings()
            .all()
        )
        section = document[section_for(key)]
        if key in ("biological_sex_uid", "gender_uid"):
            section[key] = str(rows[0]["uid"]) if rows else None
        elif key in ("sex_preference", "gender_preference"):
            section[key]["uids"] = [str(row["uid"]) for row in rows]
        elif key.endswith("_uids"):
            section[key] = [str(row["uid"]) for row in rows]
        else:
            section[key] = [{"uid": str(row["uid"]), **row["attributes"]} for row in rows]
    document["preferences"]["practices"] = [
        {
            "practice_uid": str(row.practice_uid),
            "attitude": row.attitude,
            "experience": row.experience,
            "participation": row.participation,
            "conditions": row.conditions,
        }
        for row in await db.scalars(
            select(PracticePreference)
            .where(PracticePreference.owner_id == user.id)
            .order_by(PracticePreference.practice_uid)
        )
    ]
    document["visibility"]["sections"] = []
    readers: dict[str, list[str]] = {}
    for row in await db.scalars(
        select(ProfileSectionReader).where(ProfileSectionReader.owner_id == user.id)
    ):
        readers.setdefault(row.section, []).append(str(row.reader_id))
    document["visibility"]["sections"] = [
        {"section": key, "reader_ids": values} for key, values in readers.items()
    ]
    return ProfileDocument.model_validate(document)


async def get_own_profile(db: AsyncSession, owner_id: UUID) -> ProfileView:
    user, prefs, profile = await locked_account(db, owner_id)
    draft = await db.get(ProfileDraft, owner_id)
    return ProfileView(
        document=await published_document(db, user, prefs, profile),
        version=profile.version,
        account_version=prefs.profile_version,
        progress=ProfileProgress(
            step=draft.step if draft else profile.step,
            deferred=draft.deferred if draft else profile.deferred,
            completed=profile.completed,
        ),
        draft_version=draft.version if draft else None,
    )


def draft_view(draft: ProfileDraft) -> ProfileDraftView:
    return ProfileDraftView.model_validate(draft, from_attributes=True)


async def validate_document(
    db: AsyncSession, owner: UUID, document: ProfileDocument, check_readers: bool = True
) -> None:
    value = document.model_dump(mode="json")
    checks = [
        (key, [row["uid"] for row in selections(value, key)], REF_MODELS[target])
        for key, target in LINK_TARGETS.items()
    ]
    checks.append(
        (
            "practices",
            [row["practice_uid"] for row in value["preferences"]["practices"]],
            refs.Practice,
        )
    )
    if len(set(document.dynamics.profile_labels)) != len(document.dynamics.profile_labels):
        raise AppError(422, "INVALID_INPUT")
    for _, values, model in checks:
        ids = [UUID(uid) for uid in values]
        if len(set(ids)) != len(ids):
            raise AppError(422, "INVALID_INPUT")
        if ids and set(await db.scalars(select(model.uid).where(model.uid.in_(ids)))) != set(ids):
            raise AppError(422, "INVALID_INPUT")
    if not check_readers:
        return
    allowed = await direct_partners(db, owner, lock=True)
    sections = document.visibility.sections
    if len({s.section for s in sections}) != len(sections):
        raise AppError(422, "INVALID_INPUT")
    for item in sections:
        if len(set(item.reader_ids)) != len(item.reader_ids) or not set(item.reader_ids) <= allowed:
            raise AppError(422, "INVALID_INPUT")


async def save_draft(
    db: AsyncSession, owner_id: UUID, patch: ProfileDraftPatch
) -> ProfileDraftView:
    user, prefs, profile = await locked_account(db, owner_id)
    draft = await db.get(ProfileDraft, owner_id)
    if patch.expected_version != (draft.version if draft else 0):
        raise AppError(409, "CONFLICT")
    document = (
        deepcopy(draft.document)
        if draft
        else (await published_document(db, user, prefs, profile)).model_dump(mode="json")
    )
    if patch.section is not None:
        assert patch.value is not None
        document[patch.section] = {**document[patch.section], **patch.value}
    try:
        parsed = ProfileDocument.model_validate(document)
    except ValidationError:
        raise AppError(422, "INVALID_INPUT") from None
    await validate_document(db, owner_id, parsed, check_readers=patch.section == "visibility")
    profile.draft_sequence += 1
    if draft is None:
        draft = ProfileDraft(
            user_id=owner_id,
            base_profile_version=profile.version,
            base_account_version=prefs.profile_version,
        )
        db.add(draft)
    if patch.section == "visibility":
        draft.visibility_edited = True
    draft.document = parsed.model_dump(mode="json")
    draft.version = profile.draft_sequence
    draft.step, draft.deferred = patch.step, patch.deferred
    await db.flush()
    return draft_view(draft)


async def discard_draft(db: AsyncSession, owner_id: UUID, expected_version: int) -> None:
    await locked_account(db, owner_id)
    draft = await db.get(ProfileDraft, owner_id)
    if draft is None or draft.version != expected_version:
        raise AppError(409, "CONFLICT")
    await db.delete(draft)


async def publish_draft(db: AsyncSession, owner_id: UUID, data: ProfilePublish) -> ProfileView:
    user, prefs, profile = await locked_account(db, owner_id)
    draft = await db.get(ProfileDraft, owner_id)
    if (
        draft is None
        or draft.version != data.expected_draft_version
        or draft.base_profile_version != profile.version
        or draft.base_account_version != prefs.profile_version
    ):
        raise AppError(409, "CONFLICT")
    document = ProfileDocument.model_validate(draft.document)
    await validate_document(db, owner_id, document)
    active_relations = await direct_relationships(db, owner_id, lock=True)
    previous = {
        (row.section, row.reader_id): row.relation_id
        for row in await db.scalars(
            select(ProfileSectionReader).where(ProfileSectionReader.owner_id == owner_id)
        )
    }
    grant_relations: dict[tuple[str, UUID], UUID] = {}
    for grant in document.visibility.sections:
        for reader in grant.reader_ids:
            old = previous.get((grant.section, reader))
            if not draft.visibility_edited and old not in active_relations.get(reader, set()):
                raise AppError(422, "INVALID_INPUT")
            grant_relations[(grant.section, reader)] = (
                old
                if old in active_relations[reader]
                else sorted(active_relations[reader], key=str)[0]
            )
    content = document.model_dump(mode="json")
    if (
        user.display_name != document.identity.display_name
        or prefs.profile_labels != document.dynamics.profile_labels
    ):
        user.display_name = document.identity.display_name
        prefs.profile_labels = list(document.dynamics.profile_labels)
        prefs.profile_version += 1
    content["identity"].pop("display_name")
    content["dynamics"].pop("profile_labels")
    for key, table in LINK_TABLES.items():
        await db.execute(delete(table).where(table.c.owner_id == owner_id))
        rows = selections(document.model_dump(mode="json"), key)
        if rows:
            await db.execute(
                insert(table),
                [
                    {
                        "owner_id": owner_id,
                        "uid": UUID(row["uid"]),
                        "attributes": {k: v for k, v in row.items() if k != "uid"},
                    }
                    for row in rows
                ],
            )
        section = content[section_for(key)]
        if key in ("sex_preference", "gender_preference"):
            section[key]["uids"] = []
        else:
            section.pop(key)
    await db.execute(delete(PracticePreference).where(PracticePreference.owner_id == owner_id))
    for item in document.preferences.practices:
        db.add(PracticePreference(owner_id=owner_id, **item.model_dump()))
    content["preferences"].pop("practices")
    await db.execute(delete(ProfileSectionReader).where(ProfileSectionReader.owner_id == owner_id))
    for visibility_item in document.visibility.sections:
        for reader in visibility_item.reader_ids:
            db.add(
                ProfileSectionReader(
                    owner_id=owner_id,
                    section=visibility_item.section,
                    reader_id=reader,
                    relation_id=grant_relations[(visibility_item.section, reader)],
                )
            )
    content["visibility"] = {"sections": []}
    profile.content, profile.version, profile.completed = content, profile.version + 1, True
    profile.step, profile.deferred = 6, False
    await db.delete(draft)
    await db.flush()
    return await get_own_profile(db, owner_id)


async def read_shared_profile(
    db: AsyncSession, viewer_id: UUID, owner_id: UUID
) -> SharedProfileView:
    active = await direct_relationships(db, owner_id)
    if viewer_id not in active:
        raise AppError(404, "NOT_FOUND")
    sections = list(
        await db.scalars(
            select(ProfileSectionReader.section).where(
                ProfileSectionReader.owner_id == owner_id,
                ProfileSectionReader.reader_id == viewer_id,
                ProfileSectionReader.relation_id.in_(active[viewer_id]),
            )
        )
    )
    profile, user, prefs = (
        await db.get(Profile, owner_id),
        await db.get(User, owner_id),
        await db.get(UserPreferences, owner_id),
    )
    if not sections or profile is None or user is None or prefs is None:
        raise AppError(404, "NOT_FOUND")
    document = (await published_document(db, user, prefs, profile)).model_dump(mode="json")
    shared = {key: document[key] for key in sections}
    if "boundaries" in shared:
        shared["boundaries"]["practices"] = [
            {key: row[key] for key in ("practice_uid", "attitude", "conditions")}
            for row in document["preferences"]["practices"]
            if row["attitude"] in ("taboo", "conditional")
        ]
    return SharedProfileView(owner_id=owner_id, sections=shared)
