"""Liveness/readiness endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def read_health(db: Session = Depends(get_db)) -> dict[str, str] | JSONResponse:
    """200 when the database answers, 503 when it does not.

    A container orchestrator should stop routing traffic to an instance whose
    database is gone, so this is a readiness check, not just a liveness ping.
    """
    settings = get_settings()
    payload = {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "database": "ok",
    }

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={**payload, "status": "degraded", "database": "error"},
        )

    return payload
