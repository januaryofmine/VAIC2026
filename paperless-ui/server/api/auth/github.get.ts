// GitHub OAuth callback. nuxt-auth-utils handles the redirect dance; we just map the
// GitHub profile into our session. Session-only (no users table yet) — see Slice 16.
export default defineOAuthGitHubEventHandler({
  async onSuccess(event, { user }) {
    await setUserSession(event, {
      user: {
        githubId: user.id,
        username: user.login,
        name: user.name || null,
        avatarUrl: user.avatar_url,
      },
    });
    return sendRedirect(event, "/");
  },
  onError(event, error) {
    console.error("GitHub OAuth error:", error);
    return sendRedirect(event, "/login?error=github_oauth_error");
  },
});
