import { generateText, Output } from "ai";
import { z } from "zod";

import type { MapReduce } from "./map-reduce";
import { getModel } from "./provider";

export interface QuestionsResult {
  questions: string[];
}

const questionsSchema = z.object({
  questions: z
    .array(z.string().min(10))
    // .min(5) ENFORCES deliverable #3 (≥5 critical questions): the AI SDK re-asks
    // the model on a short list, so it can't silently ship fewer than 5.
    .min(5, "Cần ít nhất 5 câu hỏi phản biện")
    .describe("Ít nhất 5 câu hỏi phản biện, chất lượng, cán bộ nên chuẩn bị"),
});

const MAP_MAX_TOKENS = 400;
// Headroom so the structured JSON never truncates mid-object ("No output generated").
const REDUCE_MAX_TOKENS = 2000;

const mapPrompt = (text: string) =>
  "Tóm tắt các ý chính và điểm đáng lưu ý (có thể gây tranh luận) trong đoạn văn bản sau, " +
  "TỐI ĐA 5 gạch đầu dòng ngắn gọn bằng tiếng Việt:\n\n" +
  text;

const reducePrompt = (partials: string[]) =>
  "Dựa trên các ý chính sau của một văn bản, hãy sinh ÍT NHẤT 5 câu hỏi phản biện, sắc bén " +
  "mà cán bộ nên chuẩn bị trước cuộc họp (bằng tiếng Việt):\n\n" +
  partials.join("\n");

/** Generate critical-thinking questions (deliverable #3), via the map-reduce engine. */
export function createAnthropicQuestionGenerator(): MapReduce<QuestionsResult> {
  const { ai } = useRuntimeConfig();
  return {
    async mapText(text) {
      const { text: out } = await generateText({
        model: getModel(ai.summarizeMapModel),
        temperature: ai.temperature,
        maxOutputTokens: MAP_MAX_TOKENS,
        prompt: mapPrompt(text),
      });
      return out;
    },
    async reduce(partials) {
      const { output } = await generateText({
        model: getModel(ai.summarizeReduceModel),
        temperature: ai.temperature,
        maxOutputTokens: REDUCE_MAX_TOKENS,
        output: Output.object({ schema: questionsSchema }),
        prompt: reducePrompt(partials),
      });
      return output as QuestionsResult;
    },
  };
}
