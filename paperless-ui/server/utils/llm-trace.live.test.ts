/**
 * Integration test: instrumentFetch ghi được trace từ một lời gọi LLM THẬT.
 *
 * Tự SKIP khi gateway (9router) không chạy → `npm test` của đồng đội vẫn xanh.
 * Chạy có gateway:  npm test -- llm-trace.live
 */
import { readFile, rm } from "node:fs/promises";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const BASE_URL = process.env.NUXT_AI_BASE_URL || "http://localhost:20128/v1";
const MODEL = process.env.MODEL || "oc/deepseek-v4-flash-free";
const TRACE_FILE = "./.llm-trace-live.jsonl";

async function gatewayUp(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE_URL}/models`, { signal: AbortSignal.timeout(3000) });
    return r.ok;
  } catch {
    return false;
  }
}

const up = await gatewayUp();

describe.skipIf(!up)("llm-trace (live gateway)", () => {
  let instrumentFetch: typeof import("./llm-trace").instrumentFetch;
  let flushTraces: typeof import("./llm-trace").flushTraces;

  beforeAll(async () => {
    process.env.LLM_TRACE_FILE = TRACE_FILE; // bật sink cục bộ trước khi wrap
    await rm(TRACE_FILE, { force: true });
    ({ instrumentFetch, flushTraces } = await import("./llm-trace"));
  });

  afterAll(async () => {
    delete process.env.LLM_TRACE_FILE;
  });

  it("ghi 1 bản ghi trace có latency + token cho lời gọi thật", async () => {
    const f = instrumentFetch(globalThis.fetch);
    const res = await f(`${BASE_URL}/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: MODEL,
        messages: [{ role: "user", content: "Trả lời đúng một từ: xin chào" }],
        stream: false,
        reasoning_effort: "none",
      }),
    });
    expect(res.ok).toBe(true);

    // response gốc vẫn đọc được (clone không tiêu thụ body) — điều kiện sống còn
    const body: any = await res.json();
    expect(body.choices?.[0]?.message).toBeDefined();

    // Bắt buộc: trace là fire-and-forget, tiến trình ngắn hạn (test/serverless)
    // sẽ thoát trước khi POST xong nếu không flush → trace mất âm thầm.
    await flushTraces();
    const lines = (await readFile(TRACE_FILE, "utf8")).trim().split("\n");
    expect(lines.length).toBeGreaterThanOrEqual(1);

    const rec = JSON.parse(lines[lines.length - 1]);
    expect(rec.name).toBe("llm-call");
    expect(rec.latencyMs).toBeGreaterThan(0);
    expect(rec.model).toBeTruthy();
    expect(rec.input).toBeTruthy();
    console.log(
      `[trace] model=${rec.model} latency=${rec.latencyMs}ms ` +
        `tokens in/out=${rec.usage?.input ?? "?"}/${rec.usage?.output ?? "?"}`,
    );
  }, 60_000);
});
