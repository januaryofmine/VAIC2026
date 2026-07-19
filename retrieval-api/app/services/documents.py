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


_FILE_SQL = """
    SELECT filename, doc_type, storage_path
    FROM documents
    WHERE id = %(id)s::uuid
"""


# Single-purpose ownership lookup for the BFF authorization guard: returns only the
# owner id (never document content), so a foreign document_id can be rejected before
# any data-serving endpoint runs. user_id is NULL for pre-Slice-18 documents.
_OWNER_SQL = """
    SELECT user_id::text AS user_id
    FROM documents
    WHERE id = %(id)s::uuid
"""


def fetch_document_file(conn: psycopg.Connection, document_id: str) -> dict | None:
    """Return {filename, doc_type, storage_path} for serving the original blob, or None."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_FILE_SQL, {"id": document_id})
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_document_owner(conn: psycopg.Connection, document_id: str) -> dict | None:
    """Return {"user_id": str | None} for the document, or None if it does not exist.

    None (no row) and {"user_id": None} (row exists, unowned) are distinct: the router
    maps the former to 404 and the latter to a 200 the BFF treats as "deny".
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_OWNER_SQL, {"id": document_id})
        row = cur.fetchone()
        return dict(row) if row else None


# List "my documents" (Home, Slice 18): owner-scoped, newest first, optional filters.
# to_char gives a stable ISO timestamp the BFF can format for display.
_LIST_SQL = """
    SELECT
        d.id::text AS document_id, d.filename, d.doc_type, d.status, d.page_count,
        (SELECT count(*) FROM chunks c WHERE c.document_id = d.id) AS chunk_count,
        d.size_bytes,
        to_char(d.uploaded_at, 'YYYY-MM-DD"T"HH24:MI:SSOF') AS uploaded_at
    FROM documents d
    WHERE d.user_id = %(user_id)s::uuid
      AND (%(doc_type)s::text IS NULL OR d.doc_type = %(doc_type)s::text)
      AND (%(date_from)s::date IS NULL OR d.uploaded_at >= %(date_from)s::date)
      AND (%(date_to)s::date IS NULL OR d.uploaded_at < (%(date_to)s::date + 1))
      AND (%(q)s::text IS NULL OR d.filename ILIKE '%%' || %(q)s::text || '%%')
    ORDER BY d.uploaded_at DESC
"""


def list_documents(
    conn: psycopg.Connection,
    user_id: str,
    doc_type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    q: str | None = None,
) -> list[dict]:
    """All documents owned by a user, newest first, with optional type/date/keyword filters."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            _LIST_SQL,
            {"user_id": user_id, "doc_type": doc_type, "date_from": date_from,
             "date_to": date_to, "q": q},
        )
        return [dict(row) for row in cur.fetchall()]


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
