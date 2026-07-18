// Log in as the shared test account — no OAuth. Upserts the fixed TEST_ACCOUNT row
// (stable owner id) and starts a session, so anyone using it sees the same documents.
export default defineEventHandler(async (event) => {
  const appUser = await upsertUser(TEST_ACCOUNT);
  await setUserSession(event, { user: toSessionUser(appUser) });
  return sendRedirect(event, "/");
});
