"""Rebuild a guarded local debug space from repository fixtures, without Telegram delivery."""

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from vowen.core.config import Settings
from vowen.core.crypto import PayloadCipher, init_keyring
from vowen.main import create_app
from vowen.modules.identity.models import User, UserPreferences
from vowen.modules.identity.service import ProvisionUserCommand, create_user
from vowen.modules.references.fixtures import CATALOGUES, fixture_rows, seed_references
from vowen.modules.rewards import economy

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "scripts/fixtures/debug-space.json"
SCOPES = [
    "rules.assign",
    "rituals.assign",
    "rituals.review",
    "discipline.propose",
    "discipline.review",
    "rewards.grant",
]


def validate_reset(url: str, users: list[tuple[int, str]]) -> None:
    """Allow only the exact legacy/generated identities on a loopback disposable database."""
    target = make_url(url)
    if target.host not in {"127.0.0.1", "localhost", "::1"} or not (
        target.database and target.database.endswith("_test")
    ):
        raise ValueError("Debug fixtures require a local database ending in _test")
    allowed = {100000000201 + i: {f"Demo {i + 1}"} for i in range(12)}
    for number, names in {
        201: {"Алекс · демо", "Алекс"},
        202: {"Луна · демо", "Вика"},
        203: {"Саша · демо", "Луна"},
        204: {"Марк · демо"},
    }.items():
        allowed[100000000000 + number].update(names)
    if any(name not in allowed.get(tid, set()) for tid, name in users):
        raise ValueError("Reset refused: unrecognized users exist; no data was deleted")


