"""Plain-fetch a full document's chunks — NO embedding, NO vector search.

This is the prep-pack data path (summarize / terms / questions): they need the
whole document in reading order, not a semantic top-k. Contrast with retrieval.py
(Slice 4), which does the vector search for Q&A.
"""

import psycopg
from psycopg.rows import dict_row

_DOC_SQL = """
    SELECT id::text, filename, doc_type, page_count, status
    FROM documents
    WHERE id = %(id)s::uuid
"""

# Deliberately does NOT select `embedding`: consumers get text + citation metadata,
# ordered by position — plain sequential fetch, no similarity.
_CHUNKS_SQL = """
    SELECT id::text, position, page, section, text
    FROM chunks
    WHERE document_id = %(id)s::uuid
    ORDER BY position
"""


_STATUS_SQL = """
    SELECT
        d.id::text AS document_id, d.filename, d.doc_type, d.status, d.page_count,
        (SELECT count(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count
    FROM documents d
    WHERE d.id = %(id)s::uuid
"""


def fetch_document_status(conn: psycopg.Connection, document_id: str) -> dict | None:
    """Lightweight status for polling during async ingestion (no chunk text)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_STATUS_SQL, {"id": document_id})
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_full_document(conn: psycopg.Connection, document_id: str) -> dict | None:
    """Return {document fields..., "chunks": [...]} or None if the document is absent."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_DOC_SQL, {"id": document_id})
        doc = cur.fetchone()
        if doc is None:
            return None
        cur.execute(_CHUNKS_SQL, {"id": document_id})
        chunks = [dict(row) for row in cur.fetchall()]
    return {**doc, "chunks": chunks}
