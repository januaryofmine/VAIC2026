// Shape of the logged-in user carried in the sealed session cookie (nuxt-auth-utils).
// `id` is our internal users.id (UUID) — the owner key for documents (Slice 18).
declare module "#auth-utils" {
  interface User {
    id: string;
    githubId: number;
    username: string;
    name: string | null;
    avatarUrl: string | null;
  }
}

export {};
