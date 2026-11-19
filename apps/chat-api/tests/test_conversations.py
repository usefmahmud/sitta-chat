"""1:1 conversations: schema, creation, idempotency, ordering, membership scope."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.db import SessionLocal, engine
from app.models import Conversation, utcnow


def create_direct(client: TestClient, headers: dict, peer_id: str):
    return client.post("/api/conversations", json={"peer_id": peer_id}, headers=headers)


def conversation_rows() -> int:
    with SessionLocal() as db:
        return len(db.scalars(select(Conversation)).all())


# --- schema (AC-01) ---------------------------------------------------------


def test_schema_has_the_planned_columns_foreign_keys_and_unique_pair():
    inspector = inspect(engine)

    conversation_columns = {c["name"] for c in inspector.get_columns("conversations")}
    assert {"id", "type", "created_at", "last_message_at"} <= conversation_columns

    member_columns = {c["name"] for c in inspector.get_columns("conversation_members")}
    assert {"conversation_id", "user_id", "joined_at", "last_read_seq"} <= member_columns

    referenced = {
        fk["referred_table"] for fk in inspector.get_foreign_keys("conversation_members")
    }
    assert referenced == {"conversations", "users"}

    unique_pairs = [
        set(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("conversation_members")
    ]
    assert {"conversation_id", "user_id"} in unique_pairs


# --- creation (AC-02) -------------------------------------------------------


def test_create_returns_201_with_the_peer(client, me, other):
    response = create_direct(client, me["headers"], other["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "direct"
    assert body["peer"] == {"id": other["id"], "display_name": other["display_name"]}
    assert set(body) == {
        "id",
        "type",
        "created_at",
        "last_message_at",
        "last_message_preview",
        "peer",
    }
    assert body["last_message_at"] is None


def test_create_is_idempotent(client, me, other):
    first = create_direct(client, me["headers"], other["id"])
    second = create_direct(client, me["headers"], other["id"])

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert conversation_rows() == 1


def test_direct_thread_is_the_same_from_either_side(client, me, other):
    from_me = create_direct(client, me["headers"], other["id"])
    from_other = create_direct(client, other["headers"], me["id"])

    assert from_me.status_code == 201
    assert from_other.status_code == 200
    assert from_other.json()["id"] == from_me.json()["id"]
    # each side sees the other as the peer
    assert from_me.json()["peer"]["id"] == other["id"]
    assert from_other.json()["peer"]["id"] == me["id"]


# --- listing (AC-03) --------------------------------------------------------


def test_list_returns_only_my_conversations(client, me, other, account):
    third = account("salim@example.com", "Salim")
    mine = create_direct(client, me["headers"], other["id"]).json()
    create_direct(client, other["headers"], third["id"])  # not mine

    response = client.get("/api/conversations", headers=me["headers"])

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [mine["id"]]


def test_list_is_empty_for_a_fresh_user(client, me):
    assert client.get("/api/conversations", headers=me["headers"]).json() == []


def test_list_ordering_puts_recent_activity_first_and_empty_rooms_last(
    client, me, other, account
):
    third = account("salim@example.com", "Salim")
    older = create_direct(client, me["headers"], other["id"]).json()
    newer = create_direct(client, me["headers"], third["id"]).json()

    # both empty: newest-created first
    empty_order = [
        c["id"] for c in client.get("/api/conversations", headers=me["headers"]).json()
    ]
    assert empty_order == [newer["id"], older["id"]]

    # activity in the older room -> it jumps to the top, the empty one is last
    with SessionLocal() as db:
        conversation = db.get(Conversation, older["id"])
        assert conversation is not None
        conversation.last_message_at = utcnow()
        db.commit()

    order = [
        c["id"] for c in client.get("/api/conversations", headers=me["headers"]).json()
    ]
    assert order == [older["id"], newer["id"]]


def test_list_preview_is_null_until_messages_land(client, me, other):
    create_direct(client, me["headers"], other["id"])

    body = client.get("/api/conversations", headers=me["headers"]).json()[0]

    assert body["last_message_preview"] is None


# --- reading one room (AC-04) ----------------------------------------------


def test_get_returns_a_conversation_i_belong_to(client, me, other):
    conversation = create_direct(client, me["headers"], other["id"]).json()

    response = client.get(
        f"/api/conversations/{conversation['id']}", headers=me["headers"]
    )

    assert response.status_code == 200
    assert response.json()["id"] == conversation["id"]


def test_not_member_gets_404_not_403(client, me, other, account):
    stranger = account("salim@example.com", "Salim")
    conversation = create_direct(client, me["headers"], other["id"]).json()

    response = client.get(
        f"/api/conversations/{conversation['id']}", headers=stranger["headers"]
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "conversation not found"


def test_unknown_conversation_returns_404(client, me):
    response = client.get(
        "/api/conversations/00000000-0000-0000-0000-000000000000",
        headers=me["headers"],
    )

    assert response.status_code == 404


# --- validation (AC-05) -----------------------------------------------------


def test_cannot_start_a_conversation_with_myself(client, me):
    response = create_direct(client, me["headers"], me["id"])

    assert response.status_code == 422
    assert response.json()["detail"] == "cannot start a conversation with yourself"


def test_unknown_peer_returns_404(client, me):
    response = create_direct(
        client, me["headers"], "00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"


def test_requires_authentication(client, other):
    response = client.post("/api/conversations", json={"peer_id": other["id"]})

    assert response.status_code == 401
    assert client.get("/api/conversations").status_code == 401
