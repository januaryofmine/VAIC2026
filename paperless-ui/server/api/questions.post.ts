export default defineEventHandler(async (event) => {
  return await cachedPrepPack(event, "questions", prepComputers.questions);
});
