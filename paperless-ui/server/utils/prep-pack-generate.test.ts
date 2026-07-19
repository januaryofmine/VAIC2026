import { describe, expect, it } from "vitest";

import { assertInternalAuth, generateAllPrepPacks } from "./prep-pack-generate";

const status = (e: unknown) => (e as { statusCode?: number })?.statusCode;

describe("assertInternalAuth", () => {
  it("allows any request when no key is configured (local dev)", () => {
    expect(() => assertInternalAuth("", undefined)).not.toThrow();
    expect(() => assertInternalAuth("", "anything")).not.toThrow();
  });

  it("allows a matching key", () => {
    expect(() => assertInternalAuth("secret", "secret")).not.toThrow();
  });

  it("rejects a missing key when one is configured", () => {
    let e: unknown;
    try { assertInternalAuth("secret", undefined); } catch (err) { e = err; }
    expect(status(e)).toBe(401);
  });

  it("rejects a wrong key when one is configured", () => {
    let e: unknown;
    try { assertInternalAuth("secret", "nope"); } catch (err) { e = err; }
    expect(status(e)).toBe(401);
  });
});

describe("generateAllPrepPacks", () => {
  it("generates all three kinds and reports each fulfilled", async () => {
    const calls: string[] = [];
    const gen = async (_id: string, kind: string) => {
      calls.push(kind);
      return kind;
    };
    const r = await generateAllPrepPacks("doc1", gen);
    expect(calls.sort()).toEqual(["questions", "summary", "terms"]);
    expect(r).toEqual({
      document_id: "doc1",
      generated: { summary: "fulfilled", terms: "fulfilled", questions: "fulfilled" },
    });
  });

  it("one kind failing does not drop the others (allSettled)", async () => {
    const gen = async (_id: string, kind: string) => {
      if (kind === "terms") throw new Error("boom");
      return kind;
    };
    const r = await generateAllPrepPacks("doc1", gen);
    expect(r.generated).toEqual({
      summary: "fulfilled",
      terms: "rejected",
      questions: "fulfilled",
    });
  });
});
