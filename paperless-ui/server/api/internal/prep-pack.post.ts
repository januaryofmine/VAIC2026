// Internal, server-to-server endpoint: generate + persist a document's prep-pack
// (summary/terms/questions). Called by retrieval-api right after ingestion embeds a
// document, so generation is backend-driven and does NOT depend on a user opening the
// doc. Authenticated by the shared api-key, not a user session.
export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig();
  assertInternalAuth(config.retrievalApiKey, getHeader(event, "x-api-key"));

  const { document_id } = await readBody<{ document_id?: string }>(event);
  if (!document_id) {
    throw createError({ statusCode: 400, statusMessage: "document_id is required" });
  }
  return await generateAllPrepPacks(document_id);
});
