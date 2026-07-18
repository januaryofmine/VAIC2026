export default defineEventHandler(async (event) => {
  const { ai } = useRuntimeConfig();
  // AI monitoring: gom mọi lời gọi map + reduce của LẦN tóm tắt này vào một trace,
  // nhờ đó đo được thời gian/chi phí của cả bước (yêu cầu < 60s) chứ không phải
  // từng lời gọi rời rạc.
  return await runWithTrace(newTraceId(), () =>
    // Cache-or-compute: returns the stored summary on a re-open, else map-reduces once.
    cachedPrepPack(event, "summary", (doc) =>
      summarizeDocument(
        doc.chunks,
        createAnthropicSummarizer(),
        ai.mapGroupChars,
        ai.mapConcurrency,
      ),
    ),
  );
});
