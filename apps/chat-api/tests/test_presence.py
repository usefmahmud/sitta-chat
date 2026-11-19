"""Presence: online/offline frames, scoping, last_seen, no flapping."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.realtime.hub import hub


@pytest.fixture(autouse=True)
def _clean_hub():
    hub.reset()
    yield
    hub.reset()


def connect(client: TestClient, user: dict):
    return client.websocket_connect(f"/ws?token={user['token']}")


def test_online_is_broadcast_to_people_who_share_a_room(
    client, me, other, conversation
):
    with connect(client, other) as peer:
        peer.receive_json()

        with connect(client, me) as mine:
            mine.receive_json()
            event = peer.receive_json()

    assert event["type"] == "presence"
    assert event["user_id"] == me["id"]
    assert event["status"] == "online"
    assert event["last_seen"] is not None


def test_offline_is_broadcast_when_the_last_socket_closes(
    client, me, other, conversation
):
    with connect(client, other) as peer:
        peer.receive_json()

        with connect(client, me) as mine:
            mine.receive_json()
            peer.receive_json()  # online

        offline = peer.receive_json()

    assert offline["type"] == "presence"
    assert offline["user_id"] == me["id"]
    assert offline["status"] == "offline"
    assert offline["last_seen"] is not None


def test_presence_never_reaches_people_outside_my_rooms(
    client, me, conversation, account
):
    stranger = account("salim@example.com", "Salim")

    with connect(client, stranger) as stranger_socket:
        stranger_socket.receive_json()

        with connect(client, me) as mine:
            mine.receive_json()
            stranger_socket.send_json({"type": "ping"})
            assert stranger_socket.receive_json() == {"type": "pong"}


def test_two_sockets_stay_online_until_the_last_one_closes(
    client, me, other, conversation
):
    with connect(client, other) as peer:
        peer.receive_json()

        with connect(client, me) as first:
            first.receive_json()
            assert peer.receive_json()["status"] == "online"

            with connect(client, me) as second:
                second.receive_json()
                assert hub.count(me["id"]) == 2

                # No flap: a second socket of the same user is not news.
                peer.send_json({"type": "ping"})
                assert peer.receive_json() == {"type": "pong"}

            # first is still open, so no offline frame yet.
            assert hub.count(me["id"]) == 1
            peer.send_json({"type": "ping"})
            assert peer.receive_json() == {"type": "pong"}

        offline = peer.receive_json()

    assert offline["status"] == "offline"


def test_last_seen_is_persisted_on_disconnect(client, me, other, conversation):
    with connect(client, other) as peer:
        peer.receive_json()
        with connect(client, me) as mine:
            mine.receive_json()
            peer.receive_json()  # online

        # The offline frame is emitted after the write: use it as the barrier.
        assert peer.receive_json()["status"] == "offline"

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.id == me["id"]))

    assert user is not None
    assert user.last_seen_at is not None


def test_presence_endpoint_reports_a_peer_as_online(client, me, other, conversation):
    with connect(client, other):
        response = client.get(
            f"/api/presence?ids={other['id']}", headers=me["headers"]
        )

    assert response.status_code == 200
    [entry] = response.json()["users"]
    assert entry["user_id"] == other["id"]
    assert entry["status"] == "online"


def test_presence_endpoint_reports_offline_with_last_seen(
    client, me, other, conversation
):
    with connect(client, other) as peer:
        peer.receive_json()
        with connect(client, me) as mine:
            mine.receive_json()
            peer.receive_json()  # online
        peer.receive_json()  # offline: the write has landed by now

        response = client.get(
            f"/api/presence?ids={me['id']}", headers=other["headers"]
        )

    [entry] = response.json()["users"]
    assert entry["status"] == "offline"
    assert entry["last_seen"] is not None


def test_presence_endpoint_omits_ids_outside_my_rooms(client, me, account):
    stranger = account("salim@example.com", "Salim")

    response = client.get(
        f"/api/presence?ids={stranger['id']}", headers=me["headers"]
    )

    assert response.status_code == 200
    assert response.json()["users"] == []


def test_presence_endpoint_omits_unknown_ids(client, me, other, conversation):
    response = client.get(
        f"/api/presence?ids={other['id']},00000000-0000-0000-0000-000000000000,nope",
        headers=me["headers"],
    )

    assert [entry["user_id"] for entry in response.json()["users"]] == [other["id"]]


def test_presence_endpoint_requires_authentication(client, other):
    assert client.get(f"/api/presence?ids={other['id']}").status_code == 401
