import type { H3Event } from "h3";

import type { FullDocument, PrepPackCache, PrepPackKind } from "../types/retrieval";

export interface PrepPackDeps<T> {
  getCache: (documentId: string) => Promise<PrepPackCache>;
  loadDoc: (documentId: string) => Promise<FullDocument>;
  compute: (doc: FullDocument) => Promise<T>;
  saveCache: (documentId: string, kind: PrepPackKind, value: T) => Promise<void>;
}

/**
 * Cache-or-compute one prep-pack kind (pure — deps injected, so it is unit-testable).
 * Cache hit → return the stored value, skipping the doc load AND the LLM call. Miss →
 * load the document, compute, store, and return.
 */
export async function resolvePrepPack<T>(
  documentId: string,
  kind: PrepPackKind,
  deps: PrepPackDeps<T>,
): Promise<{ document_id: string; filename: string; value: T }> {
  const cache = await deps.getCache(documentId);
  const cached = cache[kind];
  if (cached != null) {
    return { document_id: documentId, filename: cache.filename, value: cached as T };
  }
  const doc = await deps.loadDoc(documentId);
  const value = await deps.compute(doc);
  await deps.saveCache(documentId, kind, value);
  return { document_id: documentId, filename: doc.filename, value };
}

/** Endpoint wrapper: read document_id from the request, resolve via cache, shape the response. */
export async function cachedPrepPack<T>(
  event: H3Event,
  kind: PrepPackKind,
  compute: (doc: FullDocument) => Promise<T>,
): Promise<Record<string, unknown>> {
  const { document_id } = await readBody<{ document_id?: string }>(event);
  if (!document_id) {
    throw createError({ statusCode: 400, statusMessage: "document_id is required" });
  }
  const { document_id: id, filename, value } = await resolvePrepPack<T>(document_id, kind, {
    getCache: getPrepPack,
    loadDoc: async (docId) => {
      const doc = await fetchFullDocument(docId);
      if (!doc.chunks?.length) {
        throw createError({ statusCode: 422, statusMessage: "document has no text yet" });
      }
      return doc;
    },
    compute,
    saveCache: savePrepPack,
  });
  return { document_id: id, filename, [kind]: value };
}
