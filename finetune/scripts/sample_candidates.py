"""Dump content-bearing chunks in a compact, readable form so Claude Code can
author in-domain QA pairs (question whose answer lives in that chunk).

Balances across documents so the 59-page doc doesn't dominate. Output is human-
readable, one chunk per block, keyed by "<doc_id>::<position>".

Usage:
    .venv/Scripts/python.exe scripts/sample_candidates.py --per-doc 12
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS = ROOT / "data" / "chunks.jsonl"
DEFAULT_OUT = ROOT / "data" / "qa_candidates.txt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-doc", type=int, default=12)
    ap.add_argument("--min-len", type=int, default=250)
    ap.add_argument("--chunks", default=str(DEFAULT_CHUNKS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--max-chars", type=int, default=900, help="truncate each chunk")
    args = ap.parse_args()
    CHUNKS, OUT = Path(args.chunks), Path(args.out)

    by_doc: dict[str, list[dict]] = defaultdict(list)
    for line in CHUNKS.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if len(r["text"]) >= args.min_len:
            by_doc[r["doc_id"]].append(r)

    picked = []
    for doc_id, rows in by_doc.items():
        # spread picks across the document
        rows.sort(key=lambda r: r["position"])
        step = max(1, len(rows) // args.per_doc)
        picked.extend(rows[::step][: args.per_doc])

    lines = [f"# {len(picked)} candidate chunks from {len(by_doc)} docs\n"]
    for r in picked:
        key = f'{r["doc_id"]}::{r["position"]}'
        meta = f'page={r["page"]} section={r["section"]}'
        lines.append(f"===== {key} | {meta} =====")
        lines.append(r["text"].strip()[: args.max_chars])
        lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(picked)} candidates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
