// Verifies the app's LLM path works against an OpenAI-compatible gateway (9router):
//   1) plain generateText returns non-empty content (reasoning disabled),
//   2) structured output (Output.object + zod) parses — used by summarize/terms/questions.
//
//   node paperless-ui/scripts/test-provider.mjs
//
// Mirrors server/utils/provider.ts exactly (same options + noReasoningFetch).

import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { generateText, Output } from "ai";
import { z } from "zod";

const BASE_URL = process.env.NUXT_AI_BASE_URL || "http://localhost:20128/v1";
const MODEL = process.env.MODEL || "oc/deepseek-v4-flash-free";

// same wrapping fetch as provider.ts
const noReasoningFetch = async (input, init) => {
  if (init?.body && typeof init.body === "string") {
    try {
      const body = JSON.parse(init.body);
      body.reasoning_effort = "none";
      if (body.stream === undefined) body.stream = false;
      if (body.response_format?.type === "json_schema") {
        const schema = body.response_format.json_schema?.schema;
        body.response_format = { type: "json_object" };
        const last = body.messages?.[body.messages.length - 1];
        if (schema && last && typeof last.content === "string") {
          last.content +=
            "\n\nCHỈ trả về một JSON hợp lệ đúng schema sau, không kèm chữ nào khác:\n" +
            JSON.stringify(schema);
        }
      }
      if (body.response_format?.type === "json_object" && Array.isArray(body.messages)) {
        const mentionsJson = body.messages.some(
          (m) => typeof m.content === "string" && /json/i.test(m.content),
        );
        const last = body.messages[body.messages.length - 1];
        if (!mentionsJson && last && typeof last.content === "string") {
          last.content += "\n\nCHỈ trả về một JSON hợp lệ, không kèm chữ nào khác.";
        }
      }
      if (process.env.DEBUG_BODY) {
        console.log("[req keys]", Object.keys(body).join(","),
          "| response_format:", JSON.stringify(body.response_format));
        if (body.response_format) {
          const fs = await import("node:fs");
          fs.writeFileSync("last-structured-body.json", JSON.stringify(body, null, 2));
          console.log("[wrote last-structured-body.json]");
        }
      }
      init = { ...init, body: JSON.stringify(body) };
    } catch {}
  }
  return globalThis.fetch(input, init);
};

const gateway = createOpenAICompatible({
  name: "gateway",
  baseURL: BASE_URL,
  apiKey: "unused",
  supportsStructuredOutputs: true,
  fetch: noReasoningFetch,
});

const summarySchema = z.object({
  context: z.string(),
  main_content: z.string(),
  decision_points: z.array(z.string()),
  impact: z.string(),
});

async function main() {
  console.log(`gateway: ${BASE_URL}\nmodel:   ${MODEL}\n`);

  // 1) plain text
  let t = Date.now();
  const { text } = await generateText({
    model: gateway(MODEL),
    temperature: 0.3,
    maxOutputTokens: 300,
    prompt: "Tóm tắt 2 gạch đầu dòng: Quyết định của UBND tỉnh công bố danh mục văn bản hết hiệu lực năm 2025.",
  });
  console.log(`[1] generateText: ${((Date.now() - t) / 1000).toFixed(1)}s, len=${text.length}`);
  console.log(text.slice(0, 220));
  if (!text.trim()) throw new Error("empty content — reasoning not disabled?");

  // 2) structured output (what summarize/terms/questions rely on)
  t = Date.now();
  const { output } = await generateText({
    model: gateway(MODEL),
    temperature: 0.3,
    maxOutputTokens: 1200,
    output: Output.object({ schema: summarySchema }),
    prompt:
      "Tổng hợp thành tóm tắt có cấu trúc cho cán bộ họp:\n\n" +
      "- UBND tỉnh Điện Biên công bố 50 văn bản QPPL hết hiệu lực năm 2025.\n" +
      "- Gồm 22 Nghị quyết HĐND và 28 Quyết định UBND.\n" +
      "- Nhiều quyết định bị thay thế bởi văn bản mới năm 2025.",
  });
  console.log(`\n[2] structured output: ${((Date.now() - t) / 1000).toFixed(1)}s`);
  console.log("  context:", (output.context || "").slice(0, 120));
  console.log("  main_content:", (output.main_content || "").slice(0, 160));
  console.log("  decision_points:", output.decision_points?.length ?? 0, "mục");
  console.log("  impact:", (output.impact || "").slice(0, 120));

  const ok = text.trim().length > 0 && output.context && Array.isArray(output.decision_points);
  console.log(`\n===== PROVIDER PATH: ${ok ? "HOẠT ĐỘNG ✅" : "LỖI ❌"} =====`);
  if (!ok) process.exit(1);
}

main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
