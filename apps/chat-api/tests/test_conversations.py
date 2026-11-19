"""1:1 conversations: creation, idempotency, membership scoping."""

from __future__ import annotations

from fastapi.testclient import TestClient


def create_direct(client: TestClient, headers: dict, peer_id: str):
    return client.post("/api/conversations", json={"peer_id": peer_id}, headers=headers)


def test_create_returns_the_two_participants(client, me, other):
    response = create_direct(client, me["headers"], other["id"])

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "direct"
    assert {p["id"] for p in body["participants"]} == {me["id"], other["id"]}
    assert set(body) == {"id", "type", "created_at", "participants"}


def test_second_request_returns_the_same_thread(client, me, other):
    first = create_direct(client, me["headers"], other["id"])
    second = create_direct(client, me["headers"], other["id"])

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_direct_thread_is_the_same_from_either_side(client, me, other):
    from_me = create_direct(client, me["headers"], other["id"])
    from_other = create_direct(client, other["headers"], me["id"])

    assert from_me.status_code == 201
    assert from_other.status_code == 200
    assert from_other.json()["id"] == from_me.json()["id"]


def test_list_returns_only_my_conversations(client, me, other, account):
    third = account("salim@example.com", "Salim")
    mine = create_direct(client, me["headers"], other["id"]).json()
    create_direct(client, other["headers"], third["id"])  # not mine

    response = client.get("/api/conversations", headers=me["headers"])

    assert response.status_code == 200
    assert [c["id"] for c in response.json()] == [mine["id"]]


def test_list_is_empty_for_a_fresh_user(client, me):
    assert client.get("/api/conversations", headers=me["headers"]).json() == []


def test_get_returns_a_conversation_i_belong_to(client, me, other):
    conversation = create_direct(client, me["headers"], other["id"]).json()

    response = client.get(f"/api/conversations/{conversation['id']}", headers=me["headers"])

    assert response.status_code == 200
    assert response.json()["id"] == conversation["id"]


def test_get_hides_conversations_i_am_not_part_of(client, me, other, account):
    stranger = account("salim@example.com", "Salim")
    conversation = create_direct(client, me["headers"], other["id"]).json()

    response = client.get(
        f"/api/conversations/{conversation['id']}", headers=stranger["headers"]
    )

    assert response.status_code == 404


def test_cannot_start_a_conversation_with_myself(client, me):
    response = create_direct(client, me["headers"], me["id"])

    assert response.status_code == 400
    assert response.json()["detail"] == "cannot start a conversation with yourself"


def test_unknown_peer_returns_404(client, me):
    response = create_direct(client, me["headers"], "00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "user not found"


def test_requires_authentication(client, other):
    response = client.post("/api/conversations", json={"peer_id": other["id"]})

    assert response.status_code == 401
    assert client.get("/api/conversations").status_code == 401
