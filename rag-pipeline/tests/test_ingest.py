"""Integration: ingest into the live Postgres using a fake embedder (no model).

Verifies the Slice-2 AC contract at the DB layer: every chunk carries
document_id + page + section, and the document ends up 'ready'. Slice 17 adds
blob persistence + content-hash dedup.
"""

import os

import pytest

import db
import ingest
from parse import Block, ParsedDoc
from storage import BlobStorage, sha256_file
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


def _delete(conn, doc_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    conn.commit()


def test_ingest_persists_citation_and_blob_metadata(conn, monkeypatch, tmp_path):
    blocks = (
        Block("Điều 1. " + "nội dung điều một. " * 30, page=1, section="Điều 1"),
        Block("Điều 2. " + "quy định điều hai. " * 30, page=2, section="Điều 2"),
    )
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=blocks, page_count=2))

    # Unique content per run so its hash never collides with a leftover row (dedup).
    f = tmp_path / "sample.pdf"
    f.write_bytes(b"%PDF-1.4 " + str(tmp_path).encode())
    storage = BlobStorage(tmp_path / "store")

    doc_id = ingest.ingest(str(f), conn, FakeEmbedder(), storage=storage)

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), count(page), count(section) FROM chunks WHERE document_id = %s",
                (doc_id,),
            )
            total, with_page, with_section = cur.fetchone()
            cur.execute(
                "SELECT status, content_hash, storage_path, size_bytes "
                "FROM documents WHERE id = %s",
                (doc_id,),
            )
            status, chash, spath, size = cur.fetchone()

        assert total >= 2
        assert with_page == total and with_section == total
        assert status == "ready"
        # Slice 17: blob metadata persisted + the original file actually stored.
        assert chash == sha256_file(f)
        assert size == f.stat().st_size
        assert spath and os.path.isfile(spath)
        assert open(spath, "rb").read() == f.read_bytes()
    finally:
        _delete(conn, doc_id)


def test_ingest_dedups_identical_reupload(conn, monkeypatch, tmp_path):
    blocks = (Block("Điều 1. " + "nội dung. " * 20, page=1, section="Điều 1"),)
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=blocks, page_count=1))
    storage = BlobStorage(tmp_path / "store")

    content = b"%PDF-1.4 dedup " + str(tmp_path).encode()
    f1 = tmp_path / "dup.pdf"
    f1.write_bytes(content)
    id1 = ingest.ingest(str(f1), conn, FakeEmbedder(), storage=storage)

    # Same bytes, different filename → must reuse id1, no second row, chunks not doubled.
    f2 = tmp_path / "dup-again.pdf"
    f2.write_bytes(content)
    id2 = ingest.ingest(str(f2), conn, FakeEmbedder(), storage=storage)

    try:
        assert id2 == id1
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM documents WHERE content_hash = %s", (sha256_file(f1),)
            )
            assert cur.fetchone()[0] == 1  # exactly one document for this content
            cur.execute("SELECT count(*) FROM chunks WHERE document_id = %s", (id1,))
            assert cur.fetchone()[0] == 1  # not re-embedded/doubled
    finally:
        _delete(conn, id1)


def test_ingest_survives_dedup_race(conn, monkeypatch, tmp_path):
    # Simulate the race: the initial dedup check misses (returns None) but another
    # upload already inserted the same content_hash → the partial unique index makes
    # our insert raise, and ingest must recover by reusing the existing row.
    blocks = (Block("Điều 1. " + "nội dung. " * 20, page=1, section="Điều 1"),)
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=blocks, page_count=1))
    storage = BlobStorage(tmp_path / "store")

    content = b"%PDF-1.4 race " + str(tmp_path).encode()
    f = tmp_path / "race.pdf"
    f.write_bytes(content)
    chash = sha256_file(f)

    # Pre-insert the "winner" row with this hash (the concurrent upload that won).
    winner = db.insert_document(conn, "winner.pdf", "pdf", status="pending", content_hash=chash)

    # Dedup pre-check MISSES (returns None) so we reach the insert → unique violation;
    # the recovery re-query then finds the winner.
    calls = {"n": 0}

    def flaky_find(c, h):
        calls["n"] += 1
        return None if calls["n"] == 1 else winner  # miss on pre-check, hit on recovery

    monkeypatch.setattr(db, "find_document_by_hash", flaky_find)

    got = ingest.ingest(str(f), conn, FakeEmbedder(), storage=storage)
    try:
        assert got == winner  # recovered to the racing winner instead of erroring
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM documents WHERE content_hash = %s", (chash,))
            assert cur.fetchone()[0] == 1  # unique index kept it to one row
    finally:
        _delete(conn, winner)


def test_failed_doc_is_not_deduped_can_retry(conn, monkeypatch, tmp_path):
    # First attempt fails (no text) → row 'failed'. Re-uploading the SAME content must
    # NOT dedup to the failed row; it should ingest fresh and succeed.
    storage = BlobStorage(tmp_path / "store")
    content = b"%PDF-1.4 retry " + str(tmp_path).encode()
    f = tmp_path / "retry.pdf"
    f.write_bytes(content)
    chash = sha256_file(f)

    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=(), page_count=0))
    with pytest.raises(ValueError):
        ingest.ingest(str(f), conn, FakeEmbedder(), storage=storage)

    # Second attempt: parse now succeeds.
    blocks = (Block("Điều 1. " + "nội dung. " * 20, page=1, section="Điều 1"),)
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=blocks, page_count=1))
    new_id = ingest.ingest(str(f), conn, FakeEmbedder(), storage=storage)

    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM documents WHERE content_hash = %s ORDER BY uploaded_at",
                (chash,),
            )
            statuses = [r[0] for r in cur.fetchall()]
        assert statuses == ["failed", "ready"]  # a fresh row, not a dedup to the failed one
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE content_hash = %s", (chash,))
        conn.commit()


def test_ingest_marks_failed_when_no_text(conn, monkeypatch, tmp_path):
    # parse yields no blocks → no chunks → ingest raises, and the row it created
    # up front must be left as status='failed' (async caller polls this).
    monkeypatch.setattr(ingest, "parse", lambda _p: ParsedDoc(blocks=(), page_count=0))
    f = tmp_path / "empty-unique-9x.pdf"
    f.write_bytes(b"%PDF empty " + str(tmp_path).encode())
    storage = BlobStorage(tmp_path / "store")

    with pytest.raises(ValueError):
        ingest.ingest(str(f), conn, FakeEmbedder(), storage=storage)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status FROM documents WHERE content_hash = %s", (sha256_file(f),)
        )
        row = cur.fetchone()
    try:
        assert row is not None
        assert row[1] == "failed"
    finally:
        if row:
            _delete(conn, row[0])
