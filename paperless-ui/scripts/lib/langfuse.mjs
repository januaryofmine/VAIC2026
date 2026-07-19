// Client Langfuse tối giản dùng chung cho các script đo đạc (.mjs).
//
// Vì sao tách ra: app dùng server/utils/llm-trace.ts (TypeScript, chạy trong
// Nitro). Các script đo là .mjs chạy bằng node thuần nên không import được .ts.
// Gom logic ingestion vào đây để 3 nơi không mỗi nơi một bản.
//
// No-op khi thiếu LANGFUSE_PUBLIC_KEY/SECRET_KEY (đọc từ .env ở gốc repo).

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
let _cfg;
const _pending = new Set();

async function cfg() {
  if (_cfg !== undefined) return _cfg;
  let get = () => undefined;
  try {
    const txt = await readFile(resolve(ROOT, ".env"), "utf8");
    get = (k) => txt.match(new RegExp(`^${k}=(.*)$`, "m"))?.[1]?.trim();
  } catch {
    /* không có .env — vẫn thử biến môi trường */
  }
  const pk = process.env.LANGFUSE_PUBLIC_KEY || get("LANGFUSE_PUBLIC_KEY");
  const sk = process.env.LANGFUSE_SECRET_KEY || get("LANGFUSE_SECRET_KEY");
  _cfg = pk && sk
    ? {
        pk,
        sk,
        base: process.env.LANGFUSE_BASE_URL || get("LANGFUSE_BASE_URL") || "https://cloud.langfuse.com",
      }
    : null;
  return _cfg;
}

export async function isEnabled() {
  return (await cfg()) !== null;
}

/** Gửi 1 batch event. Nuốt lỗi (đo đạc không được phá script) — LANGFUSE_DEBUG=1 để thấy. */
export async function pushBatch(events) {
  const c = await cfg();
  if (!c || !events?.length) return false;
  try {
    const auth = Buffer.from(`${c.pk}:${c.sk}`).toString("base64");
    const res = await fetch(`${c.base}/api/public/ingestion`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Basic ${auth}` },
      body: JSON.stringify({ batch: events }),
      signal: AbortSignal.timeout(15_000),
    });
    if (process.env.LANGFUSE_DEBUG) {
      console.warn(`[langfuse] HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`);
    }
    return res.ok;
  } catch (e) {
    if (process.env.LANGFUSE_DEBUG) console.warn("[langfuse] push failed:", e.message);
    return false;
  }
}

const uid = () => crypto.randomUUID();

/**
 * Ghi 1 generation (1 lời gọi LLM) kèm trace bao ngoài.
 * Fire-and-forget nhưng có theo dõi → gọi flush() trước khi script thoát,
 * nếu không tiến trình ngắn hạn sẽ kết thúc trước khi POST xong.
 */
export function traceGeneration({
  traceId,
  name,
  model,
  input,
  output,
  usage,
  startTime,
  endTime,
  metadata,
}) {
  const tid = traceId ?? uid();
  const now = new Date().toISOString();
  const p = pushBatch([
    {
      id: uid(),
      type: "trace-create",
      timestamp: now,
      body: { id: tid, name, timestamp: startTime.toISOString(), tags: ["paperless-meetings", "bench"] },
    },
    {
      id: uid(),
      type: "generation-create",
      timestamp: now,
      body: {
        id: uid(),
        traceId: tid,
        name,
        model,
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        input,
        output,
        usage: usage
          ? { input: usage.input, output: usage.output, total: usage.total, unit: "TOKENS" }
          : undefined,
        metadata: { ...(metadata || {}), latencyMs: endTime.getTime() - startTime.getTime() },
      },
    },
  ]);
  _pending.add(p);
  void p.finally(() => _pending.delete(p));
  return tid;
}

/** Chờ mọi lần gửi đang bay. BẮT BUỘC gọi cuối script. */
export async function flush() {
  await Promise.allSettled([..._pending]);
}
