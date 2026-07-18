import { describe, expect, it } from "vitest";

import { TEST_ACCOUNT, toSessionUser } from "./session-user";

describe("toSessionUser", () => {
  it("maps an AppUser (snake_case) to the session User (camelCase)", () => {
    expect(
      toSessionUser({
        id: "uuid-1",
        github_id: 42,
        username: "octocat",
        name: "The Octocat",
        avatar_url: "https://x/y.png",
      }),
    ).toEqual({
      id: "uuid-1",
      githubId: 42,
      username: "octocat",
      name: "The Octocat",
      avatarUrl: "https://x/y.png",
    });
  });

  it("preserves nulls for name and avatar", () => {
    const u = toSessionUser({
      id: "uuid-2",
      github_id: 0,
      username: "test-account",
      name: null,
      avatar_url: null,
    });
    expect(u.name).toBeNull();
    expect(u.avatarUrl).toBeNull();
  });
});

describe("TEST_ACCOUNT", () => {
  it("uses a stable sentinel github_id that no real GitHub account can have", () => {
    expect(TEST_ACCOUNT.github_id).toBe(0);
  });
  it("has a fixed username so every login resolves to the same shared user", () => {
    expect(TEST_ACCOUNT.username).toBe("test-account");
  });
});
