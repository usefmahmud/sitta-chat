"""Messages: seq assignment, idempotency, keyset pagination, concurrency."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models import Message


def send(
    client: TestClient,
    conversation_id: str,
    headers: dict,
    body: str = "hello",
    client_msg_id: str | None = None,
):
    payload: dict[str, str] = {"body": body}
    if client_msg_id is not None:
        payload["client_msg_id"] = client_msg_id
    return client.post(
        f"/api/conversations/{conversation_id}/messages",
        json=payload,
        headers=headers,
    )


def thread_url(conversation_id: str) -> str:
    return f"/api/conversations/{conversation_id}/messages"


def test_send_returns_201_with_a_seq(client, me, conversation):
    response = send(client, conversation["id"], me["headers"], "first message")

    assert response.status_code == 201
    body = response.json()
    assert body["seq"] == 1
    assert body["sender_id"] == me["id"]
    assert body["conversation_id"] == conversation["id"]
    assert body["body"] == "first message"
    assert set(body) == {
        "id",
        "conversation_id",
        "sender_id",
        "seq",
        "body",
        "client_msg_id",
        "created_at",
    }


def test_seq_increments_by_one_per_conversation(client, me, other, conversation):
    first = send(client, conversation["id"], me["headers"], "one")
    second = send(client, conversation["id"], other["headers"], "two")
    third = send(client, conversation["id"], me["headers"], "three")

    assert [r.json()["seq"] for r in (first, second, third)] == [1, 2, 3]
    assert second.json()["sender_id"] == other["id"]


def test_seq_is_per_conversation_not_global(client, me, other, account):
    other_room = client.post(
        "/api/conversations",
        json={"peer_id": account("salim@example.com", "Salim")["id"]},
        headers=me["headers"],
    ).json()

    send(client, other_room["id"], me["headers"], "elsewhere")
    response = send(client, other_room["id"], me["headers"], "again")

    assert response.json()["seq"] == 2


def test_same_client_msg_id_returns_the_original(client, me, conversation):
    first = send(client, conversation["id"], me["headers"], "retry me", "c-1")
    second = send(client, conversation["id"], me["headers"], "retry me", "c-1")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    page = client.get(thread_url(conversation["id"]), headers=me["headers"]).json()
    assert len(page["items"]) == 1


def test_blank_and_whitespace_bodies_are_rejected(client, me, conversation):
    assert send(client, conversation["id"], me["headers"], "").status_code == 422
    assert send(client, conversation["id"], me["headers"], "   \n\t ").status_code == 422


def test_body_over_4000_chars_is_rejected(client, me, conversation):
    response = send(client, conversation["id"], me["headers"], "x" * 4001)

    assert response.status_code == 422


def test_non_member_gets_404(client, me, conversation, account):
    stranger = account("salim@example.com", "Salim")

    assert send(client, conversation["id"], stranger["headers"], "hi").status_code == 404
    assert (
        client.get(thread_url(conversation["id"]), headers=stranger["headers"]).status_code
        == 404
    )


def test_unknown_conversation_returns_404(client, me):
    assert (
        client.get(thread_url("does-not-exist"), headers=me["headers"]).status_code == 404
    )


def test_messages_require_authentication(client, conversation):
    assert send(client, conversation["id"], {}, "hi").status_code == 401
    assert client.get(thread_url(conversation["id"])).status_code == 401


def _bulk_insert(conversation_id: str, sender_id: str, count: int) -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                Message(
                    conversation_id=conversation_id,
                    sender_id=sender_id,
                    seq=seq,
                    body=f"message {seq}",
                )
                for seq in range(1, count + 1)
            ]
        )
        db.commit()


def test_pagination_walks_120_messages_exactly_once(client, me, conversation):
    _bulk_insert(conversation["id"], me["id"], 120)

    seen: list[int] = []
    before: int | None = None
    pages = 0

    while True:
        params: dict[str, int] = {"limit": 30}
        if before is not None:
            params["before_seq"] = before
        response = client.get(
            thread_url(conversation["id"]), params=params, headers=me["headers"]
        )
        assert response.status_code == 200
        page = response.json()
        seqs = [m["seq"] for m in page["items"]]

        assert seqs == sorted(seqs, reverse=True), "a page is newest-first"
        seen.extend(seqs)
        pages += 1

        if not page["has_more"]:
            break
        before = page["next_before_seq"]
        assert before is not None

    assert pages == 4
    assert sorted(seen) == list(range(1, 121))
    assert len(seen) == len(set(seen))


def test_default_limit_is_30_and_max_is_100(client, me, conversation):
    _bulk_insert(conversation["id"], me["id"], 40)

    default_page = client.get(
        thread_url(conversation["id"]), headers=me["headers"]
    ).json()
    assert len(default_page["items"]) == 30
    assert default_page["has_more"] is True

    assert (
        client.get(
            thread_url(conversation["id"]), params={"limit": 101}, headers=me["headers"]
        ).status_code
        == 422
    )


def test_after_seq_replays_newer_messages_in_order(client, me, conversation):
    _bulk_insert(conversation["id"], me["id"], 10)

    page = client.get(
        thread_url(conversation["id"]),
        params={"after_seq": 7},
        headers=me["headers"],
    ).json()

    assert [m["seq"] for m in page["items"]] == [8, 9, 10]


def test_last_message_at_and_preview_are_updated(client, me, conversation):
    send(client, conversation["id"], me["headers"], "أهلاً يا صاحبي")

    detail = client.get(
        f"/api/conversations/{conversation['id']}", headers=me["headers"]
    ).json()
    listing = client.get("/api/conversations", headers=me["headers"]).json()

    assert detail["last_message_at"] is not None
    assert listing[0]["id"] == conversation["id"]
    assert listing[0]["last_message_preview"] == "أهلاً يا صاحبي"


def test_concurrent_sends_get_consecutive_unique_seqs(client, me, conversation):
    def post(index: int):
        return send(
            client,
            conversation["id"],
            me["headers"],
            f"concurrent {index}",
            f"client-{index}",
        )

    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(post, range(20)))

    assert [r.status_code for r in responses] == [201] * 20, [
        r.text for r in responses if r.status_code != 201
    ]
    seqs = sorted(r.json()["seq"] for r in responses)
    assert seqs == list(range(1, 21))
