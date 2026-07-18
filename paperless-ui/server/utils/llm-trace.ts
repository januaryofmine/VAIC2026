/**
 * AI monitoring — gửi trace mỗi lần gọi LLM lên Langfuse.
 *
 * Vì sao cần: tiêu chí "An toàn AI, Grounding & Độ tin cậy" và lộ trình pilot ở
 * UBND đòi hỏi *đo được* chứ không chỉ tuyên bố. Trace cho ta latency thật
 * (chứng minh yêu cầu tóm tắt < 60s), token/chi phí mỗi tài liệu, và input/output
 * để chấm groundedness / độ chính xác trích dẫn sau này.
 *
 * Thiết kế có chủ đích:
 * - KHÔNG thêm dependency: POST thẳng Langfuse ingestion API bằng fetch.
 * - No-op khi thiếu key → đồng đội chạy máy không cấu hình gì vẫn bình thường.
 * - Fire-and-forget + không bao giờ ném lỗi → monitoring không thể làm hỏng request.
 * - Không đọc body của response streaming (sẽ nuốt mất stream của người dùng).
 *
 * Bật: đặt LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY (tuỳ chọn LANGFUSE_BASE_URL)
 * trong .env. Self-host on-prem chỉ cần đổi LANGFUSE_BASE_URL.
 */

type Usage = { input?: number; output?: number; total?: number };

function config() {
  const publicKey = process.env.LANGFUSE_PUBLIC_KEY;
  const secretKey = process.env.LANGFUSE_SECRET_KEY;
  const baseUrl = process.env.LANGFUSE_BASE_URL || "https://cloud.langfuse.com";
  if (!publicKey || !secretKey) return null;
  return { publicKey, secretKey, baseUrl };
}

/**
 * Sink cục bộ (JSONL) — bật bằng LLM_TRACE_FILE.
 * Có chủ đích: bản on-prem ở UBND không nhất thiết được phép gửi trace ra ngoài,
 * và PoC/CI cần đo được mà không phụ thuộc tài khoản SaaS nào.
 */
function traceFile(): string | null {
  return process.env.LLM_TRACE_FILE || null;
}

export function isTracingEnabled(): boolean {
  return config() !== null || traceFile() !== null;
}

async function appendLocal(record: unknown): Promise<void> {
  const file = traceFile();
  if (!file) return;
  try {
    const { appendFile } = await import("node:fs/promises");
    await appendFile(file, JSON.stringify(record) + "\n", "utf8");
  } catch {
    // nuốt: lỗi telemetry không được phá luồng chính
  }
}

