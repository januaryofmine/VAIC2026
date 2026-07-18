// Deliverable feasibility test for #1 (summary <60s) and #2 (>=10 terms), run
// against a REAL 40-60pp document (doc 56, 59 pages) via the 9router gateway.
// Uses the SAME prompts + grouping as the app's map-reduce so it validates the
// production approach without the Nuxt/DB/retrieval-api stack.
//
//   node paperless-ui/scripts/test-prep-pack.mjs
//
// Requires 9router running at http://localhost:20128/v1.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, "../..");
const CHUNKS = path.join(REPO, "finetune", "data", "chunks.jsonl");
const DOC_ID = "56-10-01-2026-16h35p25-signed-pdf-78875c70"; // 59-page decision

const BASE = "http://localhost:20128/v1";
const MAP_MODEL = process.env.MODEL || "oc/deepseek-v4-flash-free";
const REDUCE_MODEL = process.env.MODEL || "oc/deepseek-v4-flash-free";
const TEMP = 0.3;
// deepseek-v4-flash-free is a REASONING model: it spends tokens "thinking" before
// the answer lands in `content`. Smaller groups + generous token ceilings let the
// answer complete. (The app targets Claude haiku/sonnet, which are non-reasoning
// and far faster — so this run is a conservative lower bound on speed.)
const MAP_GROUP_CHARS = 30000; // matches the app's ai.mapGroupChars
const CONCURRENCY = 10;
const MAP_TOKENS = 600;
const REDUCE_TOKENS = 3000;

// ── prompts (verbatim from the app's summarizer / terms extractor) ──
const sumMap = (t) =>
  "Tóm tắt đoạn văn bản hành chính/pháp luật sau bằng tiếng Việt, TỐI ĐA 5 gạch đầu dòng " +
  "cực ngắn gọn. Giữ số Điều/Khoản và ý chính, bỏ chi tiết vụn vặt:\n\n" + t;
const sumReduce = (p) =>
  "Dưới đây là các tóm tắt từng phần của một văn bản, theo thứ tự. Tổng hợp thành một bản " +
  "tóm tắt có cấu trúc bằng tiếng Việt, súc tích, cho cán bộ chuẩn bị họp. Trả về JSON đúng " +
  'dạng {"context","main_content","decision_points":[...],"impact"} (mỗi trường ngắn gọn):\n\n' +
  p.join("\n\n---\n\n");
const termMap = (t) =>
  "Liệt kê các THUẬT NGỮ chuyên ngành, pháp lý hoặc viết tắt khó hiểu trong đoạn văn bản sau " +
  "(chỉ ghi tên thuật ngữ, mỗi dòng một cái, không giải thích):\n\n" + t;
const termReduce = (p) =>
  "Dưới đây là các danh sách thuật ngữ trích từ một văn bản. Gộp trùng, chọn ÍT NHẤT 10 " +
  'thuật ngữ quan trọng nhất và giải thích ngắn gọn bằng tiếng Việt. Trả về JSON dạng ' +
  '{"terms":[{"term","explanation"}, ...]} với ít nhất 10 phần tử:\n\n' + p.join("\n");
const qMap = (t) =>
  "Tóm tắt các ý chính và điểm đáng lưu ý (có thể gây tranh luận) trong đoạn văn bản sau, " +
  "TỐI ĐA 5 gạch đầu dòng ngắn gọn bằng tiếng Việt:\n\n" + t;
const qReduce = (p) =>
  "Dựa trên các ý chính sau của một văn bản, hãy sinh ÍT NHẤT 5 câu hỏi phản biện, sắc bén " +
  'mà cán bộ nên chuẩn bị trước cuộc họp. Trả về JSON dạng {"questions":[...]} (ít nhất 5):\n\n' +
  p.join("\n");

async function chat(model, prompt, maxTokens, json = false) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const out = await chatOnce(model, prompt, maxTokens);
    if (out && out.trim()) return out;
    await new Promise((r) => setTimeout(r, 1500)); // free model can return empty; retry
  }
  return "";
}

async function chatOnce(model, prompt, maxTokens) {
  const body = {
    model,
    messages: [{ role: "user", content: prompt }],
    temperature: TEMP,
    max_tokens: maxTokens,
    stream: false, // 9router streams SSE by default for some providers
    reasoning_effort: "none", // deepseek-v4 is a reasoning model; turn thinking OFF
  };
  const r = await fetch(`${BASE}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const raw = await r.text();
  if (!r.ok) throw new Error(`9router ${r.status}: ${raw.slice(0, 300)}`);
  // Handle both plain JSON and SSE ("data: {...}\n\ndata: [DONE]") responses.
  if (raw.startsWith("data:")) {
    let content = "";
    for (const line of raw.split("\n")) {
      const s = line.replace(/^data:\s*/, "").trim();
      if (!s || s === "[DONE]") continue;
      try { content += JSON.parse(s).choices?.[0]?.delta?.content ?? ""; } catch {}
    }
    return content;
  }
  return JSON.parse(raw).choices?.[0]?.message?.content ?? "";
}

function parseJson(s, label = "") {
  let t = String(s).trim();
  // strip <think>...</think> reasoning and ```json fences some models emit
  t = t.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) t = fence[1].trim();
  const m = t.match(/\{[\s\S]*\}/);
  const cand = m ? m[0] : t;
  try {
    return JSON.parse(cand);
  } catch (e) {
    console.error(`\n[parse ${label}] len=${s.length} — raw head:\n${String(s).slice(0, 600)}\n`);
    throw e;
  }
}

