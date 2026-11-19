"""Request and response bodies."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=60)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserSummary(BaseModel):
    """What a chat list shows about the other side — no email, no hash."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str


class ConversationCreate(BaseModel):
    """Start (or return) the 1:1 conversation with ``peer_id``."""

    peer_id: str = Field(min_length=1, max_length=36)


class ConversationOut(BaseModel):
    id: str
    type: str
    created_at: datetime
    last_message_at: datetime | None = None
    # Filled from the messages table with CHAT-4; always null on this branch.
    last_message_preview: str | None = None
    peer: UserSummary
