import type {
  AppUser,
  DocumentListResponse,
  FullDocument,
  RetrieveResponse,
} from "../types/retrieval";
import type { HistoryEntry } from "./chat-context";

/** Upsert the GitHub user in Postgres (retrieval-api) and get our internal id (Slice 18). */
export async function upsertUser(profile: {
  github_id: number;
  username: string;
  name: string | null;
  avatar_url: string | null;
}): Promise<AppUser> {
  const config = useRuntimeConfig();
  return await $fetch<AppUser>(`${config.retrievalApiHost}/api/users/upsert`, {
    method: "POST",
    body: profile,
  });
}

/** List a user's documents (owner-scoped) with optional type/date/keyword filters. */
export async function listDocuments(
  userId: string,
  filters: { type?: string; date_from?: string; date_to?: string; q?: string } = {},
): Promise<DocumentListResponse> {
  const config = useRuntimeConfig();
  return await $fetch<DocumentListResponse>(`${config.retrievalApiHost}/api/documents`, {
    query: { user_id: userId, ...filters },
  });
}

/** Fetch a document's full chunk list (ordered) from retrieval-api documents.py. */
export async function fetchFullDocument(documentId: string): Promise<FullDocument> {
  const config = useRuntimeConfig();
  return await $fetch<FullDocument>(
    `${config.retrievalApiHost}/api/documents/${documentId}/full`,
  );
}

/** Vector-search a document for a question (retrieval-api retrieve.py) — Q&A path. */
export async function retrieveChunks(
  question: string,
  documentId: string,
  history: HistoryEntry[],
  topK?: number,
): Promise<RetrieveResponse> {
  const config = useRuntimeConfig();
  return await $fetch<RetrieveResponse>(`${config.retrievalApiHost}/api/retrieve`, {
    method: "POST",
    body: { question, document_id: documentId, history, top_k: topK },
  });
}
