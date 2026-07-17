export default defineEventHandler(async (event) => {
  const doc = await loadDocumentForPrepPack(event);
  const { ai } = useRuntimeConfig();
  const { terms } = await mapReduceDocument(
    doc.chunks,
    createAnthropicTermsExtractor(),
    ai.mapGroupChars,
    ai.mapConcurrency,
  );
  return { document_id: doc.document_id, filename: doc.filename, terms };
});
