"""ORM models.

Empty on purpose for the skeleton ticket: the health endpoint only needs the
engine, and each later ticket adds the table it owns.
"""

from __future__ import annotations

from .db import Base

__all__ = ["Base"]
