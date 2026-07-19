export default defineEventHandler(async (event) => {
  // AI monitoring: gom mọi lời gọi map + reduce của LẦN tóm tắt này vào một trace,
  // nhờ đó đo được thời gian/chi phí của cả bước (yêu cầu < 60s) chứ không phải
  // từng lời gọi rời rạc.
  // Cache-or-compute: returns the stored summary on a re-open, else map-reduces once.
  // Shared compute (prepComputers) so this matches the backend-driven ingest trigger.
  return await runWithTrace(newTraceId(), () =>
    cachedPrepPack(event, "summary", prepComputers.summary),
  );
});
