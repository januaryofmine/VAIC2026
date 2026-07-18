import { apiKeyHeaders } from "../../../utils/retrieval-http";
import { setServerTiming } from "../../../utils/server-timing";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  if (!id) throw createError({ statusCode: 400, statusMessage: "document id is required" });
  // Authorize: only the owner may poll a document's ingestion status.
  const t0 = performance.now();
  await requireDocumentAccess(event, id);
  const t1 = performance.now();
  const config = useRuntimeConfig();
  // Proxy to retrieval-api; its 404/errors propagate to the client.
  const res = await $fetch(`${config.retrievalApiHost}/api/documents/${id}/status`, {
    headers: apiKeyHeaders(config.retrievalApiKey),
  });
  // Server-Timing: owner-check vs retrieval-api fetch split, visible in DevTools (Bậc 2).
  setServerTiming(event, [
    { name: "owner", dur: t1 - t0, desc: "ownership check" },
    { name: "status", dur: performance.now() - t1, desc: "retrieval-api" },
  ]);
  return res;
});
