import { describe, expect, it } from "vitest";

import { citationLabel, dedupeSources } from "./citations";

describe("citationLabel", () => {
  it("combines page and section (PDF)", () => {
    expect(citationLabel({ page: 3, section: "Điều 1" })).toBe("trang 3, Điều 1");
  });
  it("uses section only when page is null (DOCX)", () => {
    expect(citationLabel({ page: null, section: "Điều 5" })).toBe("Điều 5");
  });
  it("falls back to 'nguồn' when nothing is available", () => {
    expect(citationLabel({ page: null, section: null })).toBe("nguồn");
  });
});

describe("dedupeSources", () => {
  it("collapses sources sharing the same label", () => {
    const out = dedupeSources([
      { page: 1, section: "Điều 1" },
      { page: 1, section: "Điều 1" },
      { page: 2, section: "Điều 1" },
    ]);
    expect(out).toHaveLength(2);
  });
});
