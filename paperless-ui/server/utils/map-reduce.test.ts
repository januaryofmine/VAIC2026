import { describe, expect, it } from "vitest";

import type { DocumentChunk } from "../types/retrieval";
import { mapPool, mapReduceDocument } from "./map-reduce";

const mk = (i: number, len: number): DocumentChunk => ({
  id: String(i),
  position: i,
  page: null,
  section: null,
  text: "x".repeat(len),
});

describe("mapPool", () => {
  it("preserves input order in results", async () => {
    const out = await mapPool([3, 1, 2], 2, async (n) => {
      await new Promise((r) => setTimeout(r, n * 5));
      return n * 10;
    });
    expect(out).toEqual([30, 10, 20]);
  });
});

describe("mapReduceDocument", () => {
  it("maps each group then reduces, generic over result type", async () => {
    const chunks = [mk(0, 400), mk(1, 400), mk(2, 400)]; // 2 groups at 1000
    const result = await mapReduceDocument(
      chunks,
      {
        mapText: async (t) => `m${t.length}`,
        reduce: async (partials) => ({ count: partials.length }),
      },
      1000,
    );
    expect(result).toEqual({ count: 2 });
  });

  it("throws on an empty document", async () => {
    await expect(
      mapReduceDocument([], { mapText: async () => "", reduce: async () => 0 }, 1000),
    ).rejects.toThrow();
  });
});
