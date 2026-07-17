"""Integration: hybrid retrieval (vector + full-text + RRF) against a live Postgres.

embed_query is monkeypatched to a fixed vector so the vector arm is deterministic;
the keyword arm runs real Postgres full-text search on the fixture text.
"""

import math
import os
import uuid

import psycopg
import pytest
from pgvector.psycopg import register_vector

import app.services.retrieval as retrieval_mod
from app.services.retrieval import retrieve

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")


def _emb(a: float) -> list[float]:
    """Unit vector [1, a, 0...]; larger `a` = lower cosine to the query vector _emb(0)."""
    v = [0.0] * 1024
    v[0] = 1.0
    v[1] = float(a)
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg.connect(_DB_URL)
    register_vector(c)
    yield c
    c.close()


@pytest.fixture
def doc(conn):
    """One doc: a keyword-only chunk (far in vector space), a vector-closest chunk,
    a tiny noise chunk, and 10 distractors that outrank the keyword chunk on vectors."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, page_count, status) "
            "VALUES ('h.pdf', 'pdf', 1, 'ready') RETURNING id"
        )
        did = cur.fetchone()[0]
        rows = [
            (0, 2, "Điều 1", "QUAN ĐIỂM chỉ đạo xuyên suốt của quyết định này", _emb(10)),
            (1, 3, "Điều 2", "nội dung chung không chứa từ khóa mục tiêu nào", _emb(0)),
            (2, 1, None, "x", _emb(0)),  # tiny → filtered by min_chunk_chars
        ]
        rows += [
            (p, 4, "Điều 3", f"đoạn văn phân tán số {p} về hạ tầng giao thông", _emb(1))
            for p in range(3, 13)
        ]
        for pos, page, sec, txt, emb in rows:
            cur.execute(
                "INSERT INTO chunks (document_id, position, page, section, text, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (did, pos, page, sec, txt, emb),
            )
    conn.commit()
    yield did
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (did,))
    conn.commit()


def test_keyword_arm_surfaces_literal_match(conn, doc, monkeypatch):
    # Vector arm ranks pos0 last (10 distractors outrank it); only the keyword arm
    # can pull "QUAN ĐIỂM" into the top-k → proves hybrid works.
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _emb(0))
    rows = retrieve(conn, "Quan điểm chỉ đạo là gì?", str(doc), top_k=5)
    assert 0 in {r["position"] for r in rows}


def test_tiny_chunks_excluded(conn, doc, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _emb(0))
    rows = retrieve(conn, "nội dung mục tiêu", str(doc), top_k=20)
    assert all(len(r["text"].strip()) >= 30 for r in rows)
    assert 2 not in {r["position"] for r in rows}  # the "x" chunk


def test_scoped_with_citation_and_no_results(conn, doc, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _emb(0))
    rows = retrieve(conn, "hạ tầng giao thông", str(doc), top_k=10)
    assert rows and all(r["page"] is not None and r["section"] for r in rows)
    assert retrieve(conn, "bất kỳ", str(uuid.uuid4()), top_k=5) == []


def test_scores_descending(conn, doc, monkeypatch):
    monkeypatch.setattr(retrieval_mod, "embed_query", lambda q: _emb(0))
    scores = [r["score"] for r in retrieve(conn, "hạ tầng giao thông", str(doc), top_k=10)]
    assert scores == sorted(scores, reverse=True)
