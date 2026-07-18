// GitHub OAuth callback. nuxt-auth-utils handles the redirect dance; we upsert the
// GitHub profile into Postgres (via retrieval-api) and store our internal user id in
// the session — that id is the owner key for documents (Slice 18).
export default defineOAuthGitHubEventHandler({
  async onSuccess(event, { user }) {
    const appUser = await upsertUser({
      github_id: user.id,
      username: user.login,
      name: user.name || null,
      avatar_url: user.avatar_url,
    });
    await setUserSession(event, {
      user: {
        id: appUser.id,
        githubId: appUser.github_id,
        username: appUser.username,
        name: appUser.name,
        avatarUrl: appUser.avatar_url,
      },
    });
    return sendRedirect(event, "/");
  },
  onError(event, error) {
    console.error("GitHub OAuth error:", error);
    return sendRedirect(event, "/login?error=github_oauth_error");
  },
});
