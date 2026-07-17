import { describe, expect, it } from "vitest";

import { isSupportedDoc } from "./file";

describe("isSupportedDoc", () => {
  it("accepts pdf and docx (case-insensitive)", () => {
    expect(isSupportedDoc("a.pdf")).toBe(true);
    expect(isSupportedDoc("LAW.DOCX")).toBe(true);
  });
  it("rejects other types", () => {
    expect(isSupportedDoc("a.txt")).toBe(false);
    expect(isSupportedDoc("noext")).toBe(false);
  });
});
