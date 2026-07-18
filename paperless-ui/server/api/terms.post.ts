export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  // AI monitoring: gom map + reduce của lần trích thuật ngữ này vào một trace.
  return await runWithTrace(newTraceId(), () =>
    cachedPrepPack(event, "terms", async (doc) => {
      const { terms } = await mapReduceDocument(
        doc.chunks,
        createAnthropicTermsExtractor(),
        ai.mapGroupChars,
        ai.mapConcurrency,
      );
      return terms;
    }),
  );
});
