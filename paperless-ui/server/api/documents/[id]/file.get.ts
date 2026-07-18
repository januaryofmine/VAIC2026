import { apiKeyHeaders } from "../../../utils/retrieval-http";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  if (!id) throw createError({ statusCode: 400, statusMessage: "document id is required" });
  // Authorize before streaming the original file: signed in AND owns this document.
  await requireDocumentAccess(event, id);
  const config = useRuntimeConfig();
  // Stream the original blob straight through (keeps content-type/disposition,
  // propagates 404). Used by the doc viewer (Slice 15).
  return await proxyRequest(event, `${config.retrievalApiHost}/api/documents/${id}/file`, {
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
});
