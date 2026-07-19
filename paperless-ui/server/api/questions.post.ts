export default defineEventHandler(async (event) => {
  // AI monitoring: gom map + reduce của lần sinh câu hỏi này vào một trace.
  // Shared compute (prepComputers) so this matches the backend-driven ingest trigger.
  return await runWithTrace(newTraceId(), () =>
    cachedPrepPack(event, "questions", prepComputers.questions),
  );
});
