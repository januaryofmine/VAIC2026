"""User upsert — called by the BFF after GitHub OAuth (Slice 18).

The internal UUID is the stable owner key for documents; github_id is the upsert key.
"""

import psycopg
from psycopg.rows import dict_row

_UPSERT_SQL = """
    INSERT INTO users (github_id, username, name, avatar_url)
    VALUES (%(github_id)s, %(username)s, %(name)s, %(avatar_url)s)
    ON CONFLICT (github_id) DO UPDATE SET
        username = EXCLUDED.username,
        name = EXCLUDED.name,
        avatar_url = EXCLUDED.avatar_url,
        last_login_at = now()
    RETURNING id::text, github_id, username, name, avatar_url
"""


def upsert_user(
    conn: psycopg.Connection,
    github_id: int,
    username: str,
    name: str | None,
    avatar_url: str | None,
) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            _UPSERT_SQL,
            {"github_id": github_id, "username": username, "name": name, "avatar_url": avatar_url},
        )
        row = cur.fetchone()
    conn.commit()
    return dict(row)
