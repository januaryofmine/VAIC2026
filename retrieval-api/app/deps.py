import psycopg

from app.config import get_settings


def get_db():
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        yield conn
