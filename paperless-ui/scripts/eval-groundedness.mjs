// Online eval: chấm GROUNDEDNESS + ĐỘ CHÍNH XÁC TRÍCH DẪN bằng LLM-as-judge,
// rồi đẩy điểm lên Langfuse.
//
// Vì sao cần: reranker đã có số offline (Recall/MRR/nDCG) — đó là chất lượng
// TRUY XUẤT. Nhưng tiêu chí "Grounding & độ tin cậy" hỏi câu khác: câu trả lời
// có bịa không, và trích dẫn trang/Điều có đúng chỗ không. Đây là đo khâu SINH.
//
//   node scripts/eval-groundedness.mjs --n 5
//   node scripts/eval-groundedness.mjs --n 10 --no-push   # không đẩy lên Langfuse
//
// Nguồn dữ liệu: finetune/data/{eval_indomain,chunks}.jsonl (bộ held-out in-domain).
// LLM: gateway OpenAI-compatible (9router) — mặc định localhost:20128/v1.

import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "../..");

const args = process.argv.slice(2);
const flag = (n, d = null) => {
  const i = args.indexOf(n);
  return i >= 0 ? (args[i + 1]?.startsWith("--") ? true : args[i + 1]) : d;
};
const N = Number(flag("--n", 5));
const NO_PUSH = args.includes("--no-push");
// Đối chứng âm: bỏ chunk chứa đáp án khỏi ngữ cảnh. Câu trả lời BUỘC phải thiếu
// căn cứ → groundedness phải TỤT. Nếu vẫn ~1.0 nghĩa là giám khảo dễ dãi và
// thước đo vô nghĩa. Một thước đo không biết trượt thì không phải thước đo.
const ADVERSARIAL = args.includes("--adversarial");
const BASE_URL = process.env.NUXT_AI_BASE_URL || "http://localhost:20128/v1";
const MODEL = process.env.MODEL || "oc/deepseek-v4-flash-free";
const CTX_CHUNKS = 3;

async function env() {
  try {
    const txt = await readFile(resolve(ROOT, ".env"), "utf8");
    const get = (k) => txt.match(new RegExp(`^${k}=(.*)$`, "m"))?.[1]?.trim();
    return {
      pk: process.env.LANGFUSE_PUBLIC_KEY || get("LANGFUSE_PUBLIC_KEY"),
      sk: process.env.LANGFUSE_SECRET_KEY || get("LANGFUSE_SECRET_KEY"),
      base: process.env.LANGFUSE_BASE_URL || get("LANGFUSE_BASE_URL") || "https://cloud.langfuse.com",
    };
  } catch {
    return {};
  }
}

const jsonl = async (p) =>
  (await readFile(p, "utf8")).trim().split("\n").filter(Boolean).map(JSON.parse);

/** Gọi gateway. Áp các quirk đã biết: tắt reasoning, không stream, json_object. */
async function llm(messages, { json = false } = {}) {
  const body = {
    model: MODEL,
    messages,
    stream: false,
    reasoning_effort: "none",
    ...(json ? { response_format: { type: "json_object" } } : {}),
  };
  const res = await fetch(`${BASE_URL}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`gateway HTTP ${res.status}: ${(await res.text()).slice(0, 200)}`);
  const data = await res.json();
  return data.choices?.[0]?.message?.content ?? "";
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    const m = text.match(/\{[\s\S]*\}/); // model đôi khi bọc thêm chữ
    if (m) {
      try {
        return JSON.parse(m[0]);
      } catch {
        /* bỏ qua */
      }
    }
    return null;
  }
}

async function pushScores(cfg, { traceId, question, answer, groundedness, citationOk, answered, reason }) {
  if (NO_PUSH || !cfg.pk || !cfg.sk) return false;
  const now = new Date().toISOString();
  const uid = () => crypto.randomUUID();
  const batch = [
    {
      id: uid(),
      type: "trace-create",
      timestamp: now,
      body: {
        id: traceId,
        name: "eval-groundedness",
        timestamp: now,
        input: question,
        output: answer,
        tags: ["paperless-meetings", "eval"],
      },
    },
    {
      id: uid(),
      type: "score-create",
      timestamp: now,
      body: { id: uid(), traceId, name: "groundedness", value: groundedness, comment: reason },
    },
    {
      id: uid(),
      type: "score-create",
      timestamp: now,
      body: { id: uid(), traceId, name: "citation_accuracy", value: citationOk ? 1 : 0 },
    },
    {
      id: uid(),
      type: "score-create",
      timestamp: now,
      body: { id: uid(), traceId, name: "answered", value: answered ? 1 : 0 },
    },
  ];
  const auth = Buffer.from(`${cfg.pk}:${cfg.sk}`).toString("base64");
  const res = await fetch(`${cfg.base}/api/public/ingestion`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Basic ${auth}` },
    body: JSON.stringify({ batch }),
  });
  return res.ok;
}

