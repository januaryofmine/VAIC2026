// Thống kê trace LLM → bảng số đưa thẳng vào RESULTS.md / deck.
//
// Vì sao cần: yêu cầu nộp bài là "tóm tắt < 60 giây". Một lần đo thì chỉ là giai
// thoại; P50/P95 trên nhiều lượt mới là bằng chứng. Script đọc trace đã thu và
// tính phân vị + token, tách theo bước (summarize / terms / questions / chat).
//
//   node scripts/trace-stats.mjs                      # nguồn: Langfuse (đọc .env)
//   node scripts/trace-stats.mjs --file ../.llm-trace.jsonl   # nguồn: sink cục bộ
//   node scripts/trace-stats.mjs --md                 # in bảng markdown
//
// Đọc key từ .env ở gốc repo — không truyền secret qua command line.

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
const MD = args.includes("--md");
const FILE = flag("--file");
const LIMIT = Number(flag("--limit", 100));

async function envFromDotenv() {
  try {
    const txt = await readFile(resolve(ROOT, ".env"), "utf8");
    const get = (k) => txt.match(new RegExp(`^${k}=(.*)$`, "m"))?.[1]?.trim();
    return {
      pk: process.env.LANGFUSE_PUBLIC_KEY || get("LANGFUSE_PUBLIC_KEY"),
      sk: process.env.LANGFUSE_SECRET_KEY || get("LANGFUSE_SECRET_KEY"),
      base:
        process.env.LANGFUSE_BASE_URL || get("LANGFUSE_BASE_URL") || "https://cloud.langfuse.com",
    };
  } catch {
    return { pk: process.env.LANGFUSE_PUBLIC_KEY, sk: process.env.LANGFUSE_SECRET_KEY, base: "https://cloud.langfuse.com" };
  }
}

/** Bản ghi chuẩn hoá: { name, model, latencyMs, tokIn, tokOut } */
async function loadFromFile(path) {
  const txt = await readFile(resolve(process.cwd(), path), "utf8");
  return txt
    .trim()
    .split("\n")
    .filter(Boolean)
    .map(JSON.parse)
    .map((r) => ({
      name: r.name ?? "llm-call",
      model: r.model ?? "?",
      latencyMs: r.latencyMs ?? 0,
      tokIn: r.usage?.input ?? 0,
      tokOut: r.usage?.output ?? 0,
    }));
}

async function loadFromLangfuse() {
  const { pk, sk, base } = await envFromDotenv();
  if (!pk || !sk) {
    console.error("Thiếu LANGFUSE_PUBLIC_KEY/SECRET_KEY (trong .env). Dùng --file để đọc sink cục bộ.");
    process.exit(1);
  }
  const auth = Buffer.from(`${pk}:${sk}`).toString("base64");
  const res = await fetch(`${base}/api/public/observations?limit=${LIMIT}`, {
    headers: { Authorization: `Basic ${auth}` },
  });
  if (!res.ok) {
    console.error(`Langfuse API lỗi HTTP ${res.status}`);
    process.exit(1);
  }
  const j = await res.json();
  return (j.data ?? [])
    .filter((o) => o.type === "GENERATION")
    .map((o) => ({
      name: o.name ?? "llm-call",
      model: o.model ?? "?",
      latencyMs: Math.round((o.latency ?? 0) * 1000),
      tokIn: o.usage?.input ?? 0,
      tokOut: o.usage?.output ?? 0,
    }));
}

/** Phân vị kiểu "nearest-rank" — trung thực với mẫu nhỏ (không nội suy ảo). */
function pct(sorted, p) {
  if (sorted.length === 0) return 0;
  const rank = Math.ceil((p / 100) * sorted.length);
  return sorted[Math.min(Math.max(rank, 1), sorted.length) - 1];
}

function summarise(rows) {
  const lat = rows.map((r) => r.latencyMs).sort((a, b) => a - b);
  return {
    n: rows.length,
    p50: pct(lat, 50),
    p95: pct(lat, 95),
    max: lat[lat.length - 1] ?? 0,
    tokIn: rows.reduce((s, r) => s + r.tokIn, 0),
    tokOut: rows.reduce((s, r) => s + r.tokOut, 0),
  };
}

const rows = FILE ? await loadFromFile(FILE) : await loadFromLangfuse();
if (rows.length === 0) {
  console.log("Chưa có trace nào. Chạy app/test có bật tracing rồi thử lại.");
  process.exit(0);
}

const byName = new Map();
for (const r of rows) {
  if (!byName.has(r.name)) byName.set(r.name, []);
  byName.get(r.name).push(r);
}

const all = summarise(rows);
const BUDGET_MS = 60_000; // yêu cầu nộp bài: tóm tắt < 60s

if (MD) {
  console.log(`| Bước | n | P50 | P95 | Max | Token in | Token out |`);
  console.log(`|------|---|-----|-----|-----|----------|-----------|`);
  for (const [name, rs] of byName) {
    const s = summarise(rs);
    console.log(
      `| ${name} | ${s.n} | ${(s.p50 / 1000).toFixed(2)}s | ${(s.p95 / 1000).toFixed(2)}s | ${(s.max / 1000).toFixed(2)}s | ${s.tokIn} | ${s.tokOut} |`,
    );
  }
  console.log(
    `| **Tất cả** | **${all.n}** | **${(all.p50 / 1000).toFixed(2)}s** | **${(all.p95 / 1000).toFixed(2)}s** | **${(all.max / 1000).toFixed(2)}s** | **${all.tokIn}** | **${all.tokOut}** |`,
  );
  console.log(
    `\n> Ngân sách < 60s: P95 = ${(all.p95 / 1000).toFixed(2)}s → ${all.p95 < BUDGET_MS ? "✅ ĐẠT" : "❌ VƯỢT"}`,
  );
} else {
  console.log(`nguồn: ${FILE ? `file ${FILE}` : "Langfuse API"} | ${rows.length} generation\n`);
  for (const [name, rs] of byName) {
    const s = summarise(rs);
    console.log(
      `${name.padEnd(14)} n=${String(s.n).padStart(3)}  P50=${(s.p50 / 1000).toFixed(2)}s  P95=${(s.p95 / 1000).toFixed(2)}s  max=${(s.max / 1000).toFixed(2)}s  tok ${s.tokIn}/${s.tokOut}`,
    );
  }
  console.log(
    `\nTẤT CẢ        n=${String(all.n).padStart(3)}  P50=${(all.p50 / 1000).toFixed(2)}s  P95=${(all.p95 / 1000).toFixed(2)}s  max=${(all.max / 1000).toFixed(2)}s  tok ${all.tokIn}/${all.tokOut}`,
  );
  console.log(
    `Ngân sách <60s: P95=${(all.p95 / 1000).toFixed(2)}s → ${all.p95 < BUDGET_MS ? "ĐẠT" : "VƯỢT"}`,
  );
}
