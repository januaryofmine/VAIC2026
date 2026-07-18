/**
 * Helpers for calling the retrieval-api over HTTP (cloud deploy). Pure + testable;
 * the Nitro glue (`$fetch`, `useRuntimeConfig`) lives in the route handlers.
 */

/** Auth header for retrieval-api. Empty key (local dev) → no header, endpoint open. */
export function apiKeyHeaders(apiKey: string | undefined): Record<string, string> {
  return apiKey ? { "X-API-Key": apiKey } : {};
}

/** Multipart body for `POST /api/ingest`: the file under its original name, plus
 * the owning user id (Slice 18 scoping) when signed in. */
export function buildIngestForm(
  data: Uint8Array,
  filename: string,
  userId?: string | null,
): FormData {
  const fd = new FormData();
  fd.append("file", new Blob([data]), filename);
  if (userId) fd.append("user_id", userId);
  return fd;
}
