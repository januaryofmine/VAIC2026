import type { FullDocument, RetrieveResponse } from "../types/retrieval";
import type { HistoryEntry } from "./chat-context";

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
): Promise<RetrieveResponse> {
  const config = useRuntimeConfig();
  return await $fetch<RetrieveResponse>(`${config.retrievalApiHost}/api/retrieve`, {
    method: "POST",
    body: { question, document_id: documentId, history },
  });
}
