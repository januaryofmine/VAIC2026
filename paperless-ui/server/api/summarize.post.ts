export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  // Cache-or-compute: returns the stored summary on a re-open, else map-reduces once.
  return await cachedPrepPack(event, "summary", (doc) =>
    summarizeDocument(
      doc.chunks,
      createAnthropicSummarizer(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    ),
  );
});
