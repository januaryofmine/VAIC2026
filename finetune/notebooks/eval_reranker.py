"""In-domain eval: Recall@k / MRR / nDCG for retrieval vs +reranker vs +fine-tuned.

Reproduces the production setup: retrieval is scoped to one document, so each
query's candidate pool is all chunks of its document (eval_indomain.jsonl). We
score three rankers on the SAME pools and report the lift:

  (0) e5 embedding cosine        -> the current system (retrieval only)
  (1) + bge-reranker-v2-m3 base  -> off-the-shelf cross-encoder
  (2) + our fine-tuned reranker  -> the PyTorch deliverable

Example (Kaggle):
    python eval_reranker.py \
        --chunks /kaggle/input/vaic-finetune/chunks.jsonl \
        --eval   /kaggle/input/vaic-finetune/eval_indomain.jsonl \
        --finetuned /kaggle/working/bge-reranker-dienbien
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch


def load_jsonl(p: str) -> list[dict]:
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


def metrics_from_ranks(ranks: list[int]) -> dict:
    """ranks = 1-based position of the (single) positive in each query's ranking."""
    n = len(ranks)
    out = {}
    for k in (1, 3, 5):
        out[f"Recall@{k}"] = sum(1 for r in ranks if r <= k) / n
    out["MRR"] = sum(1.0 / r for r in ranks) / n
    out["nDCG@5"] = sum((1.0 / math.log2(r + 1)) if r <= 5 else 0.0 for r in ranks) / n
    return out


def rank_positive(scores: list[float], cand_ids: list[str], positive_id: str) -> int:
    order = sorted(range(len(cand_ids)), key=lambda i: -scores[i])
    for pos, idx in enumerate(order, start=1):
        if cand_ids[idx] == positive_id:
            return pos
    return len(cand_ids) + 1


# ── rankers ───────────────────────────────────────────────────────
def _e5_embed(model, tok, device, texts, prefix, max_len=512, bs=16):
    """e5 embeddings via plain transformers (mean-pool + L2 norm) — avoids the
    sentence-transformers dependency, which can drag in a torch wheel that breaks
    Kaggle's CUDA build."""
    import torch
    import torch.nn.functional as F

    chunks = []
    for i in range(0, len(texts), bs):
        batch = [prefix + t for t in texts[i : i + bs]]
        enc = tok(batch, padding=True, truncation=True, max_length=max_len, return_tensors="pt").to(device)
        with torch.no_grad():
            hidden = model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1).float()
        emb = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        chunks.append(F.normalize(emb, dim=-1).cpu())
    return torch.cat(chunks)


def e5_scores(model, tok, device, query: str, texts: list[str]) -> list[float]:
    qv = _e5_embed(model, tok, device, [query], "query: ")[0]
    dv = _e5_embed(model, tok, device, texts, "passage: ")
    return (dv @ qv).tolist()


def ce_scores(model, tokenizer, device, query: str, texts: list[str], max_len: int) -> list[float]:
    scores = []
    bs = 16
    for i in range(0, len(texts), bs):
        batch = texts[i : i + bs]
        enc = tokenizer([query] * len(batch), batch, padding=True, truncation=True,
                        max_length=max_len, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits.squeeze(-1)
        scores.extend(logits.float().cpu().tolist())
    return scores


def eval_ranker(name, eval_rows, text_of, score_fn) -> dict:
    ranks = []
    for r in eval_rows:
        cand_ids = r["candidate_ids"]
        texts = [text_of[c] for c in cand_ids]
        scores = score_fn(r["query"], texts)
        ranks.append(rank_positive(scores, cand_ids, r["positive_id"]))
    m = metrics_from_ranks(ranks)
    print(f"\n== {name} ==")
    for k, v in m.items():
        print(f"  {k:10s} {v:.4f}")
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunks", default="chunks.jsonl")
    ap.add_argument("--eval", default="eval_indomain.jsonl")
    ap.add_argument("--base-model", default="BAAI/bge-reranker-v2-m3")
    ap.add_argument("--finetuned", default="bge-reranker-dienbien")
    ap.add_argument("--e5-model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--skip-e5", action="store_true")
    args = ap.parse_args()

    chunks = load_jsonl(args.chunks)
    text_of = {f'{c["doc_id"]}::{c["position"]}': c["text"] for c in chunks}
    eval_rows = load_jsonl(args.eval)
    print(f"eval queries: {len(eval_rows)} | avg pool: "
          f"{sum(len(r['candidate_ids']) for r in eval_rows)/len(eval_rows):.1f}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    results = {}

    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

    if not args.skip_e5:
        e5_tok = AutoTokenizer.from_pretrained(args.e5_model)
        e5 = AutoModel.from_pretrained(args.e5_model).to(device).eval()
        results["e5 retrieval only"] = eval_ranker(
            "e5 retrieval only (current system)", eval_rows, text_of,
            lambda q, ts: e5_scores(e5, e5_tok, device, q, ts))
        del e5
        torch.cuda.empty_cache() if device == "cuda" else None

    for name, path in [("+ bge-reranker base", args.base_model),
                       ("+ fine-tuned reranker", args.finetuned)]:
        if not Path(path).exists() and "/" not in path:
            print(f"skip {name}: {path} not found")
            continue
        tok = AutoTokenizer.from_pretrained(path)
        mdl = AutoModelForSequenceClassification.from_pretrained(path, num_labels=1).to(device).eval()
        results[name] = eval_ranker(
            name, eval_rows, text_of,
            lambda q, ts, m=mdl, t=tok: ce_scores(m, t, device, q, ts, args.max_len))
        del mdl
        torch.cuda.empty_cache() if device == "cuda" else None

    # summary table
    print("\n\n==================== SUMMARY ====================")
    cols = ["Recall@1", "Recall@3", "Recall@5", "MRR", "nDCG@5"]
    print(f'{"stage":28s} ' + " ".join(f"{c:>9s}" for c in cols))
    for name, m in results.items():
        print(f"{name:28s} " + " ".join(f"{m[c]:9.4f}" for c in cols))
    Path("eval_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print("\nwrote eval_results.json")


if __name__ == "__main__":
    main()
