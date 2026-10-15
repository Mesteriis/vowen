from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from vowen.modules.auth.schemas import Input

ProfileLabel = Literal["dominant", "submissive", "switch"]


class ProfilePatch(Input):
    expected_version: int = Field(ge=1)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    language: Literal["ru", "en"] | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    profile_labels: list[ProfileLabel] | None = Field(default=None, max_length=3)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Empty name")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise ValueError("Unknown timezone") from None
        return value

    @model_validator(mode="after")
    def nonnull_fields(self) -> "ProfilePatch":
        for name in self.model_fields_set - {"expected_version"}:
            if getattr(self, name) is None:
                raise ValueError("Explicit null is not supported")
        if self.profile_labels is not None and len(set(self.profile_labels)) != len(
            self.profile_labels
        ):
            raise ValueError("Duplicate labels")
        return self
