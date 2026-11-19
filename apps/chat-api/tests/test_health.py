from sqlalchemy import text

from app.db import engine


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


def test_unknown_route_returns_404(client):
    assert client.get("/api/nope").status_code == 404


def test_sqlite_runs_in_wal_mode():
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"
