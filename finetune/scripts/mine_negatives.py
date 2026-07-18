"""Build cross-encoder training triples from qa.jsonl using BM25 hard negatives.

For each (query, positive_chunk) pair, the candidate pool is all chunks of the
SAME document (mirrors serving, which scopes retrieval by document_id). Hard
negatives = highest-BM25 wrong chunks (lexically similar but not the answer) —
exactly what forces the reranker to learn meaning over keyword overlap. Tops up
with random cross-doc negatives when a document is too small.

Outputs:
    data/train_indomain.jsonl  {query, positive, negatives:[...]}  (in-domain adapt)
    data/eval_indomain.jsonl   {query, doc_id, positive_id, candidate_ids:[...]}

Usage:
    .venv/Scripts/python.exe scripts/mine_negatives.py --neg 6
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from rank_bm25 import BM25Okapi

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / "data" / "chunks.jsonl"
QA = ROOT / "data" / "qa.jsonl"
TRAIN = ROOT / "data" / "train_indomain.jsonl"
EVAL = ROOT / "data" / "eval_indomain.jsonl"

RNG = random.Random(42)  # deterministic (Math.random-free, reproducible)


def tok(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--neg", type=int, default=6, help="hard negatives per query")
    ap.add_argument("--test-frac", type=float, default=0.35, help="held-out fraction for eval")
    args = ap.parse_args()

    chunks = [json.loads(l) for l in CHUNKS.read_text(encoding="utf-8").splitlines()]
    by_id = {f'{c["doc_id"]}::{c["position"]}': c for c in chunks}
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for c in chunks:
        by_doc[c["doc_id"]].append(c)

    qa = [json.loads(l) for l in QA.read_text(encoding="utf-8").splitlines() if l.strip()]

    # Validate positives exist.
    missing = [q["positive_chunk_id"] for q in qa if q["positive_chunk_id"] not in by_id]
    if missing:
        print("ERROR: positive ids not found in chunks:", missing, file=sys.stderr)
        return 1

    all_ids = list(by_id.keys())

    # Clean train/test split: group queries by positive chunk so no positive chunk
    # appears in BOTH splits (prevents memorization leakage). Shuffle groups by seed.
    groups: dict[str, list[dict]] = defaultdict(list)
    for q in qa:
        groups[q["positive_chunk_id"]].append(q)
    group_keys = sorted(groups.keys())
    RNG.shuffle(group_keys)
    n_test_q = int(len(qa) * args.test_frac)
    test_qs, train_qs, taken = [], [], 0
    for gk in group_keys:
        if taken < n_test_q:
            test_qs.extend(groups[gk])
            taken += len(groups[gk])
        else:
            train_qs.extend(groups[gk])
    print(f"split: {len(train_qs)} train / {len(test_qs)} test queries "
          f"(grouped by positive chunk, no leakage)")

    train_rows, eval_rows = [], []

    # eval set = held-out test queries only
    for q in test_qs:
        doc_chunks = by_doc[q["doc_id"]]
        cand_ids = [f'{c["doc_id"]}::{c["position"]}' for c in doc_chunks]
        eval_rows.append({
            "query": q["query"], "doc_id": q["doc_id"],
            "positive_id": q["positive_chunk_id"], "candidate_ids": cand_ids,
        })

    # train triples = train queries with BM25 hard negatives
    for q in train_qs:
        pos_id = q["positive_chunk_id"]
        doc_id = q["doc_id"]
        doc_chunks = by_doc[doc_id]
        cand_ids = [f'{c["doc_id"]}::{c["position"]}' for c in doc_chunks]

        # hard negatives via BM25 over same-doc chunks (excluding positive)
        neg_pool = [cid for cid in cand_ids if cid != pos_id]
        ranked_negs: list[str] = []
        if neg_pool:
            corpus = [tok(by_id[cid]["text"]) for cid in neg_pool]
            bm25 = BM25Okapi(corpus)
            scores = bm25.get_scores(tok(q["query"]))
            ranked_negs = [
                cid for _, cid in sorted(zip(scores, neg_pool), key=lambda x: -x[0])
            ][: args.neg]

        # top up with random cross-doc negatives if the doc is small
        if len(ranked_negs) < args.neg:
            others = [
                cid
                for cid in all_ids
                if cid != pos_id and cid not in ranked_negs and by_id[cid]["doc_id"] != doc_id
            ]
            RNG.shuffle(others)
            ranked_negs += others[: args.neg - len(ranked_negs)]

        train_rows.append(
            {
                "query": q["query"],
                "positive": by_id[pos_id]["text"],
                "negatives": [by_id[cid]["text"] for cid in ranked_negs],
            }
        )

    with TRAIN.open("w", encoding="utf-8") as f:
        for r in train_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with EVAL.open("w", encoding="utf-8") as f:
        for r in eval_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    avg_neg = sum(len(r["negatives"]) for r in train_rows) / max(1, len(train_rows))
    print(f"{len(qa)} QA pairs validated OK")
    print(f"train_indomain: {len(train_rows)} rows, avg {avg_neg:.1f} negatives -> {TRAIN}")
    print(f"eval_indomain:  {len(eval_rows)} rows -> {EVAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
