export interface DocumentChunk {
  id: string;
  position: number;
  page: number | null;
  section: string | null;
  text: string;
}

export interface FullDocument {
  document_id: string;
  filename: string;
  doc_type: string;
  page_count: number | null;
  status: string;
  chunk_count: number;
  chunks: DocumentChunk[];
}

export interface RetrieveChunk extends DocumentChunk {
  score: number;
}

export interface RetrieveResponse {
  chunks: RetrieveChunk[];
  reformulated_query: string;
}

export interface AppUser {
  id: string;
  github_id: number;
  username: string;
  name: string | null;
  avatar_url: string | null;
}

export interface DocumentListItem {
  document_id: string;
  filename: string;
  doc_type: string;
  status: string;
  page_count: number | null;
  chunk_count: number;
  size_bytes: number | null;
  uploaded_at: string;
}

export interface DocumentListResponse {
  documents: DocumentListItem[];
}

export type PrepPackKind = "summary" | "terms" | "questions";

export interface PrepPackCache {
  document_id: string;
  filename: string;
  summary: unknown | null;
  terms: unknown | null;
  questions: unknown | null;
}

/** A persisted chat message (AI-SDK UIMessage shape) for chat-history (Slice 14b). */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  parts: unknown;
  metadata?: unknown;
}
