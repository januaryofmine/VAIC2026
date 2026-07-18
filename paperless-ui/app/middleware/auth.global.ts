// Gate the whole app behind GitHub login (Slice 18) — documents are per-user.
// The login page itself is the only public route.
export default defineNuxtRouteMiddleware(async (to) => {
  const { loggedIn, user, clear } = useUserSession();
  if (to.path === "/login") return;
  if (!loggedIn.value) return navigateTo("/login");
  // A session created before Slice 18 has no internal `id` (the owner key). Invalidate
  // it so the user re-logs in and gets a session that can scope their documents.
  if (!user.value?.id) {
    await clear();
    return navigateTo("/login");
  }
});
