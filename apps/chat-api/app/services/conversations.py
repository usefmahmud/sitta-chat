"""Conversation lookups and creation.

Kept out of the router so the WebSocket layer can reuse the same membership
checks without importing HTTP concerns.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Conversation, ConversationMember, User


def direct_key_for(user_a: str, user_b: str) -> str:
    """Canonical key for a 1:1 thread, independent of who starts it."""
    return ":".join(sorted((user_a, user_b)))


def get_for_user(db: Session, conversation_id: str, user_id: str) -> Conversation | None:
    """Return the conversation only if ``user_id`` is a member of it."""
    return db.scalar(
        select(Conversation)
        .join(
            ConversationMember,
            ConversationMember.conversation_id == Conversation.id,
        )
        .where(
            Conversation.id == conversation_id,
            ConversationMember.user_id == user_id,
        )
    )


def member_ids(db: Session, conversation_id: str) -> list[str]:
    return list(
        db.scalars(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id
            )
        ).all()
    )


def list_for_user(db: Session, user_id: str) -> list[Conversation]:
    """My rooms, most recent activity first.

    ``last_message_at`` is NULL for a room nobody has written in yet; those
    sort last (``is_(None)`` is 0 for a timestamp, 1 for NULL in SQLite) and
    fall back to newest-created among themselves.
    """
    return list(
        db.scalars(
            select(Conversation)
            .join(
                ConversationMember,
                ConversationMember.conversation_id == Conversation.id,
            )
            .where(ConversationMember.user_id == user_id)
            .order_by(
                Conversation.last_message_at.is_(None),
                Conversation.last_message_at.desc(),
                Conversation.created_at.desc(),
                Conversation.id.desc(),
            )
        ).all()
    )


def create_direct(db: Session, starter: User, peer: User) -> tuple[Conversation, bool]:
    """Return ``(conversation, created)``; an existing thread is returned as is."""
    key = direct_key_for(starter.id, peer.id)

    existing = db.scalar(select(Conversation).where(Conversation.direct_key == key))
    if existing is not None:
        return existing, False

    conversation = Conversation(type="direct", direct_key=key, created_by=starter.id)
    conversation.members = [
        ConversationMember(user_id=starter.id),
        ConversationMember(user_id=peer.id),
    ]
    db.add(conversation)

    try:
        db.commit()
    except IntegrityError:
        # Two requests raced; the unique index on direct_key kept one thread.
        db.rollback()
        existing = db.scalar(select(Conversation).where(Conversation.direct_key == key))
        if existing is None:  # pragma: no cover - defensive
            raise
        return existing, False

    db.refresh(conversation)
    return conversation, True
