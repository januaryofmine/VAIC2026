"""End-to-end check of the reranker serving path with the fine-tuned LoRA model.

Exercises the SAME code the API uses (app.services.reranking.rerank) on real
held-out Điện Biên questions, over each question's document chunks. Prints where
the correct chunk lands before vs after reranking.

Usage (from repo root, with a torch+sentence-transformers env):
    python retrieval-api/scripts/test_reranker_serving.py \
        --model finetune/models/bge-reranker-lora
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "retrieval-api"))
sys.stdout.reconfigure(encoding="utf-8")

from app.services.reranking import rerank  # noqa: E402

FT = REPO / "finetune" / "data"


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(REPO / "finetune" / "models" / "bge-reranker-lora"))
    ap.add_argument("--n", type=int, default=6, help="how many held-out queries to show")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    chunks = load_jsonl(FT / "chunks.jsonl")
    text_of = {f'{c["doc_id"]}::{c["position"]}': c for c in chunks}
    evals = load_jsonl(FT / "eval_indomain.jsonl")

    print(f"model: {args.model}")
    print(f"held-out queries: {len(evals)} (showing {args.n})\n")

    hits_before = hits_after = 0
    for e in evals:
        cand_ids = e["candidate_ids"]
        # "retrieval order" baseline = document order (no cosine here); the reranker
        # must pull the right chunk to the top regardless of input order.
        rows = [
            {"id": cid, "text": text_of[cid]["text"],
             "page": text_of[cid]["page"], "section": text_of[cid]["section"], "score": 0.0}
            for cid in cand_ids
        ]
        pos = e["positive_id"]
        before = [r["id"] for r in rows].index(pos) + 1
        reranked = rerank(e["query"], rows, top_k=len(rows), model_name=args.model)
        after = [r["id"] for r in reranked].index(pos) + 1
        hits_before += before <= args.top_k
        hits_after += after <= args.top_k

    print(f"\nRecall@{args.top_k}  (positive in top-{args.top_k}):")
    print(f"  before rerank (doc order): {hits_before}/{len(evals)}")
    print(f"  after  rerank (LoRA model): {hits_after}/{len(evals)}")

    # detailed view for the first N
    print("\n--- sample (rank of correct chunk after rerank) ---")
    for e in evals[: args.n]:
        cand_ids = e["candidate_ids"]
        rows = [
            {"id": cid, "text": text_of[cid]["text"],
             "page": text_of[cid]["page"], "section": text_of[cid]["section"], "score": 0.0}
            for cid in cand_ids
        ]
        reranked = rerank(e["query"], rows, top_k=len(rows), model_name=args.model)
        rank = [r["id"] for r in reranked].index(e["positive_id"]) + 1
        top = reranked[0]
        cite = f'trang {top["page"]} · {top["section"]}' if top["page"] else (top["section"] or "-")
        print(f'  Q: {e["query"][:70]}')
        print(f'     -> đúng chunk xếp #{rank}/{len(cand_ids)} | top-1 rerank: [{cite}]')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
