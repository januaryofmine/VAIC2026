import type { FullDocument } from "../types/retrieval";

/** Fetch a document's full chunk list (ordered) from retrieval-api documents.py. */
export async function fetchFullDocument(documentId: string): Promise<FullDocument> {
  const config = useRuntimeConfig();
  return await $fetch<FullDocument>(
    `${config.retrievalApiHost}/api/documents/${documentId}/full`,
  );
}
