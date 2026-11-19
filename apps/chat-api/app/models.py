"""ORM models.

Tables are added here as their ticket lands; every model imports ``Base`` from
``app.db`` so ``init_db`` can create the schema in one call.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    """Primary keys are UUID4 strings so ids never leak row counts."""
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<User {self.email}>"


class Conversation(Base):
    """A thread of messages.

    Only ``direct`` (1:1) threads exist for now. ``direct_key`` is the two user
    ids sorted and joined, so a unique index makes a duplicate 1:1 conversation
    impossible even under two concurrent requests.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    type: Mapped[str] = mapped_column(String(16), default="direct", nullable=False)
    direct_key: Mapped[str | None] = mapped_column(
        String(73), unique=True, nullable=True
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    # NULL until the first message lands, so empty threads sort after active
    # ones. CHAT-4 bumps it inside the same transaction as the insert.
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True, index=True
    )

    members: Mapped[list[ConversationMember]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def participants(self) -> list[User]:
        return [member.user for member in self.members]

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Conversation {self.id} {self.type}>"


class ConversationMember(Base):
    __tablename__ = "conversation_members"
    # The composite primary key already forbids a duplicate pair; the named
    # constraint states the rule the API (and CHAT-3's schema check) rely on.
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_members_pair"
        ),
    )

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    # Highest message seq this member has read; 0 means "nothing read yet".
    last_read_seq: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="members")
    user: Mapped[User] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<ConversationMember {self.conversation_id}/{self.user_id}>"
