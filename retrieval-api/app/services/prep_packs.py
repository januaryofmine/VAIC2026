"""Prep-pack cache (Slice 14a): store the LLM summary/terms/questions per document.

Computed once by the BFF (Claude map-reduce), then reused so re-opens are instant,
free, and work even when the Anthropic balance is empty.
"""

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

_KINDS = ("summary", "terms", "questions")

_GET_SQL = """
    SELECT d.id::text AS document_id, d.filename,
           p.summary, p.terms, p.questions
    FROM documents d
    LEFT JOIN prep_packs p ON p.document_id = d.id
    WHERE d.id = %(id)s::uuid
"""


def get_prep_pack(conn: psycopg.Connection, document_id: str) -> dict | None:
    """Cached prep-pack for a document (any uncomputed kind is NULL), or None if no such doc."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_GET_SQL, {"id": document_id})
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_prep_pack(conn: psycopg.Connection, document_id: str, kind: str, value) -> None:
    """Store one computed kind. `kind` is whitelisted so it can be interpolated safely."""
    if kind not in _KINDS:
        raise ValueError(f"invalid prep-pack kind: {kind!r}")
    sql = (
        f"INSERT INTO prep_packs (document_id, {kind}) VALUES (%(id)s::uuid, %(value)s) "
        f"ON CONFLICT (document_id) DO UPDATE SET {kind} = %(value)s, updated_at = now()"
    )
    with conn.cursor() as cur:
        cur.execute(sql, {"id": document_id, "value": Jsonb(value)})
    conn.commit()
