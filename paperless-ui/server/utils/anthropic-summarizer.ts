import { generateText, Output } from "ai";
import { z } from "zod";

import { getModel } from "./provider";
import type { StructuredSummary, Summarizer } from "./summarize";

const summarySchema = z.object({
  context: z.string().describe("Bối cảnh ban hành / mục đích của văn bản"),
  main_content: z.string().describe("Nội dung chính, tóm lược mạch lạc"),
  decision_points: z
    .array(z.string())
    .describe("Các điểm cần quyết định / lưu ý khi họp"),
  impact: z.string().describe("Tác động / ảnh hưởng dự kiến"),
});

// Output length dominates latency → keep both steps tight (concise prompt + cap).
const MAP_MAX_TOKENS = 400;
// Generous ceiling so the structured JSON never truncates mid-object ("No output
// generated"); the concise prompt is what actually keeps the summary short/fast.
const REDUCE_MAX_TOKENS = 2500;

const mapPrompt = (text: string) =>
  "Tóm tắt đoạn văn bản hành chính/pháp luật sau bằng tiếng Việt, TỐI ĐA 5 gạch đầu dòng " +
  "cực ngắn gọn. Giữ số Điều/Khoản và ý chính, bỏ chi tiết vụn vặt:\n\n" +
  text;

const reducePrompt = (partials: string[]) =>
  "Dưới đây là các tóm tắt từng phần của một văn bản, theo thứ tự. Tổng hợp thành một bản " +
  "tóm tắt có cấu trúc bằng tiếng Việt, súc tích, cho cán bộ chuẩn bị họp. Mỗi trường ngắn " +
  "gọn (main_content tối đa ~8 câu, mỗi decision_point 1 câu):\n\n" +
  partials.join("\n\n---\n\n");

/** Real Summarizer backed by Anthropic (Claude) via the AI SDK. */
export function createAnthropicSummarizer(): Summarizer {
  const { ai } = useRuntimeConfig();
  return {
    async mapSummary(text) {
      const { text: out } = await generateText({
        model: getModel(ai.summarizeMapModel),
        temperature: ai.temperature,
        maxOutputTokens: MAP_MAX_TOKENS,
        prompt: mapPrompt(text),
      });
      return out;
    },
    async reduceSummary(partials) {
      const { output } = await generateText({
        model: getModel(ai.summarizeReduceModel),
        temperature: ai.temperature,
        maxOutputTokens: REDUCE_MAX_TOKENS,
        output: Output.object({ schema: summarySchema }),
        prompt: reducePrompt(partials),
      });
      return output as StructuredSummary;
    },
  };
}
