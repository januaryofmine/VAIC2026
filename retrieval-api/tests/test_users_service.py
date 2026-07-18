"""Integration: upsert_user + owner-scoped list_documents against a live Postgres."""

import os

import psycopg
import pytest

from app.services.documents import list_documents
from app.services.users import upsert_user

pytestmark = pytest.mark.integration

_DB_URL = os.environ.get("DATABASE_URL")


@pytest.fixture
def conn():
    if not _DB_URL:
        pytest.skip("DATABASE_URL not set")
    c = psycopg.connect(_DB_URL)
    yield c
    c.close()


def test_upsert_is_idempotent_by_github_id(conn):
    gid = 999000001
    try:
        u1 = upsert_user(conn, gid, "khanh", "Khanh", "http://a/1.png")
        u2 = upsert_user(conn, gid, "khanh-renamed", "Khanh 2", "http://a/2.png")
        assert u1["id"] == u2["id"]          # same row, not a duplicate
        assert u2["username"] == "khanh-renamed"  # fields updated
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE github_id = %s", (gid,))
        conn.commit()


def test_list_is_owner_scoped_and_filterable(conn):
    ua = upsert_user(conn, 999000002, "usera", None, None)
    ub = upsert_user(conn, 999000003, "userb", None, None)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (user_id, filename, doc_type, status) VALUES "
                "(%s,'A1.pdf','pdf','ready'),(%s,'A2.docx','docx','ready'),(%s,'B1.pdf','pdf','ready')",
                (ua["id"], ua["id"], ub["id"]),
            )
        conn.commit()

        a_docs = list_documents(conn, ua["id"])
        assert {d["filename"] for d in a_docs} == {"A1.pdf", "A2.docx"}  # B1 excluded (other owner)

        a_pdf = list_documents(conn, ua["id"], doc_type="pdf")
        assert {d["filename"] for d in a_pdf} == {"A1.pdf"}  # type filter

        a_kw = list_documents(conn, ua["id"], q="A2")
        assert {d["filename"] for d in a_kw} == {"A2.docx"}  # keyword filter
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE github_id IN (999000002, 999000003)")  # cascades docs
        conn.commit()
