import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from vowen.modules.auth.schemas import Input


class ReferenceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    uid: UUID
    name: str
    description: str
    icon: str | None = None
    thumbnail: str | None = None
    url: str | None = None
    category_uid: UUID | None = None
    device_uids: list[UUID] = Field(default_factory=list, max_length=100)
    body_part_uids: list[UUID] = Field(default_factory=list, max_length=100)
    extra: dict[str, JsonValue] = Field(default_factory=dict)


class PracticeCreate(Input):
    category_uid: UUID | None = None
    device_uids: list[UUID] = Field(default_factory=list, max_length=100)
    body_part_uids: list[UUID] = Field(default_factory=list, max_length=100)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    icon: str | None = Field(default=None, max_length=500)
    thumbnail: str | None = Field(default=None, max_length=500)
    extra: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("icon", "thumbnail")
    @classmethod
    def local_asset(cls, value: str | None) -> str | None:
        if value is not None:
            import re

            if not re.fullmatch(r"/(?!/)[A-Za-z0-9_./-]+", value) or ".." in value.split("/"):
                raise ValueError("Image must be a local asset path")
        return value

    @field_validator("extra")
    @classmethod
    def bounded_extra(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()) > 16384:
            raise ValueError("Extra data is too large")
        return value
