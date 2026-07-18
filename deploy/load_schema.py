"""Connect to Supabase (pooler, IPv4) and load db/init.sql. Determines the working
pooler host, then writes DATABASE_URL back to the secrets file.

Password is read from the secrets file (never passed on the command line).

Usage:
    python deploy/load_schema.py --ref <ref> --region <region> --secrets <path>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]


def read_secret(secrets: Path, key: str) -> str | None:
    if not secrets.exists():
        return None
    for line in secrets.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    return None


def write_secret(secrets: Path, key: str, value: str) -> None:
    lines = []
    if secrets.exists():
        lines = [l for l in secrets.read_text(encoding="utf-8").splitlines()
                 if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    secrets.write_text("\n".join(lines) + "\n", encoding="utf-8")


def split_statements(sql: str) -> list[str]:
    # Strip `-- ...` line comments first (some contain ';', which would break a
    # naive split), then split on ';'. init.sql has no ';' inside string literals.
    no_comments = "\n".join(re.sub(r"--.*$", "", line) for line in sql.splitlines())
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def try_connect(url: str):
    return psycopg.connect(url, connect_timeout=10, autocommit=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--region", required=True)
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--initsql", default=str(ROOT / "db" / "init.sql"))
    ap.add_argument("--port", default="5432")  # 5432 session pooler
    ap.add_argument("--dim", type=int, default=None,
                    help="override embedding vector dim (e.g. 768 for Gemini)")
    ap.add_argument("--drop", action="store_true",
                    help="DROP existing tables first (needed when changing --dim)")
    args = ap.parse_args()

    secrets = Path(args.secrets)
    pw = read_secret(secrets, "SUPABASE_DB_PASSWORD")
    if not pw:
        print("ERROR: SUPABASE_DB_PASSWORD not in secrets file", file=sys.stderr)
        return 1

    user = f"postgres.{args.ref}"
    candidates = [
        f"postgresql://{user}:{pw}@aws-0-{args.region}.pooler.supabase.com:{args.port}/postgres",
        f"postgresql://{user}:{pw}@aws-1-{args.region}.pooler.supabase.com:{args.port}/postgres",
    ]

    conn = None
    working = None
    for url in candidates:
        host = re.search(r"@([^:]+)", url).group(1)
        try:
            conn = try_connect(url)
            working = url
            print(f"connected via {host}:{args.port}")
            break
        except Exception as e:
            print(f"  {host}: {type(e).__name__}: {str(e)[:80]}")
    if not conn:
        print("ERROR: could not connect to any pooler host", file=sys.stderr)
        return 2

    sql = Path(args.initsql).read_text(encoding="utf-8")
    if args.dim:
        sql = re.sub(r"vector\(\d+\)", f"vector({args.dim})", sql)
        print(f"schema vector dim -> {args.dim}")
    with conn.cursor() as cur:
        if args.drop:
            cur.execute(
                "DROP TABLE IF EXISTS chat_messages, chat_sessions, chunks, documents CASCADE"
            )
            print("dropped existing tables")
        for st in split_statements(sql):
            cur.execute(st)
    # verify
    with conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1")
        tables = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT extname FROM pg_extension WHERE extname='vector'")
        has_vec = cur.fetchone() is not None
    conn.close()

    write_secret(secrets, "DATABASE_URL", working)
    masked = re.sub(r":([^:@]+)@", ":***@", working)
    print(f"schema loaded. pgvector={has_vec} tables={tables}")
    print(f"DATABASE_URL (masked) = {masked}")
    print("DATABASE_URL saved to secrets file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
