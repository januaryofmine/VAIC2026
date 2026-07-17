#!/usr/bin/env bash
# Slice 1 acceptance check: schema created + pgvector OK.
# Runs against host psql if available, otherwise falls back to `docker exec`
# into the vaic2026-postgres container.
#   Usage: source .env && ./db/verify.sh
set -euo pipefail

CONTAINER="${PG_CONTAINER:-vaic2026-postgres}"

# Pick a way to run SQL: prefer host psql + DATABASE_URL, else docker exec.
if command -v psql >/dev/null 2>&1 && [[ -n "${DATABASE_URL:-}" ]]; then
  run_sql() { psql "$DATABASE_URL" -tAc "$1"; }
  echo "using host psql"
elif command -v docker >/dev/null 2>&1; then
  run_sql() { docker exec "$CONTAINER" psql -U "${POSTGRES_USER:-paperless}" -d "${POSTGRES_DB:-paperless}" -tAc "$1"; }
  echo "using docker exec ($CONTAINER)"
else
  echo "neither psql nor docker available" >&2; exit 2
fi

fail=0
check() {  # check "<label>" "<sql>" "<expected substring>"
  local label="$1" sql="$2" want="$3" got
  got="$(run_sql "$sql" 2>&1 | tr -d '[:space:]')"
  if [[ "$got" == *"$want"* ]]; then
    echo "PASS  $label ($got)"
  else
    echo "FAIL  $label — want '$want', got '$got'"; fail=1
  fi
}

check "pgvector extension"        "SELECT extname FROM pg_extension WHERE extname='vector'"                                                                             "vector"
check "documents table"          "SELECT to_regclass('public.documents')"                                                                                              "documents"
check "chunks table"             "SELECT to_regclass('public.chunks')"                                                                                                 "chunks"
check "chat_sessions table"      "SELECT to_regclass('public.chat_sessions')"                                                                                          "chat_sessions"
check "chat_messages table"      "SELECT to_regclass('public.chat_messages')"                                                                                          "chat_messages"
check "chunks.document_id column" "SELECT count(*) FROM information_schema.columns WHERE table_name='chunks' AND column_name='document_id'"                            "1"
check "chunks.page column"       "SELECT count(*) FROM information_schema.columns WHERE table_name='chunks' AND column_name='page'"                                    "1"
check "chunks.section column"    "SELECT count(*) FROM information_schema.columns WHERE table_name='chunks' AND column_name='section'"                                 "1"
check "embedding is vector(1024)" "SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid='public.chunks'::regclass AND attname='embedding'"        "vector(1024)"
check "HNSW embedding index"     "SELECT indexname FROM pg_indexes WHERE tablename='chunks' AND indexname='chunks_embedding_idx'"                                      "chunks_embedding_idx"
check "document_id index"        "SELECT indexname FROM pg_indexes WHERE tablename='chunks' AND indexname='chunks_document_position_idx'"                              "chunks_document_position_idx"

echo "---"
if [[ "$fail" -eq 0 ]]; then echo "ALL PASS"; else echo "FAILED"; exit 1; fi
