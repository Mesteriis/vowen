from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MiniAppLogin(Input):
    init_data: str = Field(max_length=16384)


class RefreshRequest(Input):
    refresh_token: str = Field(min_length=43, max_length=43)


class SessionTokens(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    session_id: UUID


class MemberView(BaseModel):
    id: UUID
    display_name: str
    paused: bool


class SessionView(BaseModel):
    id: UUID
    client: str
    device_label: str
    created_at: datetime
    expires_at: datetime
    revoked: bool


class InstanceView(BaseModel):
    display_name: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