class Scenario:
    def __init__(self, app: FastAPI, client: httpx.AsyncClient, data: dict[str, Any]):
        self.app, self.client, self.data = app, client, data
        self.users: dict[str, str] = {}
        self.headers: dict[str, dict[str, str]] = {}
        self.relations: list[dict[str, Any]] = []

    async def call(
        self, who: str | None, method: str, path: str, body: Any = None
    ) -> Any:
        response = await self.client.request(
            method,
            "/api/v1" + path,
            headers=self.headers.get(who or "", {}),
            **({"json": body} if body is not None else {}),
        )
        if response.status_code >= 400:
            # No response bodies or sensitive request content in logs.
            code = response.json().get("error", {}).get("code", "UNAVAILABLE")
            raise RuntimeError(
                f"Fixture API failed: {method} {path}: {response.status_code} {code}"
            )
        return response.json() if response.content else None

    async def create_participants(self) -> None:
        async with self.app.state.sessions.begin() as db:
            if await db.scalar(select(User.id).limit(1)):
                raise ValueError(
                    "Populate requires an empty users table; use guarded --reset"
                )
            await seed_references(db)
            for person in self.data["participants"]:
                user = await create_user(
                    db,
                    ProvisionUserCommand(
                        telegram_id=person["telegram_id"],
                        display_name=person["name"],
                        shop_role=person["shop_role"],
                    ),
                    self.app.state.clock.now(),
                )
                self.users[person["key"]] = str(user.id)
                prefs = await db.get(UserPreferences, user.id)
                assert prefs is not None
                prefs.language, prefs.timezone = "ru", "Europe/Madrid"
                prefs.notification_channels = ["in_app"]
        for key, uid in self.users.items():
            auth = await self.call(None, "POST", "/auth/debug", {"user_id": uid})
            self.headers[key] = {"Authorization": "Bearer " + auth["access_token"]}

    async def create_relations(self) -> None:
        for edge in self.data["relations"]:
            upper, lower = edge["upper"], edge["lower"]
            relation = await self.call(
                upper,
                "POST",
                "/relations",
                {
                    "dominant_user_id": self.users[upper],
                    "submissive_user_id": self.users[lower],
                    "scopes": SCOPES,
                    "agreement_text": "Синтетический пример договорённостей двух участников. "
                    "Полномочия действуют только в этих отношениях и не передаются дальше по цепочке.",
                },
            )
            for key in [upper, lower]:
                relation = await self.call(
                    key,
                    "POST",
                    f"/relations/{relation['id']}/accept",
                    {
                        "expected_version": relation["version"],
                        "relation_version_id": relation["relation_version_id"],
                    },
                )
            self.relations.append({**edge, "id": relation["id"]})

    async def profiles(self) -> None:
        refs = {
            kind: {row["name"]: str(row["uid"]) for row in fixture_rows(kind)}
            for kind in CATALOGUES
        }
        for p in self.data["participants"]:
            key = p["key"]
            partners = [
                self.users[e["lower"] if e["upper"] == key else e["upper"]]
                for e in self.relations
                if key in (e["upper"], e["lower"])
            ]
            sections = {
                "identity": {
                    "display_name": p["name"],
                    "bio": p["bio"],
                    "biological_sex_uid": refs["biological-sex"][p["sex"]],
                    "gender_uid": refs["genders"][p["gender"]],
                },
                "dynamics": {
                    "profile_labels": [p["label"]],
                    "sex_preference": {"mode": "any", "uids": []},
                    "gender_preference": {"mode": "any", "uids": []},
                    "relationship_type_uids": [
                        refs["relationship-types"]["Романтические"]
                    ],
                    "interaction_format_uids": [refs["interaction-formats"]["Очно"]],
                    "composition_uids": [
                        refs["participant-compositions"][name]
                        for name in p["compositions"]
                    ],
                },
                "preferences": {
                    "practices": [
                        {
                            "practice_uid": refs["practices"][v["name"]],
                            "participation": p["participation"],
                            **{
                                k: v[k]
                                for k in ["attitude", "experience", "conditions"]
                            },
                        }
                        for v in self.data["practices"]
                    ],
                    "devices": [
                        {
                            "uid": refs["devices"]["Манжеты"],
                            "attitude": "conditional",
                            "conditions": "Заранее обсудить формат.",
                        }
                    ],
                    "body_parts": [
                        {
                            "uid": refs["body-parts"]["Спина"],
                            "attitude": "like",
                            "conditions": "Предпочитаю спокойный массаж.",
                        }
                    ],
                    "role_scenarios": [
                        {
                            "uid": refs["role-scenarios"][p["scenario"]],
                            "attitude": "want_to_try",
                        }
                    ],
                    "materials": [
                        {
                            "uid": refs["materials"]["Латекс"],
                            "attitude": "taboo",
                            "conditions": "Личная граница в синтетическом примере.",
                        }
                    ],
                    "venues": [{"uid": refs["venues"]["Дом"], "attitude": "like"}],
                },
                "boundaries": {"notes": p["boundary"]},
                "health": {
                    "condition_uids": [],
                    "allergen_uids": [],
                    "care_practice_uids": [refs["practices"]["Забота после практики"]],
                    "notes": "Синтетический профиль. Медицинские сведения не указаны. "
                    "После практики предпочитаю отдых, воду и спокойную обстановку.",
                },
                "visibility": {
                    "sections": [
                        {"section": section, "reader_ids": partners}
                        for section in [
                            "identity",
                            "dynamics",
                            "preferences",
                            "boundaries",
                        ]
                    ]
                },
            }
            version = 0
            for step, (section, value) in enumerate(sections.items(), 1):
                draft = await self.call(
                    key,
                    "PUT",
                    "/me/profile/draft",
                    {
                        "expected_version": version,
                        "section": section,
                        "value": value,
                        "step": step,
                    },
                )
                version = draft["version"]
            await self.call(
                key, "POST", "/me/profile/publish", {"expected_draft_version": version}
            )

    async def questionnaires_and_journals(self) -> None:
        for p in self.data["participants"]:
            key = p["key"]
            author = "vika" if key in {"alex", "luna"} else "alex"
            form = await self.call(author, "POST", "/forms", self.data["questionnaire"])
            form = await self.call(
                author,
                "POST",
                f"/forms/{form['id']}/publish",
                {
                    "expected_version": form["revision"],
                },
            )
            invite = await self.call(
                author,
                "POST",
                f"/forms/{form['id']}/invitations",
                {
                    "recipient_user_id": self.users[key],
                    "reader_ids": [self.users[author]],
                    "deliver": False,
                },
            )
            await self.call(
                key,
                "POST",
                f"/form-invitations/{invite['id']}/submit",
                {
                    "answers": {
                        "comfort": "Понятные планы, спокойный разговор и время без спешки.",
                        "boundaries": p["boundary"],
                        "care": ["tea", "talk"],
                        "pace": 4,
                    },
                    "acknowledged": True,
                    "idempotency_key": str(uuid4()),
                },
            )
            await self.call(
                key,
                "POST",
                "/journal",
                {
                    "date": str(
                        self.app.state.clock.now()
                        .astimezone(ZoneInfo("Europe/Madrid"))
                        .date()
                    ),
                    "title": "Первый день в пространстве",
                    "text": p["bio"]
                    + " Сегодня заполнили профили и обсудили пожелания. "
                    "Эта запись доступна только мне.",
                    "mood": "Спокойно",
                    "tags": ["знакомство", "личное"],
                    "published": True,
                },
            )

    async def relationship_examples(self, edge: dict[str, Any]) -> None:
        upper, lower, rid = edge["upper"], edge["lower"], edge["id"]
        for item in self.data["rules"]:
            rule = await self.call(
                upper,
                "POST",
                "/rules",
                {
                    "title": item["title"],
                    "description": item["description"],
                },
            )
            rule = await self.call(
                upper,
                "POST",
                f"/rules/{rule['id']}/publish",
                {
                    "expected_version": rule["revision"],
                },
            )
            assignment = await self.call(
                upper,
                "POST",
                f"/rules/{rule['id']}/assignments",
                {
                    "rule_version_id": rule["version_id"],
                    "recipient_id": self.users[lower],
                    "manager_ids": [self.users[upper]],
                },
            )
            assignment = await self.call(
                lower,
                "POST",
                f"/rule-assignments/{assignment['id']}/accept",
                {
                    "expected_version": assignment["revision"],
                    "rule_version_id": rule["version_id"],
                },
            )
            if item["change_request"]:
                await self.call(
                    lower,
                    "POST",
                    "/change-requests",
                    {
                        "kind": "rule_edit",
                        "assignment_id": assignment["id"],
                        "expected_version": assignment["revision"],
                        "idempotency_key": str(uuid4()),
                        "reason": "Предлагаю уточнить, что достаточно короткого сообщения.",
                        "content": {
                            "title": item["title"],
                            "description": item["description"]
                            + " Достаточно короткого сообщения без подробного объяснения.",
                        },
                    },
                )
        for item in self.data["rituals"]:
            ritual = await self.call(
                upper,
                "POST",
                "/rituals",
                {
                    "title": item["title"],
                    "description": item["description"],
                },
            )
            ritual = await self.call(
                upper,
                "POST",
                f"/rituals/{ritual['id']}/publish",
                {
                    "expected_version": ritual["revision"],
                },
            )
            assignment = await self.call(
                upper,
                "POST",
                f"/rituals/{ritual['id']}/assignments",
                {
                    "recipient_id": self.users[lower],
                    "reviewer_ids": [self.users[upper]],
                    "approval_required": True,
                    "evidence_policy": {"required": False},
                    "schedule": {
                        "kind": "once",
                        "timezone": "Europe/Madrid",
                        "hour": 0,
                        "minute": 0,
                        "start_date": str(
                            self.app.state.clock.now()
                            .astimezone(ZoneInfo("Europe/Madrid"))
                            .date()
                        ),
                        "weekdays": [],
                        "window_hours": 48,
                    },
                    "idempotency_key": str(uuid4()),
                },
            )
            occurrences = await self.call(lower, "GET", "/ritual-occurrences")
            occurrence = next(
                o for o in occurrences if o["assignment_id"] == assignment["id"]
            )
            state = item["state"]
            if state in {"reported", "completed"}:
                occurrence = await self.call(
                    lower,
                    "POST",
                    f"/ritual-occurrences/{occurrence['id']}/report",
                    {
                        "expected_version": occurrence["revision"],
                        "text": "Нашлось время на отдых "
                        "и спокойный разговор. Всё прошло в комфортном темпе.",
                        "links": [],
                        "evidence_ids": [],
                        "idempotency_key": str(uuid4()),
                    },
                )
                if state == "completed":
                    await self.call(
                        upper,
                        "POST",
                        f"/ritual-occurrences/{occurrence['id']}/review",
                        {
                            "expected_version": occurrence["revision"],
                            "decision": "approved",
                            "comment": "Спасибо за отчёт!",
                        },
                    )
            if state == "skip_requested":
                await self.call(
                    lower,
                    "POST",
                    "/change-requests",
                    {
                        "kind": "ritual_skip",
                        "assignment_id": assignment["id"],
                        "occurrence_id": occurrence["id"],
                        "expected_version": assignment["revision"],
                        "reason": "Сегодня хочу восстановиться и перенести прогулку на выходные.",
                        "idempotency_key": str(uuid4()),
                    },
                )
        for item in self.data["punishments"]:
            template = await self.call(
                upper,
                "POST",
                "/punishment-templates",
                {
                    "relation_id": rid,
                    **item,
                },
            )
            if item["punishment_type"] == "other":
                await self.call(
                    upper,
                    "POST",
                    f"/punishment-templates/{template['id']}/assign",
                    {
                        "expected_version": template["revision"],
                        "idempotency_key": str(uuid4()),
                        "comment": "Пример назначения с комментарием для просмотра интерфейса.",
                    },
                )

    async def shop(self) -> dict[str, Any]:
        products = json.loads((ROOT / "scripts/fixtures/rewards.json").read_text())
        for product in products:
            await self.call("alex", "POST", "/shop/products", product)
        wallets = {}
        for edge in self.relations:
            upper, lower, rid = edge["upper"], edge["lower"], edge["id"]
            # Fixture bootstrap credits use the real ledger service. Switch cannot issue manual
            # credits via the product-management API; do not temporarily elevate its shop role.
            async with self.app.state.sessions.begin() as db:
                await economy.locked_wallet(db, UUID(rid))
                await economy.append(
                    db,
                    UUID(rid),
                    UUID(self.users[upper]),
                    edge["coins"],
                    "manual",
                    "Стартовые монеты debug-фикстуры",
                    self.app.state.clock.now(),
                    PayloadCipher(self.app.state.settings.data_keyring_file),
                    key=uuid4(),
                )
            catalogue = await self.call(
                lower, "GET", f"/shop/catalogue?relation_id={rid}"
            )
            for purchase in self.data["purchases"]:
                product = next(p for p in catalogue if p["title"] == purchase["title"])
                grant = await self.call(
                    lower,
                    "POST",
                    f"/shop/{product['id']}/purchases",
                    {
                        "relation_id": rid,
                        "expected_version": product["revision"],
                        "idempotency_key": str(uuid4()),
                    },
                )
                if purchase["state"] != "pending":
                    action = "reject" if purchase["state"] == "rejected" else "approve"
                    grant = await self.call(
                        upper,
                        "POST",
                        f"/reward-grants/{grant['id']}/transitions",
                        {
                            "expected_version": grant["revision"],
                            "action": action,
                        },
                    )
                    if purchase["state"] == "redeemed":
                        await self.call(
                            lower,
                            "POST",
                            f"/reward-grants/{grant['id']}/transitions",
                            {
                                "expected_version": grant["revision"],
                                "action": "redeem",
                            },
                        )
            wallets[lower] = await self.call(lower, "GET", f"/relations/{rid}/wallet")
        return {"products": len(products), "wallets": wallets}

    async def verify(self) -> dict[str, Any]:
        for key in self.users:
            profile = await self.call(key, "GET", "/me/profile")
            if not profile["progress"]["completed"]:
                raise RuntimeError("Fixture profile is incomplete")
            submissions = await self.call(key, "GET", "/form-invitations")
            if not any(s["status"] == "submitted" for s in submissions):
                raise RuntimeError("Fixture questionnaire is incomplete")
            journals = await self.call(key, "GET", "/journal")
            if len(journals) != 1 or journals[0]["visibility"] != "private":
                raise RuntimeError("Fixture journals must remain private")
        denied = await self.client.get(
            "/api/v1/participants/" + self.users["luna"] + "/profile",
            headers=self.headers["alex"],
        )
        if denied.status_code not in {403, 404}:
            raise RuntimeError("Unexpected transitive profile access")
        return {
            "profiles_completed": 3,
            "questionnaires_submitted": 3,
            "transitive_access_denied": True,
            "private_journals": 3,
        }