// ── chạy ────────────────────────────────────────────────────────
const cfg = await env();
const chunks = await jsonl(resolve(ROOT, "finetune/data/chunks.jsonl"));
const evalRows = await jsonl(resolve(ROOT, "finetune/data/eval_indomain.jsonl"));
const byId = new Map(chunks.map((c) => [`${c.doc_id}::${c.position}`, c]));

const sample = evalRows.slice(0, N);
console.log(`Chấm ${sample.length} câu (model: ${MODEL})\n`);

const results = [];
for (const [i, row] of sample.entries()) {
  // Ngữ cảnh RAG: chunk đúng + vài chunk cùng tài liệu (giống lúc chạy thật).
  const others = row.candidate_ids.filter((c) => c !== row.positive_id);
  const ids = ADVERSARIAL
    ? others.slice(0, CTX_CHUNKS) // bỏ hẳn chunk chứa đáp án
    : [row.positive_id, ...others].slice(0, CTX_CHUNKS);
  const ctx = ids
    .map((id) => byId.get(id))
    .filter(Boolean)
    .map((c) => `[trang ${c.page ?? "?"} | ${c.section ?? "không rõ mục"}]\n${c.text}`)
    .join("\n\n---\n\n");

  let answer = "";
  let judged = null;
  try {
    answer = await llm([
      {
        role: "user",
        content:
          `Dựa CHỈ vào ngữ cảnh dưới đây, trả lời câu hỏi bằng tiếng Việt, ngắn gọn, ` +
          `và BẮT BUỘC trích dẫn theo dạng (trang X, Điều Y).\n\n` +
          `NGỮ CẢNH:\n${ctx}\n\nCÂU HỎI: ${row.query}`,
      },
    ]);

    const verdict = await llm(
      [
        {
          role: "user",
          content:
            `Bạn là giám khảo chấm chất lượng RAG. Trả về json.\n\n` +
            `NGỮ CẢNH:\n${ctx}\n\nCÂU HỎI: ${row.query}\n\nCÂU TRẢ LỜI: ${answer}\n\n` +
            `Chấm 3 tiêu chí:\n` +
            `1. groundedness: số 0..1 — mọi khẳng định trong câu trả lời có được ngữ cảnh ` +
            `chống lưng không (1 = hoàn toàn có căn cứ, 0 = bịa). LƯU Ý: câu từ chối ` +
            `("không có thông tin") vẫn tính là có căn cứ.\n` +
            `2. citation_ok: true/false — trích dẫn (trang/Điều) có khớp đúng nơi chứa thông tin không.\n` +
            `3. answered: true/false — câu trả lời có THỰC SỰ trả lời câu hỏi không ` +
            `(false nếu chỉ từ chối / nói không tìm thấy). Tiêu chí này để phát hiện ` +
            `trường hợp hệ thống "an toàn giả" bằng cách luôn từ chối.\n` +
            `Chỉ trả về json: {"groundedness": <số>, "citation_ok": <bool>, "answered": <bool>, "reason": "<1 câu>"}`,
        },
      ],
      { json: true },
    );
    judged = parseJson(verdict);
  } catch (e) {
    console.log(`  [${i + 1}] LỖI: ${e.message}`);
    continue;
  }

  if (!judged) {
    console.log(`  [${i + 1}] không parse được kết quả chấm — bỏ qua`);
    continue;
  }

  const g = Math.max(0, Math.min(1, Number(judged.groundedness) || 0));
  const cOk = !!judged.citation_ok;
  const ans = !!judged.answered;
  const traceId = crypto.randomUUID();
  const pushed = await pushScores(cfg, {
    traceId,
    question: row.query,
    answer,
    groundedness: g,
    citationOk: cOk,
    answered: ans,
    reason: String(judged.reason ?? "").slice(0, 300),
  });
  results.push({ g, cOk, ans });
  console.log(
    `  [${i + 1}] grounded=${g.toFixed(2)} citation=${cOk ? "OK" : "SAI"} answered=${ans ? "CO" : "KHONG"}${pushed ? " ↑langfuse" : ""}  ${String(judged.reason ?? "").slice(0, 70)}`,
  );
}

if (results.length === 0) {
  console.log("\nKhông có kết quả nào.");
  process.exit(1);
}
const meanG = results.reduce((s, r) => s + r.g, 0) / results.length;
const citAcc = results.filter((r) => r.cOk).length / results.length;
console.log(`\n=== TỔNG KẾT (n=${results.length}) ===`);
console.log(`groundedness trung bình : ${meanG.toFixed(3)}  (ngưỡng production ≥ 0.75 → ${meanG >= 0.75 ? "ĐẠT" : "CHƯA ĐẠT"})`);
console.log(`độ chính xác trích dẫn  : ${(citAcc * 100).toFixed(1)}%`);
const ansRate = results.filter((r) => r.ans).length / results.length;
console.log(`tỷ lệ thực sự trả lời   : ${(ansRate * 100).toFixed(1)}%  (thấp = hệ thống né bằng cách từ chối)`);
