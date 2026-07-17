export default defineEventHandler(async (event) => {
  const doc = await loadDocumentForPrepPack(event);
  const { ai } = useRuntimeConfig();
  const { questions } = await mapReduceDocument(
    doc.chunks,
    createAnthropicQuestionGenerator(),
    ai.mapGroupChars,
    ai.mapConcurrency,
  );
  return { document_id: doc.document_id, filename: doc.filename, questions };
});
