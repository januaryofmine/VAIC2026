// Shape of the logged-in user carried in the sealed session cookie (nuxt-auth-utils).
// Session-only for now (Slice 16 auth part): no users table yet — that comes with
// per-user data scoping. githubId is the stable identity until then.
declare module "#auth-utils" {
  interface User {
    githubId: number;
    username: string;
    name: string | null;
    avatarUrl: string | null;
  }
}

export {};
