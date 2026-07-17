"""Insert documents + chunks into Postgres/pgvector."""

from __future__ import annotations

import psycopg
from pgvector.psycopg import register_vector

from chunk import Chunk

_INSERT_CHUNK_SQL = """
    INSERT INTO chunks (document_id, position, page, section, text, embedding)
    VALUES (%(document_id)s, %(position)s, %(page)s, %(section)s, %(text)s, %(embedding)s)
"""


def connect(database_url: str) -> psycopg.Connection:
    conn = psycopg.connect(database_url)
    register_vector(conn)  # lets psycopg adapt list[float] <-> vector
    return conn


def insert_document(
    conn: psycopg.Connection,
    filename: str,
    doc_type: str,
    page_count: int | None = None,
    status: str = "pending",
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (filename, doc_type, page_count, status) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (filename, doc_type, page_count, status),
        )
        doc_id = cur.fetchone()[0]
    conn.commit()
    return str(doc_id)


def update_page_count(
    conn: psycopg.Connection, document_id: str, page_count: int | None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE documents SET page_count = %s WHERE id = %s",
            (page_count, document_id),
        )
    conn.commit()


def insert_chunks(
    conn: psycopg.Connection,
    document_id: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    batch_size: int = 100,
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )
    rows = [
        {
            "document_id": document_id,
            "position": c.position,
            "page": c.page,
            "section": c.section,
            "text": c.text,
            "embedding": emb,
        }
        for c, emb in zip(chunks, embeddings)
    ]
    inserted = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            cur.executemany(_INSERT_CHUNK_SQL, batch)
            inserted += len(batch)
    conn.commit()
    return inserted


def set_status(conn: psycopg.Connection, document_id: str, status: str) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE documents SET status = %s WHERE id = %s", (status, document_id))
    conn.commit()
