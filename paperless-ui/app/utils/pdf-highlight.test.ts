import { describe, expect, it } from "vitest";

import { matchRatio, normalizeForMatch, shouldHighlightSpan } from "./pdf-highlight";

describe("matchRatio", () => {
  it("is 1 for identical strings", () => {
    expect(matchRatio("điều 5", "điều 5")).toBe(1);
  });
  it("is high when one string is a substring of the other", () => {
    // span text is a line contained in the chunk text
    expect(matchRatio("mục tiêu tăng trưởng grdp 10,5%", "tăng trưởng grdp")).toBeGreaterThan(0.5);
  });
  it("is low for disjoint strings", () => {
    expect(matchRatio("abcdef", "uvwxyz")).toBeLessThan(0.5);
  });
  it("returns 0 when either string is empty", () => {
    expect(matchRatio("", "abc")).toBe(0);
    expect(matchRatio("abc", "")).toBe(0);
  });
});

describe("normalizeForMatch", () => {
  it("lowercases", () => {
    expect(normalizeForMatch("Điều")).toBe("điều");
  });
  it("makes composed and decomposed Vietnamese diacritics compare equal (NFC)", () => {
    const composed = "Điều 5"; // may already be NFC
    const decomposed = "Điều 5".normalize("NFD");
    expect(normalizeForMatch(composed)).toBe(normalizeForMatch(decomposed));
  });
});

describe("shouldHighlightSpan", () => {
  const chunk = "Phấn đấu tốc độ tăng trưởng tổng sản phẩm trên địa bàn (GRDP) đạt 10,5% trong năm 2026.";
  it("highlights a span whose text is a line of the cited chunk", () => {
    expect(shouldHighlightSpan(chunk, "tăng trưởng tổng sản phẩm")).toBe(true);
  });
  it("skips a span unrelated to the chunk", () => {
    expect(shouldHighlightSpan(chunk, "Kho bạc Nhà nước cấp tỉnh")).toBe(false);
  });
  it("skips very short spans (≤4 chars) to avoid noise", () => {
    expect(shouldHighlightSpan(chunk, "GRDP")).toBe(false);
  });
  it("matches across NFC/NFD and case", () => {
    expect(shouldHighlightSpan(chunk.normalize("NFD"), "TĂNG TRƯỞNG TỔNG SẢN PHẨM")).toBe(true);
  });
});
