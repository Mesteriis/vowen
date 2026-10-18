from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, JsonValue, field_validator, model_validator

from vowen.modules.auth.schemas import Input
from vowen.modules.identity.schemas import ProfileLabel

Section = Literal["identity", "dynamics", "preferences", "boundaries", "health", "visibility"]
Attitude = Literal["not_specified", "like", "want_to_try", "conditional", "taboo"]
UidList = Annotated[list[UUID], Field(max_length=500)]


class IdentitySection(Input):
    display_name: str = Field(min_length=1, max_length=100)
    bio: str = Field(default="", max_length=2000)
    biological_sex_uid: UUID | None = None
    gender_uid: UUID | None = None

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Empty name")
        return value.strip()


class PartnerPreference(Input):
    mode: Literal["not_specified", "any", "selected"] = "not_specified"
    uids: UidList = Field(default_factory=list)

    @model_validator(mode="after")
    def selected_values(self) -> "PartnerPreference":
        if (self.mode == "selected") != bool(self.uids):
            raise ValueError("Selected mode requires values; other modes require none")
        return self


class DynamicsSection(Input):
    profile_labels: list[ProfileLabel] = Field(default_factory=list, max_length=3)
    sex_preference: PartnerPreference = Field(default_factory=PartnerPreference)
    gender_preference: PartnerPreference = Field(default_factory=PartnerPreference)
    relationship_type_uids: UidList = Field(default_factory=list)
    composition_uids: UidList = Field(default_factory=list)
    interaction_format_uids: UidList = Field(default_factory=list)


class PracticeChoice(Input):
    practice_uid: UUID
    attitude: Attitude = "not_specified"
    experience: Literal["not_specified", "none", "tried", "experienced"] = "not_specified"
    participation: Literal["not_specified", "give", "receive", "both"] = "not_specified"
    conditions: str = Field(default="", max_length=2000)


class ReferenceChoice(Input):
    uid: UUID
    attitude: Attitude = "not_specified"
    conditions: str = Field(default="", max_length=2000)


class PreferencesSection(Input):
    practices: list[PracticeChoice] = Field(default_factory=list, max_length=500)
    devices: list[ReferenceChoice] = Field(default_factory=list, max_length=500)
    body_parts: list[ReferenceChoice] = Field(default_factory=list, max_length=500)
    materials: list[ReferenceChoice] = Field(default_factory=list, max_length=500)
    role_scenarios: list[ReferenceChoice] = Field(default_factory=list, max_length=500)
    venues: list[ReferenceChoice] = Field(default_factory=list, max_length=500)


class BoundariesSection(Input):
    notes: str = Field(default="", max_length=4000)


class HealthSection(Input):
    condition_uids: UidList = Field(default_factory=list)
    allergen_uids: UidList = Field(default_factory=list)
    care_practice_uids: UidList = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)


class SectionReaders(Input):
    section: Literal["identity", "dynamics", "preferences", "boundaries", "health"]
    reader_ids: UidList = Field(default_factory=list)


class VisibilitySection(Input):
    sections: list[SectionReaders] = Field(default_factory=list, max_length=5)


class ProfileDocument(Input):
    identity: IdentitySection
    dynamics: DynamicsSection = Field(default_factory=DynamicsSection)
    preferences: PreferencesSection = Field(default_factory=PreferencesSection)
    boundaries: BoundariesSection = Field(default_factory=BoundariesSection)
    health: HealthSection = Field(default_factory=HealthSection)
    visibility: VisibilitySection = Field(default_factory=VisibilitySection)


class ProfileProgress(Input):
    step: int = Field(ge=1, le=6)
    deferred: bool
    completed: bool


class ProfileView(Input):
    document: ProfileDocument
    version: int
    account_version: int
    progress: ProfileProgress
    draft_version: int | None


class ProfileDraftView(Input):
    document: ProfileDocument
    version: int
    base_profile_version: int
    base_account_version: int
    step: int
    deferred: bool


class ProfileDraftPatch(Input):
    expected_version: int = Field(ge=0)
    section: Section | None = None
    value: dict[str, JsonValue] | None = None
    step: int = Field(ge=1, le=6)
    deferred: bool = False

    @model_validator(mode="after")
    def paired(self) -> "ProfileDraftPatch":
        if (self.section is None) != (self.value is None):
            raise ValueError("Section and value must be supplied together")
        return self


class ProfilePublish(Input):
    expected_draft_version: int = Field(ge=1)


class SharedProfileView(Input):
    owner_id: UUID
    sections: dict[str, JsonValue]
