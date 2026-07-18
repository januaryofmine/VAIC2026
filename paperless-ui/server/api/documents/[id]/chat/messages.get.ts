// Load a document's saved chat history (Slice 14b) for the client to hydrate the chat.
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  if (!id) throw createError({ statusCode: 400, statusMessage: "document id is required" });
  // Authorize: only the owner may read a document's saved chat history.
  await requireDocumentAccess(event, id);
  return await getChatMessages(id);
});
