"""WebSocket: auth, registry, broadcast, isolation and protocol errors."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.realtime.hub import hub
from app.security import create_access_token


@pytest.fixture(autouse=True)
def _clean_hub():
    hub.reset()
    yield
    hub.reset()


def ws_url(token: str) -> str:
    return f"/ws?token={token}"


def send(
    client: TestClient, conversation_id: str, headers: dict, body: str, key: str | None = None
):
    payload: dict[str, str] = {"body": body}
    if key:
        payload["client_msg_id"] = key
    return client.post(
        f"/api/conversations/{conversation_id}/messages", json=payload, headers=headers
    )


def test_rejects_a_missing_token(client):
    with client.websocket_connect("/ws") as websocket:
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()

    assert exc.value.code == 4401


def test_rejects_a_garbage_token(client):
    with client.websocket_connect(ws_url("not-a-jwt")) as websocket:
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()

    assert exc.value.code == 4401


def test_rejects_an_expired_token(client, me):
    expired, _ = create_access_token(me["id"], ttl_minutes=-1)

    with client.websocket_connect(ws_url(expired)) as websocket:
        with pytest.raises(WebSocketDisconnect) as exc:
            websocket.receive_json()

    assert exc.value.code == 4401


def test_ready_frame_lists_my_conversations(client, me, other, conversation):
    with client.websocket_connect(ws_url(me["token"])) as websocket:
        ready = websocket.receive_json()

    assert ready["type"] == "connection.ready"
    assert ready["user_id"] == me["id"]
    assert ready["conversations"] == [conversation["id"]]


def test_registry_keeps_every_socket_of_a_user(client, me):
    assert hub.count(me["id"]) == 0

    with client.websocket_connect(ws_url(me["token"])) as first:
        first.receive_json()
        assert hub.count(me["id"]) == 1

        with client.websocket_connect(ws_url(me["token"])) as second:
            second.receive_json()
            assert hub.count(me["id"]) == 2

        assert hub.count(me["id"]) == 1

    assert hub.count(me["id"]) == 0


def test_message_sent_over_rest_reaches_the_peer(client, me, other, conversation):
    with client.websocket_connect(ws_url(other["token"])) as websocket:
        websocket.receive_json()  # connection.ready

        response = send(client, conversation["id"], me["headers"], "hello over rest", "k1")
        event = websocket.receive_json()

    assert response.status_code == 201
    assert event["type"] == "message.created"
    assert event["message"]["body"] == "hello over rest"
    assert event["message"]["seq"] == 1
    assert event["message"]["sender_id"] == me["id"]


def test_every_socket_of_the_receiver_gets_the_frame(client, me, other, conversation):
    with client.websocket_connect(ws_url(other["token"])) as phone:
        phone.receive_json()
        with client.websocket_connect(ws_url(other["token"])) as laptop:
            laptop.receive_json()

            send(client, conversation["id"], me["headers"], "to both", "k2")

            assert phone.receive_json()["type"] == "message.created"
            assert laptop.receive_json()["type"] == "message.created"


def test_sender_does_not_receive_their_own_message(client, me, conversation):
    with client.websocket_connect(ws_url(me["token"])) as websocket:
        websocket.receive_json()

        send(client, conversation["id"], me["headers"], "mine only", "k3")

        # If the sender's own message had been queued, it would arrive first.
        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}


def test_non_member_receives_nothing(client, me, conversation, account):
    stranger = account("salim@example.com", "Salim")

    with client.websocket_connect(ws_url(stranger["token"])) as websocket:
        websocket.receive_json()

        send(client, conversation["id"], me["headers"], "private", "k4")

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}


def test_unknown_event_and_bad_frame_keep_the_socket_open(client, me):
    with client.websocket_connect(ws_url(me["token"])) as websocket:
        websocket.receive_json()

        websocket.send_text("this is not json")
        assert websocket.receive_json()["code"] == "bad_frame"

        websocket.send_json({"type": "message.send"})
        unknown = websocket.receive_json()
        assert unknown["type"] == "error"
        assert unknown["code"] == "unknown_event"

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}


def test_a_failed_send_emits_no_frame(client, me, other, conversation, account):
    stranger = account("salim@example.com", "Salim")

    with client.websocket_connect(ws_url(other["token"])) as websocket:
        websocket.receive_json()

        rejected = send(client, conversation["id"], stranger["headers"], "ghost", "k5")
        send(client, conversation["id"], me["headers"], "real", "k6")
        event = websocket.receive_json()

    assert rejected.status_code == 404
    assert event["message"]["body"] == "real"


def test_replaying_a_client_msg_id_does_not_broadcast_twice(client, me, other, conversation):
    with client.websocket_connect(ws_url(other["token"])) as websocket:
        websocket.receive_json()

        send(client, conversation["id"], me["headers"], "once", "same-key")
        send(client, conversation["id"], me["headers"], "once", "same-key")
        assert websocket.receive_json()["message"]["body"] == "once"

        websocket.send_json({"type": "ping"})
        assert websocket.receive_json() == {"type": "pong"}
