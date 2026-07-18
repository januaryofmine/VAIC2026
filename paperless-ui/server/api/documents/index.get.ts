// "Tài liệu của tôi" — list the signed-in user's documents (owner-scoped in Postgres),
// with optional type / date-range / keyword filters from the query string.
export default defineEventHandler(async (event) => {
  const { user } = await requireUserSession(event);
  // A pre-Slice-18 session has no internal id → can't scope; force a clean re-login.
  if (!user.id) throw createError({ statusCode: 401, statusMessage: "session expired" });
  const q = getQuery(event);
  const pick = (v: unknown) => (typeof v === "string" && v ? v : undefined);
  return await listDocuments(user.id, {
    type: pick(q.type),
    date_from: pick(q.date_from),
    date_to: pick(q.date_to),
    q: pick(q.q),
  });
});
