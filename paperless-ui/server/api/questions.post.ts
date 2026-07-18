export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  // AI monitoring: gom map + reduce của lần sinh câu hỏi này vào một trace.
  return await runWithTrace(newTraceId(), () =>
    cachedPrepPack(event, "questions", async (doc) => {
      const { questions } = await mapReduceDocument(
        doc.chunks,
        createAnthropicQuestionGenerator(),
        ai.mapGroupChars,
        ai.mapConcurrency,
      );
      return questions;
    }),
  );
});
