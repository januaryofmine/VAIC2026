export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  return await cachedPrepPack(event, "questions", async (doc) => {
    const { questions } = await mapReduceDocument(
      doc.chunks,
      createAnthropicQuestionGenerator(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    );
    return questions;
  });
});
