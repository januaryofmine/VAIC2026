"""Persist Q&A chat per document (Slice 14b): one session per document, ordered messages.

Message shape mirrors the AI-SDK UIMessage (id/role/parts/metadata) so the BFF can
save and reload conversations without translation. Re-saving a message id is a no-op.
"""

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

_GET_OR_CREATE_SESSION = """
    INSERT INTO chat_sessions (document_id) VALUES (%(id)s::uuid)
    ON CONFLICT (document_id) WHERE document_id IS NOT NULL
    DO UPDATE SET updated_at = now()
    RETURNING id
"""

_LIST_SQL = """
    SELECT m.id, m.role, m.parts, m.metadata
    FROM chat_messages m
    JOIN chat_sessions s ON s.id = m.session_id
    WHERE s.document_id = %(id)s::uuid
    ORDER BY m.sort_order
"""

_INSERT_SQL = """
    INSERT INTO chat_messages (id, session_id, role, parts, metadata, sort_order)
    VALUES (
        %(mid)s, %(sid)s, %(role)s, %(parts)s, %(metadata)s,
        (SELECT COALESCE(max(sort_order), -1) + 1 FROM chat_messages WHERE session_id = %(sid)s)
    )
    ON CONFLICT (id) DO NOTHING
"""


def get_or_create_session(conn: psycopg.Connection, document_id: str) -> str:
    with conn.cursor() as cur:
        cur.execute(_GET_OR_CREATE_SESSION, {"id": document_id})
        session_id = cur.fetchone()[0]
    conn.commit()
    return str(session_id)


def list_chat_messages(conn: psycopg.Connection, document_id: str) -> list[dict]:
    """Saved messages for a document's chat, in order (empty if none)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(_LIST_SQL, {"id": document_id})
        return [dict(row) for row in cur.fetchall()]


def append_chat_message(
    conn: psycopg.Connection,
    document_id: str,
    message_id: str,
    role: str,
    parts,
    metadata=None,
) -> None:
    """Append one message to the document's session (dedup on message id)."""
    session_id = get_or_create_session(conn, document_id)
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_SQL,
            {
                "mid": message_id,
                "sid": session_id,
                "role": role,
                "parts": Jsonb(parts),
                "metadata": Jsonb(metadata) if metadata is not None else None,
            },
        )
    conn.commit()
