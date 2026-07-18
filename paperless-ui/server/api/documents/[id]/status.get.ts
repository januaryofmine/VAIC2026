export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const config = useRuntimeConfig();
  // Proxy to retrieval-api; its 404/errors propagate to the client.
  return await $fetch(`${config.retrievalApiHost}/api/documents/${id}/status`);
});
