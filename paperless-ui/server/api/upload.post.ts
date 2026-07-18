import { basename } from "node:path";
import { apiKeyHeaders, buildIngestForm } from "../utils/retrieval-http";

/**
 * Upload → forward to retrieval-api `POST /api/ingest` over HTTP.
 *
 * The UI runs serverless (Vercel Node) with no Python, so ingestion happens in the
 * retrieval-api container (which co-locates rag-pipeline). retrieval-api returns as
 * soon as the document row exists (status "processing"); the client then polls
 * `/api/documents/{id}/status`.
 */
export default defineEventHandler(async (event) => {
  // Uploads are owned by the logged-in user (Slice 18); 401 if not signed in.
  const { user } = await requireUserSession(event);
  if (!user.id) throw createError({ statusCode: 401, statusMessage: "session expired" });

  const form = await readMultipartFormData(event);
  const filePart = form?.find((p) => p.name === "file" && p.filename);
  if (!filePart || !filePart.filename) {
    throw createError({ statusCode: 400, statusMessage: "file field is required" });
  }

  const docType = detectDocType(filePart.filename);
  if (!docType) {
    throw createError({
      statusCode: 400,
      statusMessage: "unsupported file type (only .pdf or .docx)",
    });
  }

  const config = useRuntimeConfig();
  const maxBytes = config.ingest.maxFileMb * 1024 * 1024;
  if (filePart.data.length > maxBytes) {
    throw createError({
      statusCode: 413,
      statusMessage: `file too large (max ${config.ingest.maxFileMb}MB)`,
    });
  }

  const safeName = basename(filePart.filename);
  const body = buildIngestForm(filePart.data, safeName, user.id);

  try {
    // retrieval-api returns early: { document_id, filename, status: "processing" }.
    const res = await $fetch<{ document_id: string; status: string }>(
      `${config.retrievalApiHost}/api/ingest`,
      { method: "POST", body, headers: apiKeyHeaders(config.retrievalApiKey) },
    );
    return {
      document_id: res.document_id,
      filename: safeName,
      doc_type: docType,
      status: res.status,
    };
  } catch (e) {
    // Don't leak the upstream error to the client (S1 hardening).
    throw createError({ statusCode: 502, statusMessage: "ingestion service unavailable" });
  }
});
