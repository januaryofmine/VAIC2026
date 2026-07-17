import { describe, expect, it } from "vitest";

import type { DocumentChunk } from "../types/retrieval";
import { groupChunks } from "./group-chunks";

const mk = (i: number, len: number): DocumentChunk => ({
  id: String(i),
  position: i,
  page: null,
  section: null,
  text: "x".repeat(len),
});

describe("groupChunks", () => {
  it("packs consecutive chunks up to maxChars", () => {
    const groups = groupChunks([mk(0, 400), mk(1, 400), mk(2, 400)], 1000);
    expect(groups.length).toBe(2);
    expect(groups[0].length).toBe(2); // 400 + 400 <= 1000
    expect(groups[1].length).toBe(1);
  });

  it("keeps an oversized single chunk in its own group", () => {
    const groups = groupChunks([mk(0, 5000)], 1000);
    expect(groups).toHaveLength(1);
    expect(groups[0]).toHaveLength(1);
  });

  it("returns no groups for an empty input", () => {
    expect(groupChunks([], 1000)).toEqual([]);
  });

  it("covers every chunk exactly once", () => {
    const chunks = [mk(0, 300), mk(1, 300), mk(2, 300), mk(3, 300)];
    expect(groupChunks(chunks, 700).flat()).toHaveLength(4);
  });
});
