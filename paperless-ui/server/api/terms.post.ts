export default defineEventHandler(async (event) => {
  return await cachedPrepPack(event, "terms", prepComputers.terms);
});
