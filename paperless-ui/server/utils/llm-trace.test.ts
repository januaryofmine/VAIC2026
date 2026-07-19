/**
 * Tương quan trace: nhiều lời gọi LLM trong CÙNG một request phải gom về MỘT trace.
 *
 * Đây là điều kiện sống còn của tính năng: một câu hỏi gồm lời gọi lập kế hoạch +
 * N lần truy xuất + lời gọi sinh câu trả lời. Nếu mỗi cái mang một traceId riêng
 * thì Langfuse chỉ có các mảnh rời và KHÔNG truy nguyên được vì sao câu trả lời sai.
 *
 * Test dùng sink JSONL cục bộ nên không cần Langfuse/gateway → luôn chạy được.
 */
import { readFile, rm } from "node:fs/promises";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

const TRACE_FILE = "./.llm-trace-unit.jsonl";

async function loadModule() {
  // import động sau khi đã set env: config đọc process.env tại thời điểm gọi
  return await import("./llm-trace");
}

function fakeCall(name: string) {
  const start = new Date(Date.now() - 100);
  return { name, model: "test-model", input: "x", output: "y", startTime: start, endTime: new Date() };
}

describe("llm-trace: tương quan traceId", () => {
  beforeEach(async () => {
    process.env.LLM_TRACE_FILE = TRACE_FILE;
    await rm(TRACE_FILE, { force: true });
  });

  afterEach(async () => {
    delete process.env.LLM_TRACE_FILE;
    await rm(TRACE_FILE, { force: true });
  });

  it("gom mọi lời gọi trong cùng runWithTrace về một traceId", async () => {
    const { traceLLM, runWithTrace, newTraceId, flushTraces } = await loadModule();
    const traceId = newTraceId();

    await runWithTrace(traceId, async () => {
      traceLLM(fakeCall("plan")); // bước lập kế hoạch
      traceLLM(fakeCall("answer")); // bước sinh câu trả lời
    });
    await flushTraces();

    const recs = (await readFile(TRACE_FILE, "utf8"))
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));

    expect(recs).toHaveLength(2);
    expect(recs.map((r) => r.name).sort()).toEqual(["answer", "plan"]);
    // điểm mấu chốt: cùng một traceId, đúng id mà handler đã đặt
    expect(new Set(recs.map((r) => r.traceId)).size).toBe(1);
    expect(recs[0].traceId).toBe(traceId);
  });

  it("ngoài runWithTrace thì mỗi lời gọi có traceId riêng", async () => {
    const { traceLLM, flushTraces } = await loadModule();
    traceLLM(fakeCall("a"));
    traceLLM(fakeCall("b"));
    await flushTraces();

    const recs = (await readFile(TRACE_FILE, "utf8"))
      .trim()
      .split("\n")
      .map((l) => JSON.parse(l));
    expect(new Set(recs.map((r) => r.traceId)).size).toBe(2);
  });

  it("không cấu hình gì thì là no-op (không ghi file, không lỗi)", async () => {
    delete process.env.LLM_TRACE_FILE;
    const { traceLLM, flushTraces } = await loadModule();
    expect(() => traceLLM(fakeCall("x"))).not.toThrow();
    await flushTraces();
    await expect(readFile(TRACE_FILE, "utf8")).rejects.toThrow(); // file không tồn tại
  });
});

describe("llm-trace: instrumentFetch bắt input/output", () => {
  beforeEach(async () => {
    process.env.LLM_TRACE_FILE = TRACE_FILE;
    await rm(TRACE_FILE, { force: true });
  });
  afterEach(async () => {
    delete process.env.LLM_TRACE_FILE;
    await rm(TRACE_FILE, { force: true });
  });

  async function lastRecord() {
    const lines = (await readFile(TRACE_FILE, "utf8")).trim().split("\n");
    return JSON.parse(lines[lines.length - 1]);
  }

  it("gộp cả `system` (grounding của Anthropic) vào input, không chỉ messages", async () => {
    const { instrumentFetch, flushTraces } = await loadModule();
    const fakeInner = async () =>
      new Response(
        JSON.stringify({ model: "m", content: [{ type: "text", text: "hi" }], usage: { input_tokens: 5, output_tokens: 2 } }),
        { headers: { "content-type": "application/json" } },
      );
    const f = instrumentFetch(fakeInner as typeof globalThis.fetch);
    await f("https://x/api", {
      method: "POST",
      body: JSON.stringify({ model: "m", system: "NGỮ-CẢNH-luật", messages: [{ role: "user", content: "q" }] }),
    });
    await flushTraces();

    const rec = await lastRecord();
    // điểm mấu chốt: chat để grounding ở `system` → phải có mặt trong trace
    expect(rec.input.system).toBe("NGỮ-CẢNH-luật");
    expect(rec.input.messages).toEqual([{ role: "user", content: "q" }]);
    expect(rec.output).toBeTruthy();
    expect(rec.usage.input).toBe(5);
  });

  it("streaming: không đọc body nhưng vẫn ghi input kèm system", async () => {
    const { instrumentFetch, flushTraces } = await loadModule();
    const fakeInner = async () =>
      new Response("data: ...", { headers: { "content-type": "text/event-stream" } });
    const f = instrumentFetch(fakeInner as typeof globalThis.fetch);
    await f("https://x/api", {
      method: "POST",
      body: JSON.stringify({ model: "m", stream: true, system: "S", messages: [{ role: "user", content: "q" }] }),
    });
    await flushTraces();

    const rec = await lastRecord();
    expect(rec.input.system).toBe("S");
    expect(rec.metadata.streaming).toBe(true);
    expect(rec.output).toBeUndefined();
  });
});
