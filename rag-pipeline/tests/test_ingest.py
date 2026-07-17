"""Integration: ingest into the live Postgres using a fake embedder (no model).

Verifies the Slice-2 AC contract at the DB layer: every chunk carries
document_id + page + section, and the document ends up 'ready'.
"""

import os

import pytest

import db
import ingest
from parse import Block, ParsedDoc
from tests.fakes import FakeEmbedder

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = db.connect(_DB_URL)
    yield c
    c.close()


def test_ingest_persists_citation_metadata(conn, monkeypatch, tmp_path):
    blocks = (
        Block("Điều 1. " + "nội dung điều một. " * 30, page=1, section="Điều 1"),
        Block("Điều 2. " + "quy định điều hai. " * 30, page=2, section="Điều 2"),
    )
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=blocks, page_count=2))

    f = tmp_path / "sample.pdf"
    f.write_bytes(b"%PDF-1.4 fake")

    doc_id = ingest.ingest(str(f), conn, FakeEmbedder())

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), count(page), count(section) "
                "FROM chunks WHERE document_id = %s",
                (doc_id,),
            )
            total, with_page, with_section = cur.fetchone()
            cur.execute("SELECT status FROM documents WHERE id = %s", (doc_id,))
            status = cur.fetchone()[0]

        assert total >= 2
        assert with_page == total       # every chunk has a page
        assert with_section == total    # every chunk has a section
        assert status == "ready"
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
