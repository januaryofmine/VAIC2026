import { generateText, Output } from "ai";
import { z } from "zod";

import type { RetrieveChunk, RetrieveResponse } from "../types/retrieval";
import type { HistoryEntry } from "./chat-context";
import { getModel } from "./provider";

// Port of open-notebook's "Ask" plan step: analyse the question, then fan out into
// a few focused sub-queries. Paperless runs each sub-query through its hybrid
// retriever (dense+BM25+RRF+neighbour), so recall is broader than a single query.

export interface SubQuery {
  query: string; // a short, self-contained search query
  focus: string; // what facet of the answer this query is meant to surface
}

export interface Strategy {
  reasoning: string;
  subqueries: SubQuery[];
}

const MAX_SUBQUERIES = 5;

const strategySchema = z.object({
  reasoning: z.string().describe("giải thích ngắn vì sao tách thành các truy vấn này"),
  subqueries: z
    .array(
      z.object({
        query: z.string().describe("truy vấn tìm kiếm ngắn, độc lập (đã tự chứa ngữ cảnh)"),
        focus: z.string().describe("khía cạnh của câu trả lời mà truy vấn này nhắm tới"),
      }),
    )
    .min(1)
    .max(MAX_SUBQUERIES),
});

const PLAN_MAX_TOKENS = 700;

/** Single-query fallback = today's behaviour; used when planning fails or is degenerate. */
export function fallbackStrategy(question: string): Strategy {
  return { reasoning: "", subqueries: [{ query: question, focus: "" }] };
}

/** Build the planning prompt (pure, so it is unit-testable without the LLM). */
export function buildPlanPrompt(question: string, history: HistoryEntry[]): string {
  const priorTurns = history.length
    ? "# HỘI THOẠI TRƯỚC (để hiểu ngữ cảnh câu hỏi)\n" +
      history.map((h) => `${h.role === "user" ? "Người dùng" : "Trợ lý"}: ${h.content}`).join("\n") +
      "\n\n"
    : "";

  return (
    "Bạn lập chiến lược tìm kiếm cho một hệ thống hỏi-đáp trên MỘT văn bản pháp lý.\n" +
    `Phân tích câu hỏi rồi tách thành 1–${MAX_SUBQUERIES} truy vấn tìm kiếm.\n` +
    "- Câu hỏi đơn giản, một khía cạnh → chỉ 1 truy vấn.\n" +
    `- Câu hỏi nhiều khía cạnh → tách tối đa ${MAX_SUBQUERIES} truy vấn, mỗi truy vấn một facet ` +
    "(dùng cả từ đồng nghĩa để tăng recall).\n" +
    "- Mỗi truy vấn phải NGẮN, ĐỘC LẬP, tự chứa ngữ cảnh (đã thay đại từ/hồi chỉ bằng chủ thể cụ thể).\n\n" +
    priorTurns +
    "# CÂU HỎI\n" +
    question
  );
}

/**
 * Fuse the per-sub-query result lists with Reciprocal Rank Fusion (k=60, the same
 * constant the retriever uses). A chunk surfaced by several sub-queries — consensus —
 * outranks a chunk seen once. Dedupes by position and caps the merged set.
 */
export function mergeAndDedupe(
  results: RetrieveResponse[],
  cap: number,
  k = 60,
): RetrieveChunk[] {
  const fused = new Map<number, { chunk: RetrieveChunk; score: number }>();
  for (const res of results) {
    res.chunks.forEach((chunk, rank) => {
      const contribution = 1 / (k + rank + 1);
      const existing = fused.get(chunk.position);
      if (existing) {
        existing.score += contribution;
      } else {
        fused.set(chunk.position, { chunk, score: contribution });
      }
    });
  }
  return [...fused.values()]
    .sort((a, b) => b.score - a.score)
    .slice(0, cap)
    .map((e) => e.chunk);
}

/** Plan the search strategy with a cheap/fast model; fall back to single-query on any failure. */
export async function planStrategy(
  question: string,
  history: HistoryEntry[],
  model: string,
  temperature: number,
): Promise<Strategy> {
  try {
    const { output } = await generateText({
      model: getModel(model),
      temperature,
      maxOutputTokens: PLAN_MAX_TOKENS,
      output: Output.object({ schema: strategySchema }),
      prompt: buildPlanPrompt(question, history),
    });
    const strategy = output as Strategy;
    if (!strategy?.subqueries?.length) return fallbackStrategy(question);
    return strategy;
  } catch {
    return fallbackStrategy(question);
  }
}
