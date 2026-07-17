"""Integration: vector search scoping + citation, with embed_query monkeypatched
(so we don't load the 2GB model just to test SQL/scoping)."""

import os

import psycopg
import pytest
from pgvector.psycopg import register_vector

import app.services.retrieval as retrieval_mod
from app.services.retrieval import retrieve

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")


def _vec(seed: int) -> list[float]:
    v = [0.0] * 1024
    v[seed % 1024] = 1.0
    return v


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg.connect(_DB_URL)
    register_vector(c)
    yield c
    c.close()


@pytest.fixture
def two_docs(conn):
    ids: dict[str, object] = {}
    with conn.cursor() as cur:
        for key, base in (("a", 0), ("b", 100)):
            cur.execute(
                "INSERT INTO documents (filename, doc_type, page_count, status) "
                "VALUES (%s, 'pdf', 1, 'ready') RETURNING id",
                (f"{key}.pdf",),
            )
            did = cur.fetchone()[0]
            ids[key] = did
            for pos in range(3):
                cur.execute(
                    "INSERT INTO chunks (document_id, position, page, section, text, embedding) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (did, pos, pos + 1, f"Điều {pos + 1}", f"{key} chunk {pos}", _vec(base + pos)),
                )
    conn.commit()
    yield ids
    with conn.cursor() as cur:
        for did in ids.values():
            cur.execute("DELETE FROM documents WHERE id = %s", (did,))
    conn.commit()


def test_results_scoped_to_document_with_citation(conn, two_docs, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _vec(0))
    rows = retrieve(conn, "bất kỳ", str(two_docs["a"]), top_k=5)
    assert rows, "expected chunks"
    assert all(r["text"].startswith("a chunk") for r in rows)  # only doc a — scoping
    assert all(r["page"] is not None and r["section"] for r in rows)  # citation present
    assert all("score" in r for r in rows)


def test_top_k_limit_respected(conn, two_docs, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _vec(0))
    assert len(retrieve(conn, "x", str(two_docs["a"]), top_k=2)) == 2


def test_scores_descending(conn, two_docs, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _vec(0))
    scores = [r["score"] for r in retrieve(conn, "x", str(two_docs["a"]), top_k=5)]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0, abs=1e-4)  # query == chunk 0's vector


def test_no_results_for_unknown_document(conn, monkeypatch):
    import uuid

    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _vec(0))
    assert retrieve(conn, "x", str(uuid.uuid4()), top_k=5) == []
