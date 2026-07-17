import { describe, expect, it } from "vitest";

import type { RetrieveChunk, RetrieveResponse } from "../types/retrieval";
import { buildPlanPrompt, fallbackStrategy, mergeAndDedupe } from "./ask-strategy";

const chunk = (over: Partial<RetrieveChunk>): RetrieveChunk => ({
  id: "1",
  position: 0,
  page: null,
  section: null,
  text: "nội dung",
  score: 0.9,
  ...over,
});

const resp = (chunks: RetrieveChunk[]): RetrieveResponse => ({
  chunks,
  reformulated_query: "",
});

describe("fallbackStrategy", () => {
  it("degenerates to a single subquery = the question", () => {
    const s = fallbackStrategy("Quan điểm gồm những gì?");
    expect(s.subqueries).toHaveLength(1);
    expect(s.subqueries[0].query).toBe("Quan điểm gồm những gì?");
  });
});

describe("buildPlanPrompt", () => {
  it("includes the question and the ≤5 self-contained-query instruction", () => {
    const p = buildPlanPrompt("Mục tiêu và giải pháp là gì?", []);
    expect(p).toContain("Mục tiêu và giải pháp là gì?");
    expect(p).toContain("5"); // bounded fan-out mentioned
  });

  it("includes prior turns when history is present", () => {
    const p = buildPlanPrompt("Còn điều 2?", [
      { role: "user", content: "Điều 1 nói gì?" },
      { role: "assistant", content: "Điều 1 quy định..." },
    ]);
    expect(p).toContain("Điều 1 nói gì?");
  });
});

describe("mergeAndDedupe (RRF across subqueries)", () => {
  it("dedupes by position, keeping one entry per chunk", () => {
    const merged = mergeAndDedupe(
      [resp([chunk({ position: 5 })]), resp([chunk({ position: 5 })])],
      10,
    );
    expect(merged).toHaveLength(1);
    expect(merged[0].position).toBe(5);
  });

  it("ranks a consensus chunk (found by 2 subqueries) above a single-hit chunk", () => {
    // pos 2 appears top of both lists; pos 9 appears once → consensus wins.
    const merged = mergeAndDedupe(
      [
        resp([chunk({ position: 2 }), chunk({ position: 9 })]),
        resp([chunk({ position: 2 })]),
      ],
      10,
    );
    expect(merged[0].position).toBe(2);
  });

  it("caps the merged set to the requested size", () => {
    const many = Array.from({ length: 8 }, (_, i) => chunk({ position: i }));
    expect(mergeAndDedupe([resp(many)], 3)).toHaveLength(3);
  });

  it("returns [] for no results", () => {
    expect(mergeAndDedupe([resp([]), resp([])], 10)).toEqual([]);
  });
});
