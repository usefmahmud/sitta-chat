from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, get_db


def test_health_reports_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sitta-chat-api",
        "version": "0.1.0",
        "environment": "test",
        "database": "ok",
    }


def test_health_is_json(client):
    assert client.get("/api/health").headers["content-type"].startswith(
        "application/json"
    )


def test_health_returns_503_when_the_database_is_down(client):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("database is gone"))

    client.app.dependency_overrides[get_db] = lambda: BrokenSession()
    try:
        response = client.get("/api/health")
    finally:
        client.app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "error"


def test_unknown_route_returns_404(client):
    assert client.get("/api/nope").status_code == 404


def test_sqlite_runs_in_wal_mode():
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_sqlite_waits_for_the_write_lock():
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
