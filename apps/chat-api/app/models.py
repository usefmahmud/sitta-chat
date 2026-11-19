"""ORM models.

Tables are added here as their ticket lands; every model imports ``Base`` from
``app.db`` so ``init_db`` can create the schema in one call.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

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