function groupChunks(texts, maxChars) {
  const groups = [];
  let cur = [], size = 0;
  for (const t of texts) {
    if (cur.length && size + t.length > maxChars) { groups.push(cur); cur = []; size = 0; }
    cur.push(t); size += t.length;
  }
  if (cur.length) groups.push(cur);
  return groups;
}

async function mapPool(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  const worker = async () => { while (next < items.length) { const i = next++; out[i] = await fn(items[i], i); } };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

async function main() {
  const rows = fs.readFileSync(CHUNKS, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  const doc = rows.filter((r) => r.doc_id === DOC_ID).sort((a, b) => a.position - b.position);
  const texts = doc.map((c) => c.text);
  const totalChars = texts.reduce((s, t) => s + t.length, 0);
  const groups = groupChunks(texts, MAP_GROUP_CHARS);
  const pages = Math.max(...doc.map((c) => c.page ?? 0));
  console.log(`Doc 56: ${doc.length} chunks, ${pages} trang, ${totalChars} ký tự -> ${groups.length} nhóm map`);
  console.log(`Models: map=${MAP_MODEL}  reduce=${REDUCE_MODEL}\n`);

  // ── Deliverable #1: structured summary, timed ──
  let t0 = Date.now();
  const sumPartials = await mapPool(groups, CONCURRENCY, (g) => chat(MAP_MODEL, sumMap(g.join("\n\n")), MAP_TOKENS));
  const summaryRaw = await chat(REDUCE_MODEL, sumReduce(sumPartials), REDUCE_TOKENS, true);
  const summary = parseJson(summaryRaw, "summary");
  const sumSecs = ((Date.now() - t0) / 1000).toFixed(1);

  console.log("========== #1 SUMMARIZATION ==========");
  console.log(`⏱  ${sumSecs}s  (yêu cầu < 60s -> ${Number(sumSecs) < 60 ? "ĐẠT ✅" : "TRƯỢT ❌"})`);
  console.log("Bối cảnh:", (summary.context || "").slice(0, 200));
  console.log("Nội dung chính:", (summary.main_content || "").slice(0, 300));
  console.log("Điểm quyết định:", (summary.decision_points || []).length, "mục");
  (summary.decision_points || []).slice(0, 4).forEach((d) => console.log("  -", d));
  console.log("Tác động:", (summary.impact || "").slice(0, 200));

  // ── Deliverable #2: >=10 explained terms, timed ──
  t0 = Date.now();
  const termPartials = await mapPool(groups, CONCURRENCY, (g) => chat(MAP_MODEL, termMap(g.join("\n\n")), MAP_TOKENS));
  const termsRaw = await chat(REDUCE_MODEL, termReduce(termPartials), REDUCE_TOKENS, true);
  const terms = parseJson(termsRaw, "terms").terms ?? [];
  const termSecs = ((Date.now() - t0) / 1000).toFixed(1);

  console.log("\n========== #2 THUẬT NGỮ ==========");
  console.log(`⏱  ${termSecs}s  |  ${terms.length} thuật ngữ (yêu cầu >=10 -> ${terms.length >= 10 ? "ĐẠT ✅" : "TRƯỢT ❌"})`);
  terms.slice(0, 12).forEach((t, i) => console.log(`  ${i + 1}. ${t.term}: ${(t.explanation || "").slice(0, 90)}`));

  // ── Deliverable #3: >=5 critical-thinking questions, timed ──
  t0 = Date.now();
  const qPartials = await mapPool(groups, CONCURRENCY, (g) => chat(MAP_MODEL, qMap(g.join("\n\n")), MAP_TOKENS));
  const qRaw = await chat(REDUCE_MODEL, qReduce(qPartials), REDUCE_TOKENS, true);
  const questions = parseJson(qRaw, "questions").questions ?? [];
  const qSecs = ((Date.now() - t0) / 1000).toFixed(1);

  console.log("\n========== #3 CÂU HỎI GỢI Ý ==========");
  console.log(`⏱  ${qSecs}s  |  ${questions.length} câu hỏi (yêu cầu >=5 -> ${questions.length >= 5 ? "ĐẠT ✅" : "TRƯỢT ❌"})`);
  questions.slice(0, 6).forEach((q, i) => console.log(`  ${i + 1}. ${q}`));

  const ok = Number(sumSecs) < 60 && terms.length >= 10 && questions.length >= 5;
  console.log(`\n===== KẾT LUẬN: ${ok ? "CẢ 3 DELIVERABLE ĐẠT ✅" : "CẦN XEM LẠI ❌"} =====`);
}

main().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
