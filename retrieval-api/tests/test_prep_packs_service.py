"""Integration: prep-pack cache upsert/get against a live Postgres."""

import os
import uuid

import psycopg
import pytest

from app.services.prep_packs import get_prep_pack, upsert_prep_pack

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
            "VALUES ('pp.pdf','pdf','ready') RETURNING id"
        )
        doc_id = str(cur.fetchone()[0])
    conn.commit()
    yield doc_id
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))  # cascades prep_packs
    conn.commit()


def test_get_is_null_before_compute(conn, doc):
    row = get_prep_pack(conn, doc)
    assert row["filename"] == "pp.pdf"
    assert row["summary"] is None and row["terms"] is None and row["questions"] is None


def test_upsert_then_get_returns_cached(conn, doc):
    upsert_prep_pack(conn, doc, "summary", {"context": "abc", "points": [1, 2]})
    upsert_prep_pack(conn, doc, "terms", [{"term": "GRDP", "def": "…"}])
    row = get_prep_pack(conn, doc)
    assert row["summary"] == {"context": "abc", "points": [1, 2]}
    assert row["terms"] == [{"term": "GRDP", "def": "…"}]
    assert row["questions"] is None  # not computed yet

    # re-upsert summary → replaces, keeps terms
    upsert_prep_pack(conn, doc, "summary", {"context": "xyz"})
    row = get_prep_pack(conn, doc)
    assert row["summary"] == {"context": "xyz"}
    assert row["terms"] == [{"term": "GRDP", "def": "…"}]


def test_invalid_kind_rejected(conn, doc):
    with pytest.raises(ValueError):
        upsert_prep_pack(conn, doc, "summary; DROP TABLE prep_packs", {"x": 1})


def test_get_none_for_missing_document(conn):
    assert get_prep_pack(conn, str(uuid.uuid4())) is None
