"""Vector search for Q&A — cosine top-k, ALWAYS scoped to one document.

Contrast with documents.py (plain-fetch full doc). Here we embed the query and
rank by similarity, returning page/section so the answer can cite them.
"""

import psycopg
from psycopg.rows import dict_row

from app.services.embedding import embed_query

# Scope by document_id is mandatory: never mix chunks across uploaded documents.
# %(vector)s::vector cast: the list param arrives as double precision[]; the `<=>`
# operator has no type context (unlike an INSERT into a vector column), so cast it.
_SEARCH_SQL = """
    SELECT
        id::text, position, page, section, text,
        1 - (embedding <=> %(vector)s::vector) AS score
    FROM chunks
    WHERE document_id = %(document_id)s::uuid
    ORDER BY embedding <=> %(vector)s::vector
    LIMIT %(limit)s
"""


def retrieve(
    conn: psycopg.Connection,
    question: str,
    document_id: str,
    top_k: int,
) -> list[dict]:
    vector = embed_query(question)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            _SEARCH_SQL,
            {"vector": vector, "document_id": document_id, "limit": top_k},
        )
        return [dict(row) for row in cur.fetchall()]
