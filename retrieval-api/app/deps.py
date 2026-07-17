import psycopg
from pgvector.psycopg import register_vector

from app.config import get_settings


def get_db():
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        register_vector(conn)  # adapt list[float] <-> vector for retrieval.py
        yield conn
