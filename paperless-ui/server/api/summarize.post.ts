export default defineEventHandler(async (event) => {
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

  const { ai } = useRuntimeConfig();
  const summary = await summarizeDocument(
    doc.chunks,
    createAnthropicSummarizer(),
    ai.mapGroupChars,
    ai.mapConcurrency,
  );

  return { document_id, filename: doc.filename, summary };
});