function uuid(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Gửi 1 batch sự kiện. Nuốt mọi lỗi — monitoring không được phá luồng chính. */
async function send(events: unknown[]): Promise<void> {
  const cfg = config();
  if (!cfg || events.length === 0) return;
  try {
    const auth = Buffer.from(`${cfg.publicKey}:${cfg.secretKey}`).toString("base64");
    await globalThis.fetch(`${cfg.baseUrl}/api/public/ingestion`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Basic ${auth}` },
      body: JSON.stringify({ batch: events }),
    });
  } catch {
    // nuốt: lỗi telemetry không bao giờ được nổi lên người dùng
  }
}

export type TraceLLMInput = {
  traceId?: string;
  /** Tên bước: summarize | terms | questions | chat … */
  name: string;
  model: string;
  input: unknown;
  output?: unknown;
  usage?: Usage;
  startTime: Date;
  endTime: Date;
  metadata?: Record<string, unknown>;
  error?: string;
};

/** Ghi 1 lần gọi LLM (kèm trace bao ngoài) — fire-and-forget. */
export function traceLLM(e: TraceLLMInput): void {
  if (!isTracingEnabled()) return;
  const traceId = e.traceId ?? uuid();
  const now = new Date().toISOString();
  const latencyMs = e.endTime.getTime() - e.startTime.getTime();

  // Sink cục bộ: bản ghi phẳng, dễ tính P50/P95 + tổng token bằng script.
  void appendLocal({
    traceId,
    name: e.name,
    model: e.model,
    latencyMs,
    usage: e.usage,
    startTime: e.startTime.toISOString(),
    endTime: e.endTime.toISOString(),
    error: e.error,
    metadata: e.metadata,
    input: e.input,
    output: e.output,
  });

  const events = [
    {
      id: uuid(),
      type: "trace-create",
      timestamp: now,
      body: {
        id: traceId,
        name: e.name,
        timestamp: e.startTime.toISOString(),
        metadata: e.metadata,
        tags: ["paperless-meetings"],
      },
    },
    {
      id: uuid(),
      type: "generation-create",
      timestamp: now,
      body: {
        id: uuid(),
        traceId,
        name: e.name,
        startTime: e.startTime.toISOString(),
        endTime: e.endTime.toISOString(),
        model: e.model,
        input: e.input,
        output: e.error ? { error: e.error } : e.output,
        usage: e.usage
          ? { input: e.usage.input, output: e.usage.output, total: e.usage.total, unit: "TOKENS" }
          : undefined,
        level: e.error ? "ERROR" : "DEFAULT",
        statusMessage: e.error,
        metadata: {
          ...e.metadata,
          latencyMs: e.endTime.getTime() - e.startTime.getTime(),
        },
      },
    },
  ];

  void send(events); // không await: không chặn response
}

/**
 * Bọc một `fetch` để mọi lời gọi LLM (OpenAI-compatible hoặc Anthropic) đều
 * được ghi trace. Đặt ở provider.ts nên tất cả điểm gọi (summarize / terms /
 * questions / chat) đều được bao mà không phải sửa từng nơi.
 */
export function instrumentFetch(inner: typeof globalThis.fetch): typeof globalThis.fetch {
  if (!isTracingEnabled()) return inner; // không cấu hình → trả nguyên bản

  return async (input, init) => {
    const startTime = new Date();
    let req: any = null;
    if (init?.body && typeof init.body === "string") {
      try {
        req = JSON.parse(init.body);
      } catch {
        /* body không phải JSON */
      }
    }
    const model = req?.model ?? "unknown";
    const streaming = req?.stream === true;

    let res: Response;
    try {
      res = await inner(input, init);
    } catch (err) {
      traceLLM({
        name: "llm-call",
        model,
        input: req?.messages ?? req,
        startTime,
        endTime: new Date(),
        error: err instanceof Error ? err.message : String(err),
      });
      throw err;
    }

    const endTime = new Date();
    // Response streaming: KHÔNG đọc body (sẽ nuốt mất stream) — chỉ ghi latency.
    const isStream =
      streaming || (res.headers.get("content-type") ?? "").includes("text/event-stream");

    if (isStream) {
      traceLLM({
        name: "llm-call",
        model,
        input: req?.messages ?? req,
        startTime,
        endTime,
        metadata: { streaming: true, status: res.status },
      });
      return res;
    }

    // Không stream: clone để đọc mà không tiêu thụ response gốc.
    try {
      const data: any = await res.clone().json();
      const choice = data?.choices?.[0]?.message?.content ?? data?.content;
      traceLLM({
        name: "llm-call",
        model: data?.model ?? model,
        input: req?.messages ?? req,
        output: choice ?? data,
        usage: data?.usage
          ? {
              input: data.usage.prompt_tokens ?? data.usage.input_tokens,
              output: data.usage.completion_tokens ?? data.usage.output_tokens,
              total: data.usage.total_tokens,
            }
          : undefined,
        startTime,
        endTime,
        metadata: { status: res.status },
      });
    } catch {
      traceLLM({
        name: "llm-call",
        model,
        input: req?.messages ?? req,
        startTime,
        endTime,
        metadata: { status: res.status, note: "response not JSON" },
      });
    }
    return res;
  };
}
