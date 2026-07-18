"""Integration: fetch_full_document against a live Postgres."""

import os
import uuid

import psycopg
import pytest
from pgvector.psycopg import register_vector

from app.services.documents import fetch_document_status, fetch_full_document

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")
_ZERO = [0.0] * 1024


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg.connect(_DB_URL)
    register_vector(c)  # only to insert the fixture vector; fetch doesn't touch it
    yield c
    c.close()


def test_returns_chunks_ordered_by_position(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, page_count, status) "
            "VALUES ('t.pdf', 'pdf', 1, 'ready') RETURNING id"
        )
        doc_id = cur.fetchone()[0]
        # insert deliberately out of order: 2, 0, 1
        for pos, text in [(2, "c2"), (0, "c0"), (1, "c1")]:
            cur.execute(
                "INSERT INTO chunks (document_id, position, page, section, text, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (doc_id, pos, 1, "Điều 1", text, _ZERO),
            )
    conn.commit()
    try:
        result = fetch_full_document(conn, str(doc_id))
        assert result is not None
        assert [c["position"] for c in result["chunks"]] == [0, 1, 2]
        assert result["chunks"][0]["section"] == "Điều 1"
        assert "embedding" not in result["chunks"][0]  # never selected
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()


def test_missing_document_returns_none(conn):
    assert fetch_full_document(conn, str(uuid.uuid4())) is None


def test_status_reports_state_and_chunk_count(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, page_count, status) "
            "VALUES ('s.pdf', 'pdf', 3, 'embedding') RETURNING id"
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO chunks (document_id, position, page, section, text, embedding) "
            "VALUES (%s, 0, 1, 'Điều 1', 'x', %s)",
            (doc_id, [0.0] * 1024),
        )
    conn.commit()
    try:
        st = fetch_document_status(conn, str(doc_id))
        assert st["status"] == "embedding"
        assert st["chunk_count"] == 1
        assert st["page_count"] == 3
        assert fetch_document_status(conn, str(uuid.uuid4())) is None
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()


def test_document_with_no_chunks(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, page_count, status) "
            "VALUES ('empty.pdf', 'pdf', 0, 'ready') RETURNING id"
        )
        doc_id = cur.fetchone()[0]
    conn.commit()
    try:
        result = fetch_full_document(conn, str(doc_id))
        assert result is not None
        assert result["chunks"] == []
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
