export default defineEventHandler(async (event) => {
  // Cache-or-compute: returns the stored summary on a re-open, else map-reduces once.
  // Shared compute (prepComputers) so this matches the backend-driven ingest trigger.
  return await cachedPrepPack(event, "summary", prepComputers.summary);
});
