"""Message writes and keyset pagination.

The interesting part is ``seq``: it must increase by exactly one per
conversation and never repeat. SQLite serialises writers, so the sequence is
computed inside the write transaction and the two unique constraints act as the
real guard: a losing writer gets an IntegrityError and retries with a fresh
``MAX(seq)``. ``busy_timeout`` (see ``db.py``) makes the contender wait for the
lock instead of failing outright.
"""

from __future__ import annotations

import time

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..models import Conversation, Message, utcnow

WRITE_ATTEMPTS = 8
PREVIEW_CHARS = 120


class MessageNotSaved(Exception):
    """The database stayed locked through every retry."""


def _by_client_id(
    db: Session, sender_id: str, client_msg_id: str | None
) -> Message | None:
    if not client_msg_id:
        return None
    return db.scalar(
        select(Message).where(
            Message.sender_id == sender_id, Message.client_msg_id == client_msg_id
        )
    )


def send_message(
    db: Session,
    conversation_id: str,
    sender_id: str,
    body: str,
    client_msg_id: str | None = None,
) -> tuple[Message, bool]:
    """Insert one message; return ``(message, created)``.

    A repeat of the same ``client_msg_id`` from the same sender returns the
    original row with ``created=False`` — a network retry never duplicates.
    """
    existing = _by_client_id(db, sender_id, client_msg_id)
    if existing is not None:
        return existing, False

    last_error: Exception | None = None
    for attempt in range(WRITE_ATTEMPTS):
        try:
            next_seq = (
                db.scalar(
                    select(func.coalesce(func.max(Message.seq), 0)).where(
                        Message.conversation_id == conversation_id
                    )
                )
                or 0
            ) + 1
            message = Message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                seq=next_seq,
                body=body,
                client_msg_id=client_msg_id,
                created_at=utcnow(),
            )
            db.add(message)
            # Same transaction as the insert: the chat list reorders immediately.
            db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(last_message_at=message.created_at)
            )
            db.commit()
            db.refresh(message)
            return message, True
        except (IntegrityError, OperationalError) as exc:
            # Either another writer took this seq (unique constraint) or the
            # database was locked; either way, roll back and try again.
            db.rollback()
            last_error = exc
            existing = _by_client_id(db, sender_id, client_msg_id)
            if existing is not None:
                return existing, False
            time.sleep(0.005 * (attempt + 1))

    raise MessageNotSaved(str(last_error))


def page(
    db: Session,
    conversation_id: str,
    *,
    before_seq: int | None = None,
    after_seq: int | None = None,
    limit: int = 30,
) -> tuple[list[Message], int | None, bool]:
    """Return ``(messages, next_before_seq, has_more)``.

    ``before_seq`` walks backwards through history (newest page first, the
    default). ``after_seq`` is the reconnect path: everything newer than the
    client's ``last_seq``, oldest first, so a client that came back online can
    replay without gaps.
    """
    query = select(Message).where(Message.conversation_id == conversation_id)

    if after_seq is not None:
        rows = list(
            db.scalars(
                query.where(Message.seq > after_seq)
                .order_by(Message.seq.asc())
                .limit(limit + 1)
            ).all()
        )
        has_more = len(rows) > limit
        return rows[:limit], None, has_more

    if before_seq is not None:
        query = query.where(Message.seq < before_seq)

    rows = list(db.scalars(query.order_by(Message.seq.desc()).limit(limit + 1)).all())
    has_more = len(rows) > limit
    messages = rows[:limit]
    next_before = messages[-1].seq if has_more and messages else None
    return messages, next_before, has_more


def last_previews(db: Session, conversation_ids: list[str]) -> dict[str, str]:
    """One truncated preview per conversation, in a single query."""
    if not conversation_ids:
        return {}

    ranked = (
        select(
            Message.conversation_id.label("conversation_id"),
            Message.body.label("body"),
            func.row_number()
            .over(
                partition_by=Message.conversation_id,
                order_by=Message.seq.desc(),
            )
            .label("rank"),
        )
        .where(Message.conversation_id.in_(conversation_ids))
        .subquery()
    )
    rows = db.execute(
        select(ranked.c.conversation_id, ranked.c.body).where(ranked.c.rank == 1)
    ).all()
    return {
        conversation_id: body[:PREVIEW_CHARS] for conversation_id, body in rows
    }
