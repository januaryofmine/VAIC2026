import { apiKeyHeaders } from "../../../utils/retrieval-http";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  if (!id) throw createError({ statusCode: 400, statusMessage: "document id is required" });
  // Authorize: only the owner may poll a document's ingestion status.
  await requireDocumentAccess(event, id);
  const config = useRuntimeConfig();
  // Proxy to retrieval-api; its 404/errors propagate to the client.
  return await $fetch(`${config.retrievalApiHost}/api/documents/${id}/status`, {
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
});
