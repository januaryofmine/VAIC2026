import { generateText, Output } from "ai";
import { z } from "zod";

import type { MapReduce } from "./map-reduce";
import { getModel } from "./provider";

export interface Term {
  term: string;
  explanation: string;
}
export interface TermsResult {
  terms: Term[];
}

const termsSchema = z.object({
  terms: z
    .array(
      z.object({
        term: z.string().min(1),
        explanation: z
          .string()
          .min(10)
          .describe("Giải thích ngắn gọn, dễ hiểu bằng tiếng Việt"),
      }),
    )
    // .min(10) ENFORCES deliverable #2 (≥10 terms): the AI SDK re-asks the model
    // when validation fails, so a short list can't silently ship. A 40-60pp legal
    // document always yields ≥10 specialized terms, so this never spuriously fails.
    .min(10, "Cần ít nhất 10 thuật ngữ chuyên ngành")
    .describe("Ít nhất 10 thuật ngữ chuyên ngành/pháp lý quan trọng, không trùng lặp"),
});

const MAP_MAX_TOKENS = 500;
const REDUCE_MAX_TOKENS = 2500;

const mapPrompt = (text: string) =>
  "Liệt kê các THUẬT NGỮ chuyên ngành, pháp lý hoặc viết tắt khó hiểu trong đoạn văn bản sau " +
  "(chỉ ghi tên thuật ngữ, mỗi dòng một cái, không giải thích):\n\n" +
  text;

const reducePrompt = (partials: string[]) =>
  "Dưới đây là các danh sách thuật ngữ trích từ một văn bản. Gộp trùng, chọn ÍT NHẤT 10 " +
  "thuật ngữ quan trọng nhất và giải thích ngắn gọn bằng tiếng Việt cho cán bộ:\n\n" +
  partials.join("\n");

/** Extract & explain specialized terms (deliverable #2), via the map-reduce engine. */
export function createAnthropicTermsExtractor(): MapReduce<TermsResult> {
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
        output: Output.object({ schema: termsSchema }),
        prompt: reducePrompt(partials),
      });
      return output as TermsResult;
    },
  };
}
