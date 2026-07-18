import type {
  AppUser,
  ChatMessage,
  DocumentListResponse,
  FullDocument,
  PrepPackKind,
  PrepPackCache,
  RetrieveResponse,
} from "../types/retrieval";
import type { HistoryEntry } from "./chat-context";
import { apiKeyHeaders } from "./retrieval-http";

/** Read the cached prep-pack (summary/terms/questions) for a document (Slice 14a). */
export async function getPrepPack(documentId: string): Promise<PrepPackCache> {
  const config = useRuntimeConfig();
  return await $fetch<PrepPackCache>(
    `${config.retrievalApiHost}/api/documents/${documentId}/prep-pack`,
    { headers: apiKeyHeaders(config.retrievalApiKey) },
  );
}

/** Store one computed prep-pack kind so future opens read it instead of re-calling Claude. */
export async function savePrepPack(
  documentId: string,
  kind: PrepPackKind,
  value: unknown,
): Promise<void> {
  const config = useRuntimeConfig();
  await $fetch(`${config.retrievalApiHost}/api/documents/${documentId}/prep-pack`, {
    method: "PUT",
    body: { kind, value },
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
}

/** Load a document's saved chat messages, in order (Slice 14b). */
export async function getChatMessages(documentId: string): Promise<{ messages: ChatMessage[] }> {
  const config = useRuntimeConfig();
  return await $fetch<{ messages: ChatMessage[] }>(
    `${config.retrievalApiHost}/api/documents/${documentId}/chat/messages`,
    { headers: apiKeyHeaders(config.retrievalApiKey) },
  );
}

/** Append one chat message (dedup by id) so the conversation survives a refresh. */
export async function appendChatMessage(
  documentId: string,
  message: ChatMessage,
): Promise<void> {
  const config = useRuntimeConfig();
  await $fetch(`${config.retrievalApiHost}/api/documents/${documentId}/chat/messages`, {
    method: "POST",
    body: message,
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
}

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
    headers: apiKeyHeaders(config.retrievalApiKey),
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
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
}

/** Fetch a document's full chunk list (ordered) from retrieval-api documents.py. */
export async function fetchFullDocument(documentId: string): Promise<FullDocument> {
  const config = useRuntimeConfig();
  return await $fetch<FullDocument>(
    `${config.retrievalApiHost}/api/documents/${documentId}/full`,
    { headers: apiKeyHeaders(config.retrievalApiKey) },
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
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
}
