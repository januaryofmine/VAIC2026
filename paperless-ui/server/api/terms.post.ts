export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  return await cachedPrepPack(event, "terms", async (doc) => {
    const { terms } = await mapReduceDocument(
      doc.chunks,
      createAnthropicTermsExtractor(),
      ai.mapGroupChars,
      ai.mapConcurrency,
    );
    return terms;
  });
});
