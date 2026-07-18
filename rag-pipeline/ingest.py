"""Orchestrate ingestion: file -> parse -> chunk -> embed -> Postgres.

Runs when a user uploads a document. On any failure the document row is marked
'failed' rather than left dangling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg

import db
from chunk import chunk_blocks
from config import config as cfg
from embed import E5Embedder, Embedder
from parse import parse
from storage import BlobStorage, sha256_file


def ingest(
    path: str | Path, conn, embedder: Embedder, storage: BlobStorage | None = None
) -> str:
    p = Path(path)
    doc_type = p.suffix.lower().lstrip(".")
    storage = storage or BlobStorage()

    # Dedup: an identical file already ingested → reuse it (no new row, no re-embed).
    content_hash = sha256_file(p)
    existing = db.find_document_by_hash(conn, content_hash)
    if existing:
        print(f"document_id={existing}", flush=True)
        print("[ingest] reused existing document (dedup)", flush=True)
        return existing

    # Persist the original file (blob) so it can be displayed later, then create the
    # row FIRST (status='pending') so the id exists immediately for an async caller.
    storage_path = storage.save(content_hash, doc_type, p)
    try:
        doc_id = db.insert_document(
            conn,
            p.name,
            doc_type,
            status="pending",
            content_hash=content_hash,
            storage_path=storage_path,
            size_bytes=p.stat().st_size,
        )
    except psycopg.errors.UniqueViolation:
        # Lost a concurrent double-upload race: another ingest inserted the same
        # content_hash first (blocked by the partial unique index). Reuse that row.
        conn.rollback()
        doc_id = db.find_document_by_hash(conn, content_hash)
        print(f"document_id={doc_id}", flush=True)
        print("[ingest] lost dedup race, reused existing (dedup)", flush=True)
        return doc_id
    print(f"document_id={doc_id}", flush=True)  # emit early for async upload

    try:
        db.set_status(conn, doc_id, "parsing")
        parsed = parse(p)
        db.update_page_count(conn, doc_id, parsed.page_count)
        chunks = chunk_blocks(parsed.blocks)
        if not chunks:
            raise ValueError(f"No text extracted from {p}")

        db.set_status(conn, doc_id, "embedding")
        embeddings = embedder.embed_documents([c.text for c in chunks])
        db.insert_chunks(conn, doc_id, chunks, embeddings)
        db.set_status(conn, doc_id, "ready")
    except Exception:
        db.set_status(conn, doc_id, "failed")
        raise
    return doc_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a PDF/DOCX into Postgres/pgvector"
    )
    parser.add_argument("file", help="Path to a .pdf or .docx file")
    args = parser.parse_args()

    if not cfg.database_url:
        print("DATABASE_URL not set — `source ../.env` first", file=sys.stderr)
        sys.exit(1)

    conn = db.connect(cfg.database_url)
    try:
        doc_id = ingest(args.file, conn, E5Embedder())
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*), count(page), count(section) "
                "FROM chunks WHERE document_id = %s",
                (doc_id,),
            )
            total, with_page, with_section = cur.fetchone()
        print(
            f"[ingest done] chunks={total}  "
            f"with_page={with_page}  with_section={with_section}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
