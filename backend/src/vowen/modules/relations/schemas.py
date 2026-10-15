from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from vowen.modules.auth.schemas import Input

Scope = Literal[
    "rules.assign",
    "rituals.assign",
    "rituals.review",
    "discipline.propose",
    "discipline.review",
    "rewards.grant",
]


class VersionContent(Input):
    scopes: list[Scope] = Field(min_length=1, max_length=6)
    agreement_text: str = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def unique_scopes(self) -> "VersionContent":
        if len(set(self.scopes)) != len(self.scopes):
            raise ValueError("Duplicate scopes")
        return self


class ProposeRelationCommand(VersionContent):
    dominant_user_id: UUID
    submissive_user_id: UUID


class ExpectedVersion(Input):
    expected_version: int = Field(ge=1)


class AcceptRelation(ExpectedVersion):
    relation_version_id: UUID


class ChangeVersion(VersionContent):
    expected_version: int = Field(ge=1)


class RelationView(Input):
    id: UUID
    dominant_user_id: UUID
    submissive_user_id: UUID
    status: str
    version: int
    relation_version_id: UUID
    scopes: list[str]
    agreement_text: str
    consent_user_ids: list[UUID]
