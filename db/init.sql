-- Paperless Meetings (VAIC2026) — DB schema
-- Document/citation-oriented RAG. Adapted from aks-advisor (web-crawl oriented).

CREATE EXTENSION IF NOT EXISTS vector;

-- ── documents ────────────────────────────────────────────────
-- One row per file a user uploads. The ingestion pipeline updates `status`.
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT NOT NULL,
  doc_type TEXT NOT NULL,                    -- 'pdf' | 'docx'
  page_count INTEGER,                        -- page count (PDF); NULL until parsed
  status TEXT NOT NULL DEFAULT 'pending',    -- pending → parsing → embedding → ready | failed
  storage_path TEXT,                         -- absolute path to the original file (blob); NULL until stored
  size_bytes BIGINT,                         -- original file size
  content_hash TEXT,                         -- SHA-256 of file bytes → dedup identical re-uploads
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT documents_doc_type_check CHECK (doc_type IN ('pdf', 'docx')),
  CONSTRAINT documents_status_check
    CHECK (status IN ('pending', 'parsing', 'embedding', 'ready', 'failed'))
);

-- Dedup: identical file re-uploaded → reuse the existing document instead of re-ingesting.
-- UNIQUE (partial) so a concurrent double-upload can't create two rows for the same
-- content; ingest catches the violation and reuses the winner. Excludes 'failed' so a
-- file that failed once can be re-uploaded for a fresh attempt (and NULL hashes, of which
-- there may be many from pre-Slice-17 docs).
CREATE UNIQUE INDEX IF NOT EXISTS documents_content_hash_uniq
  ON documents (content_hash) WHERE content_hash IS NOT NULL AND status <> 'failed';

-- ── chunks ───────────────────────────────────────────────────
-- Heart of citation. Scoped by document_id, carries page (PDF) + section (Điều/Khoản).
CREATE TABLE IF NOT EXISTS chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,  -- scope
  position INTEGER NOT NULL,                 -- order within doc → documents.py ORDER BY position
  page INTEGER,                              -- citation: page number (PDF)
  section TEXT,                              -- citation: 'Điều 5', 'Khoản 2' (legal document)
  text TEXT NOT NULL,
  embedding vector(1024) NOT NULL,           -- multilingual-e5-large (1024-dim)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chunks_document_position_unique UNIQUE (document_id, position)
);

-- Vector search (Q&A via retrieval.py): HNSW cosine.
CREATE INDEX IF NOT EXISTS chunks_embedding_idx
  ON chunks USING hnsw (embedding vector_cosine_ops);
-- Scope + full-doc fetch (documents.py): filter by document_id, ordered by position.
CREATE INDEX IF NOT EXISTS chunks_document_position_idx
  ON chunks (document_id, position);

-- ── chat (Q&A history) ───────────────────────────────────────
-- No auth (internal tool). A session is tied to one document.
CREATE TABLE IF NOT EXISTS chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  title TEXT NOT NULL DEFAULT '(untitled chat)',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_sessions_document_idx
  ON chat_sessions (document_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,                        -- 'user' | 'assistant'
  parts JSONB NOT NULL DEFAULT '[]',
  metadata JSONB,                            -- citations (page/section) live here for assistant msgs
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  sort_order INTEGER NOT NULL,
  CONSTRAINT chat_messages_role_check CHECK (role IN ('user', 'assistant'))
);

CREATE INDEX IF NOT EXISTS chat_messages_session_idx
  ON chat_messages (session_id, sort_order);