async def populate(app: FastAPI, client: httpx.AsyncClient) -> dict[str, Any]:
    settings = app.state.settings
    if settings.app_env != "development" or not settings.debug_auth:
        raise ValueError("Fixtures require explicit development debug authentication")
    validate_reset(settings.database_url, [])
    scenario = Scenario(app, client, json.loads(SCENARIO.read_text()))
    await scenario.create_participants()
    await scenario.create_relations()
    await scenario.profiles()
    await scenario.questionnaires_and_journals()
    for edge in scenario.relations:
        await scenario.relationship_examples(edge)
    shop = await scenario.shop()
    return {
        "participants": scenario.users,
        "relations": scenario.relations,
        **shop,
        "checks": await scenario.verify(),
    }


def backup_database(url: str, folder: Path) -> Path:
    target = make_url(url)
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    output = folder / (
        "before-debug-reset-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".dump"
    )
    # Reserve private permissions before pg_dump writes any data.
    output.touch(mode=0o600, exist_ok=False)
    env = {**os.environ, "PGPASSWORD": target.password or ""}
    try:
        subprocess.run(
            [
                "pg_dump",
                "-h",
                target.host or "",
                "-p",
                str(target.port or 5432),
                "-U",
                target.username or "",
                "-d",
                target.database or "",
                "-Fc",
                "-f",
                str(output),
            ],
            env=env,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        output.unlink(missing_ok=True)
        raise RuntimeError(
            "Private database backup failed; reset was not started"
        ) from exc
    return output


async def main(args: argparse.Namespace) -> None:
    validate_reset(args.database_url, [])
    app = create_app(
        Settings(
            app_env="development",
            debug_auth=True,
            database_url=args.database_url,
            telegram_bot_token_file=args.bot_token_file,
            data_keyring_file=args.keyring_file,
            public_base_url="http://127.0.0.1:5176",
        )
    )
    try:
        async with app.state.sessions.begin() as db:
            # Lock identity inspection; recheck after backup before resetting the tables.
            await db.execute(text("LOCK TABLE users IN ACCESS EXCLUSIVE MODE"))
            users = [
                (u.telegram_id, u.display_name) for u in await db.scalars(select(User))
            ]
            validate_reset(args.database_url, users)
            if users and not args.reset:
                raise ValueError(
                    "Users exist; pass --reset to replace recognized synthetic users"
                )
        if users:
            backup_database(args.database_url, args.backup_dir)
        init_keyring(args.keyring_file)
        async with app.state.sessions.begin() as db:
            await db.execute(text("LOCK TABLE users IN ACCESS EXCLUSIVE MODE"))
            current = [
                (u.telegram_id, u.display_name) for u in await db.scalars(select(User))
            ]
            if sorted(current) != sorted(users):
                raise ValueError("Users changed during backup; reset refused")
            validate_reset(args.database_url, current)
            await db.execute(text("TRUNCATE users CASCADE"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=app.state.settings.public_base_url,
            headers={"Origin": app.state.settings.public_base_url},
        ) as client:
            result = await populate(app, client)
        print(
            json.dumps(
                {
                    "participants": list(result["participants"]),
                    "products": result["products"],
                    "checks": result["checks"],
                    "wallets": {
                        k: {f: v[f] for f in ["balance", "reserved"]}
                        for k, v in result["wallets"].items()
                    },
                },
                ensure_ascii=False,
            )
        )
    finally:
        await app.state.engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", default=os.environ.get("TEST_DATABASE_URL"), required=False
    )
    parser.add_argument("--bot-token-file", type=Path, required=True)
    parser.add_argument("--keyring-file", type=Path, required=True)
    parser.add_argument(
        "--backup-dir", type=Path, default=ROOT / ".superpowers/debug-backups"
    )
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Set TEST_DATABASE_URL or --database-url")
    asyncio.run(main(args))
