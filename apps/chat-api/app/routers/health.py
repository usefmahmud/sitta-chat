"""Liveness/readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health(db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "database": "ok",
    }
