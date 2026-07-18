"""Integration: chat-history persistence against a live Postgres."""

import os

import psycopg
import pytest

from app.services.chat import append_chat_message, get_or_create_session, list_chat_messages

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg.connect(_DB_URL)
    yield c
    c.close()


@pytest.fixture
def doc(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, status) "
            "VALUES ('chat.pdf','pdf','ready') RETURNING id"
        )
        doc_id = str(cur.fetchone()[0])
    conn.commit()
    yield doc_id
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))  # cascades sessions+messages
    conn.commit()


def test_empty_for_new_document(conn, doc):
    assert list_chat_messages(conn, doc) == []


def test_append_then_list_in_order(conn, doc):
    append_chat_message(conn, doc, "m1", "user", [{"type": "text", "text": "Điều 1?"}])
    append_chat_message(
        conn, doc, "m2", "assistant",
        [{"type": "text", "text": "Trả lời…"}], {"sources": [{"page": 3}]},
    )
    msgs = list_chat_messages(conn, doc)
    assert [m["id"] for m in msgs] == ["m1", "m2"]
    assert msgs[0]["role"] == "user"
    assert msgs[1]["metadata"] == {"sources": [{"page": 3}]}


def test_dedup_on_message_id(conn, doc):
    append_chat_message(conn, doc, "dup", "user", [{"type": "text", "text": "x"}])
    append_chat_message(conn, doc, "dup", "user", [{"type": "text", "text": "x again"}])
    msgs = list_chat_messages(conn, doc)
    assert len(msgs) == 1  # ON CONFLICT (id) DO NOTHING


def test_single_session_reused_per_document(conn, doc):
    s1 = get_or_create_session(conn, doc)
    append_chat_message(conn, doc, "m1", "user", [{"type": "text", "text": "a"}])
    s2 = get_or_create_session(conn, doc)
    assert s1 == s2  # one session per document
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM chat_sessions WHERE document_id = %s", (doc,))
        assert cur.fetchone()[0] == 1
