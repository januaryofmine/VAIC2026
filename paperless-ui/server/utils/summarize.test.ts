import { describe, expect, it } from "vitest";

import type { DocumentChunk } from "../types/retrieval";
import { summarizeDocument, type StructuredSummary, type Summarizer } from "./summarize";

const mk = (i: number, len: number): DocumentChunk => ({
  id: String(i),
  position: i,
  page: null,
  section: null,
  text: "x".repeat(len),
});

const fakeSummary: StructuredSummary = {
  context: "c",
  main_content: "m",
  decision_points: ["d"],
  impact: "i",
};

function makeFake() {
  const mapCalls: string[] = [];
  const reduceArgs: string[][] = [];
  const summarizer: Summarizer = {
    async mapSummary(text) {
      mapCalls.push(text);
      return `S(${text.length})`;
    },
    async reduceSummary(partials) {
      reduceArgs.push(partials);
      return fakeSummary;
    },
  };
  return { summarizer, mapCalls, reduceArgs };
}

describe("summarizeDocument", () => {
  it("maps each group, then reduces the partial summaries", async () => {
    const f = makeFake();
    const chunks = [mk(0, 400), mk(1, 400), mk(2, 400)]; // -> 2 groups at maxChars 1000
    const out = await summarizeDocument(chunks, f.summarizer, 1000);

    expect(f.mapCalls).toHaveLength(2); // one map call per group
    expect(f.reduceArgs[0]).toHaveLength(2); // reduce receives both partials
    expect(out).toEqual(fakeSummary);
  });

  it("throws on an empty document", async () => {
    await expect(
      summarizeDocument([], makeFake().summarizer, 1000),
    ).rejects.toThrow();
  });

  it("never runs more than maxConcurrency map calls at once", async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    const summarizer: Summarizer = {
      async mapSummary() {
        inFlight++;
        maxInFlight = Math.max(maxInFlight, inFlight);
        await new Promise((r) => setTimeout(r, 10));
        inFlight--;
        return "s";
      },
      async reduceSummary() {
        return fakeSummary;
      },
    };
    // maxChars 10 with 12 chunks of 100 chars → 12 single-chunk groups
    const chunks = Array.from({ length: 12 }, (_, i) => mk(i, 100));
    await summarizeDocument(chunks, summarizer, 10, 3);
    expect(maxInFlight).toBeLessThanOrEqual(3);
    expect(maxInFlight).toBe(3); // and it actually uses the full budget
  });

  it("passes partials to reduce in document order despite jittered completion", async () => {
    let reduced: string[] = [];
    const summarizer: Summarizer = {
      async mapSummary(text) {
        await new Promise((r) => setTimeout(r, Math.random() * 15));
        return text[0]; // first char identifies which group this was
      },
      async reduceSummary(partials) {
        reduced = partials;
        return fakeSummary;
      },
    };
    const chunks = [
      { ...mk(0, 4), text: "AAAA" },
      { ...mk(1, 4), text: "BBBB" },
      { ...mk(2, 4), text: "CCCC" },
    ];
    await summarizeDocument(chunks, summarizer, 4, 3); // 3 single-chunk groups
    expect(reduced).toEqual(["A", "B", "C"]);
  });
});
