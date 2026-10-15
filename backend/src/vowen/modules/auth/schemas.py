from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MiniAppLogin(Input):
    init_data: str = Field(max_length=16384)


class DebugLogin(Input):
    user_id: UUID


class DebugUserView(BaseModel):
    id: UUID
    display_name: str


class RefreshRequest(Input):
    refresh_token: str = Field(min_length=43, max_length=43)


class SessionTokens(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    session_id: UUID


class ParticipantView(BaseModel):
    id: UUID
    display_name: str
    profile_labels: list[str]


class MemberView(ParticipantView):
    paused: bool
    language: str
    timezone: str
    profile_version: int


class SessionView(BaseModel):
    id: UUID
    client: str
    device_label: str
    created_at: datetime
    expires_at: datetime
    revoked: bool


class InstanceView(BaseModel):
    display_name: str
    debug_auth_enabled: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
