import { describe, expect, it, vi } from "vitest";

import type { FullDocument, PrepPackCache } from "../types/retrieval";
import { resolvePrepPack } from "./prep-pack-cache";

const cache = (over: Partial<PrepPackCache>): PrepPackCache => ({
  document_id: "d1",
  filename: "x.pdf",
  summary: null,
  terms: null,
  questions: null,
  ...over,
});

const doc = { document_id: "d1", filename: "x.pdf", chunks: [{}] } as unknown as FullDocument;

describe("resolvePrepPack", () => {
  it("cache hit → returns stored value, skips loadDoc + compute", async () => {
    const compute = vi.fn();
    const loadDoc = vi.fn();
    const saveCache = vi.fn();
    const out = await resolvePrepPack("d1", "summary", {
      getCache: async () => cache({ summary: { context: "cached" } }),
      loadDoc,
      compute,
      saveCache,
    });
    expect(out).toEqual({ document_id: "d1", filename: "x.pdf", value: { context: "cached" } });
    expect(compute).not.toHaveBeenCalled();
    expect(loadDoc).not.toHaveBeenCalled();
    expect(saveCache).not.toHaveBeenCalled();
  });

  it("cache miss → loads doc, computes, saves, returns computed value", async () => {
    const compute = vi.fn().mockResolvedValue(["q1", "q2"]);
    const saveCache = vi.fn().mockResolvedValue(undefined);
    const out = await resolvePrepPack("d1", "questions", {
      getCache: async () => cache({ questions: null }),
      loadDoc: async () => doc,
      compute,
      saveCache,
    });
    expect(out.value).toEqual(["q1", "q2"]);
    expect(compute).toHaveBeenCalledOnce();
    expect(saveCache).toHaveBeenCalledWith("d1", "questions", ["q1", "q2"]);
  });

  it("treats an empty-array cached value as present (does not recompute)", async () => {
    const compute = vi.fn();
    await resolvePrepPack("d1", "terms", {
      getCache: async () => cache({ terms: [] }),
      loadDoc: vi.fn(),
      compute,
      saveCache: vi.fn(),
    });
    expect(compute).not.toHaveBeenCalled();
  });
});
