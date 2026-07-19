import { describe, expect, it } from "vitest";

import { assertDocumentAccess, type DocumentAccessDeps } from "./document-access";

const DOC = "11111111-1111-1111-1111-111111111111";
const ME = "22222222-2222-2222-2222-222222222222";
const OTHER = "33333333-3333-3333-3333-333333333333";

function deps(over: Partial<DocumentAccessDeps> = {}): DocumentAccessDeps {
  return {
    getSessionUserId: async () => ME,
    getOwner: async () => ({ user_id: ME }),
    ...over,
  };
}

const status = (e: unknown) => (e as { statusCode?: number })?.statusCode;

describe("assertDocumentAccess", () => {
  it("returns the session user id when the caller owns the document", async () => {
    const out = await assertDocumentAccess(DOC, deps());
    expect(out).toEqual({ userId: ME });
  });

  it("401s when there is no session", async () => {
    const e = await assertDocumentAccess(DOC, deps({ getSessionUserId: async () => undefined }))
      .catch((err) => err);
    expect(status(e)).toBe(401);
  });

  it("404s when the document has no owner (null)", async () => {
    const e = await assertDocumentAccess(DOC, deps({ getOwner: async () => ({ user_id: null }) }))
      .catch((err) => err);
    expect(status(e)).toBe(404);
  });

  it("404s when the caller is not the owner", async () => {
    const e = await assertDocumentAccess(DOC, deps({ getOwner: async () => ({ user_id: OTHER }) }))
      .catch((err) => err);
    expect(status(e)).toBe(404);
  });

  it("404s (not-found) when the owner lookup 404s", async () => {
    const e = await assertDocumentAccess(
      DOC,
      deps({ getOwner: async () => { throw { statusCode: 404 }; } }),
    ).catch((err) => err);
    expect(status(e)).toBe(404);
  });

  it("404s when the owner lookup 422s (malformed id)", async () => {
    const e = await assertDocumentAccess(
      DOC,
      deps({ getOwner: async () => { throw { statusCode: 422 }; } }),
    ).catch((err) => err);
    expect(status(e)).toBe(404);
  });

  it("rethrows a genuine upstream error (500) instead of masking it as 404", async () => {
    const e = await assertDocumentAccess(
      DOC,
      deps({ getOwner: async () => { throw { statusCode: 500 }; } }),
    ).catch((err) => err);
    expect(status(e)).toBe(500);
  });
});
