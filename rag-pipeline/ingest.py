"""Orchestrate ingestion: file -> parse -> chunk -> embed -> Postgres.

Runs when a user uploads a document. On any failure the document row is marked
'failed' rather than left dangling.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import db
from chunk import chunk_blocks
from config import config as cfg
from embed import E5Embedder, Embedder
from parse import parse


def ingest(path: str | Path, conn, embedder: Embedder) -> str:
    p = Path(path)
    doc_type = p.suffix.lower().lstrip(".")

    # Create the row FIRST (status='pending') so the id exists immediately and an
    # async caller can return right away; heavy work then updates status.
    doc_id = db.insert_document(conn, p.name, doc_type, status="pending")
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
