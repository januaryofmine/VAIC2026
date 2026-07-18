import { createError, type H3Event } from "h3";

/**
 * Authorization for a document-scoped request. `getSessionUserId` yields the signed-in
 * user's internal id (undefined when unauthenticated); `getOwner` resolves the document's
 * owner. Injected so the decision logic is unit-testable without the Nuxt runtime.
 */
export interface DocumentAccessDeps {
  getSessionUserId: () => Promise<string | undefined>;
  getOwner: (documentId: string) => Promise<{ user_id: string | null }>;
}

/**
 * Decide whether the caller may act on `documentId`. Returns the session user id on
 * success; otherwise throws 401 (no session) or 404. A missing/malformed document and a
 * document the caller does not own both surface as 404 (never 403) so a non-owner cannot
 * probe which document ids exist.
 */
export async function assertDocumentAccess(
  documentId: string,
  deps: DocumentAccessDeps,
): Promise<{ userId: string }> {
  const userId = await deps.getSessionUserId();
  if (!userId) {
    throw createError({ statusCode: 401, statusMessage: "session expired" });
  }

  let owner: { user_id: string | null };
  try {
    owner = await deps.getOwner(documentId);
  } catch (e) {
    // "not found" / "bad id" from the owner lookup → 404. Anything else (e.g. the
    // retrieval-api being down) is a genuine error and must not be masked as 404.
    const code = (e as { statusCode?: number; status?: number })?.statusCode
      ?? (e as { status?: number })?.status;
    if (code === 404 || code === 422) {
      throw createError({ statusCode: 404, statusMessage: "document not found" });
    }
    throw e;
  }

  if (owner.user_id === null || owner.user_id !== userId) {
    throw createError({ statusCode: 404, statusMessage: "document not found" });
  }
  return { userId };
}

/**
 * Server-route guard: require a valid session AND that the session user owns
 * `documentId`. Wire this into every document-scoped server route — the client-side
 * route middleware (`app/middleware/auth.global.ts`) only gates page navigation and
 * does NOT protect Nitro handlers.
 */
export async function requireDocumentAccess(
  event: H3Event,
  documentId: string,
): Promise<{ userId: string }> {
  return await assertDocumentAccess(documentId, {
    getSessionUserId: async () => (await requireUserSession(event)).user?.id,
    getOwner: fetchDocumentOwner,
  });
}
