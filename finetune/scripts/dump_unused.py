"""Dump chunks that are NOT yet used as an answer in qa.jsonl.

Expanding the TEST set is what actually raises measurement resolution (see
EXPERIMENT_MULTIPROVINCE.md: at 18 questions each one is worth 5.6 points of
Recall@1, so small gains are invisible). This lists the material still available
to write fresh questions from.

Usage:
    .venv/Scripts/python.exe scripts/dump_unused.py --docs 6e83 a570 --per-doc 12
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default=str(ROOT / "data" / "chunks.jsonl"))
    ap.add_argument("--qa", default=str(ROOT / "data" / "qa.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "data" / "dump_unused.txt"))
    ap.add_argument("--docs", nargs="*", default=[], help="doc_id substrings to include")
    ap.add_argument("--per-doc", type=int, default=12)
    ap.add_argument("--min-len", type=int, default=400)
    ap.add_argument("--max-chars", type=int, default=750)
    args = ap.parse_args()

    chunks = [json.loads(l) for l in Path(args.chunks).read_text(encoding="utf-8").splitlines() if l.strip()]
    qa = [json.loads(l) for l in Path(args.qa).read_text(encoding="utf-8").splitlines() if l.strip()]
    used = {q["positive_chunk_id"] for q in qa}

    by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        cid = f'{c["doc_id"]}::{c["position"]}'
        if cid in used or len(c["text"]) < args.min_len:
            continue
        if args.docs and not any(s in c["doc_id"] for s in args.docs):
            continue
        by_doc[c["doc_id"]].append(c)

    lines, n = [], 0
    for doc_id, rows in by_doc.items():
        rows.sort(key=lambda r: r["position"])
        step = max(1, len(rows) // args.per_doc)
        for r in rows[::step][: args.per_doc]:
            lines.append(f'===== {doc_id}::{r["position"]} | page={r["page"]} section={r["section"]} =====')
            lines.append(r["text"].strip()[: args.max_chars])
            lines.append("")
            n += 1

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {n} unused chunks from {len(by_doc)} docs -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
