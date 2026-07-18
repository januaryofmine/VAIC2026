"""Unit: ingest() fires on_created(doc_id) as soon as the document row exists,
BEFORE the slow embedding step — so an async HTTP caller (B3) can return the id
early and let the client poll status. Fully mocked; no live DB or model."""

import db
import ingest
from parse import Block, ParsedDoc
from tests.fakes import FakeEmbedder


class _Storage:
    def save(self, content_hash: str, doc_type: str, path) -> str:
        return f"/blob/{content_hash}.{doc_type}"


def _wire(monkeypatch, order):
    """Patch every DB / parse touchpoint so ingest() runs without Postgres."""
    monkeypatch.setattr(ingest, "sha256_file", lambda p: "hash-xyz")
    monkeypatch.setattr(db, "find_document_by_hash", lambda *a, **k: None)
    monkeypatch.setattr(db, "insert_document", lambda *a, **k: "doc-123")
    monkeypatch.setattr(
        ingest,
        "parse",
        lambda p: ParsedDoc(
            blocks=(Block("Điều 1. " + "nội dung. " * 20, page=1, section="Điều 1"),),
            page_count=1,
        ),
    )
    monkeypatch.setattr(db, "set_status", lambda c, i, s: order.append(("status", s)))
    monkeypatch.setattr(db, "update_page_count", lambda *a, **k: None)
    monkeypatch.setattr(db, "insert_chunks", lambda *a, **k: order.append(("chunks",)))


def test_on_created_fires_once_with_doc_id(monkeypatch, tmp_path):
    order: list = []
    _wire(monkeypatch, order)
    created: list[str] = []
    f = tmp_path / "x.pdf"
    f.write_bytes(b"x")

    got = ingest.ingest(
        str(f), conn=object(), embedder=FakeEmbedder(), storage=_Storage(),
        user_id="u1", on_created=lambda did: created.append(did),
    )

    assert got == "doc-123"
    assert created == ["doc-123"]  # fired exactly once, with the real id


def test_on_created_fires_before_embedding(monkeypatch, tmp_path):
    order: list = []
    _wire(monkeypatch, order)
    f = tmp_path / "x.pdf"
    f.write_bytes(b"x")

    ingest.ingest(
        str(f), conn=object(), embedder=FakeEmbedder(), storage=_Storage(),
        on_created=lambda did: order.append(("created", did)),
    )

    # The callback must land before chunks are inserted (embedding phase).
    assert ("created", "doc-123") in order
    assert order.index(("created", "doc-123")) < order.index(("chunks",))


def test_ingest_without_callback_still_works(monkeypatch, tmp_path):
    # Backward-compat: on_created is optional (CLI path passes nothing).
    order: list = []
    _wire(monkeypatch, order)
    f = tmp_path / "x.pdf"
    f.write_bytes(b"x")
    assert ingest.ingest(str(f), conn=object(), embedder=FakeEmbedder(), storage=_Storage()) == "doc-123"
