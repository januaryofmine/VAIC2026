import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import get_settings

# A single shared pool for the whole process. Opening a connection to Supabase is
# expensive (cross-region TCP + TLS + auth handshake, ~2.8s from the HF Space), so we
# pay it ONCE at startup and hand out warm, reused connections per request instead of
# reconnecting on every call. Opened in main.py's lifespan; closed on shutdown.
_pool: ConnectionPool | None = None


def _configure(conn: psycopg.Connection) -> None:
    """Run once per physical connection when the pool creates it (not per request):
    register pgvector so list[float] <-> vector adaptation works in retrieval.py."""
    register_vector(conn)


def init_pool() -> None:
    """Open the shared connection pool. Idempotent — safe to call more than once."""
    global _pool
    if _pool is not None:
        return
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,  # keep one warm connection so the first request after startup is fast
        max_size=10,  # conservative cap for the Supabase pooler's connection budget
        configure=_configure,
        check=ConnectionPool.check_connection,  # drop a dead/idle-killed conn instead of handing it out
        open=False,
    )
    pool.open()
    _pool = pool


def close_pool() -> None:
    """Close the shared pool (on app shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def get_db():
    """FastAPI dependency: check out a warm pooled connection. It is returned to the
    pool on exit (NOT closed), so the handshake is not repeated per request. Lazily
    opens the pool if startup has not run (e.g. tests that do not override this dep)."""
    if _pool is None:
        init_pool()
    with _pool.connection() as conn:
        yield conn
