import type { H3Event } from "h3";

import type { FullDocument } from "../types/retrieval";

/**
 * Shared entry for the prep-pack endpoints (summarize / terms / questions):
 * read `document_id`, fetch the full document, and reject if it has no chunks.
 */
export async function loadDocumentForPrepPack(event: H3Event): Promise<FullDocument> {
  const { document_id } = await readBody<{ document_id?: string }>(event);
  if (!document_id) {
    throw createError({ statusCode: 400, statusMessage: "document_id is required" });
  }
  const doc = await fetchFullDocument(document_id);
  if (doc.chunks.length === 0) {
    throw createError({
      statusCode: 422,
      statusMessage: "document has no chunks (not ingested yet?)",
    });
  }
  return doc;
}
