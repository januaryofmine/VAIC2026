"""Dump chunks for specific doc_ids (substring match) for QA authoring."""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = [json.loads(l) for l in (ROOT / "data" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
outpath = ROOT / "data" / "dump.txt"
subs = sys.argv[1:]
out = []
for r in rows:
    if any(s in r["doc_id"] for s in subs) and len(r["text"]) >= 150:
        out.append(f'===== {r["doc_id"]}::{r["position"]} | page={r["page"]} section={r["section"]} =====')
        out.append(r["text"].strip()[:1100])
        out.append("")
outpath.write_text("\n".join(out), encoding="utf-8")
print(f"wrote {len(out)} lines -> {outpath}")
