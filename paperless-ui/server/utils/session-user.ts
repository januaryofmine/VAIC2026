import type { User } from "#auth-utils";

import type { AppUser } from "../types/retrieval";

/**
 * The shared test account. Anyone who clicks "Login as Test Account" is upserted
 * onto this single row (keyed by the sentinel github_id), so they all share one
 * owner id and therefore see the same documents. No real GitHub account has id 0.
 */
export const TEST_ACCOUNT = {
  github_id: 0,
  username: "test-account",
  name: "Tài khoản Test",
  avatar_url: null,
} satisfies {
  github_id: number;
  username: string;
  name: string | null;
  avatar_url: string | null;
};

/** Map the internal AppUser (snake_case, from retrieval-api) to the session User. */
export function toSessionUser(u: AppUser): User {
  return {
    id: u.id,
    githubId: u.github_id,
    username: u.username,
    name: u.name,
    avatarUrl: u.avatar_url,
  };
}
