"""Request and response bodies."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


class MessageCreate(BaseModel):
    """Send a message. ``client_msg_id`` makes a retry idempotent."""

    body: str = Field(min_length=1, max_length=4000)
    client_msg_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("body")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("body must contain at least one non-space character")
        return value


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    seq: int
    body: str
    client_msg_id: str | None = None
    created_at: datetime


class MessagePage(BaseModel):
    """One page of a thread.

    ``items`` is newest-first unless the request used ``after_seq`` (the
    reconnect catch-up), in which case it is oldest-first and contiguous.
    ``next_before_seq`` is the cursor for the next older page, ``null`` when the
    start of the thread has been reached.
    """

    items: list[MessageOut]
    next_before_seq: int | None = None
    has_more: bool = False
