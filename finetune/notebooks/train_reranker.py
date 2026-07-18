"""Fine-tune a Vietnamese legal cross-encoder reranker — native PyTorch training loop.

This is the PyTorch centerpiece of the project. We fine-tune
`BAAI/bge-reranker-v2-m3` (a multilingual cross-encoder, num_labels=1) on:
  1. Zalo Vietnamese legal retrieval (real query→relevant-passage labels, BEIR format)
  2. our in-domain Điện Biên triples (train_indomain.jsonl)

with BM25-mined hard negatives. Training is a hand-written loop (DataLoader +
AdamW + linear warmup + AMP autocast/GradScaler + grad clipping) — no high-level
Trainer — so the PyTorch engineering is explicit and inspectable.

Runs on a free Kaggle/Colab T4/P100. Example:
    python train_reranker.py --epochs 2 --batch-size 16 \
        --indomain /kaggle/input/vaic-finetune/train_indomain.jsonl \
        --out /kaggle/working/bge-reranker-dienbien
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import time
from pathlib import Path

# Reduce fragmentation OOM on 16GB GPUs (must be set before torch inits CUDA).
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# ── reproducibility (no wall-clock / RNG surprises) ───────────────
SEED = 42
random.seed(SEED)
torch.manual_seed(SEED)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def tok_bm25(s: str) -> list[str]:
    return re.findall(r"\w+", s.lower(), flags=re.UNICODE)


def first_key(row: dict, *cands: str) -> str:
    """Pick the first present column name (datasets schemas vary)."""
    for c in cands:
        if c in row:
            return c
    raise KeyError(f"none of {cands} in row keys {list(row)}")


# ── data building ─────────────────────────────────────────────────
def build_zalo_triples(neg_per_pos: int, max_queries: int | None) -> list[dict]:
    """Load Zalo legal retrieval (BEIR-style corpus/queries/qrels) and build
    {query, positive, negatives[]} with BM25 hard negatives from the corpus."""
    from datasets import load_dataset
    from rank_bm25 import BM25Okapi

    repo = "GreenNode/zalo-ai-legal-text-retrieval-vn"
    log("loading Zalo corpus/queries/qrels ...")

    def _first_split(ds):  # each config exposes one split (named 'test' here, not the config name)
        return ds[list(ds.keys())[0]]

    corpus = _first_split(load_dataset(repo, "corpus"))
    queries = _first_split(load_dataset(repo, "queries"))
    qrels = _first_split(load_dataset(repo, "qrels"))

    c0 = corpus[0]
    cid_key = first_key(c0, "_id", "id", "corpus-id", "doc_id")
    ctext_key = first_key(c0, "text", "content", "passage")
    q0 = queries[0]
    qid_key = first_key(q0, "_id", "id", "query-id")
    qtext_key = first_key(q0, "text", "query", "content")
    r0 = qrels[0]
    rq_key = first_key(r0, "query-id", "query_id", "qid")
    rc_key = first_key(r0, "corpus-id", "corpus_id", "cid", "doc_id")

    corpus_text = {str(r[cid_key]): r[ctext_key] for r in corpus}
    query_text = {str(r[qid_key]): r[qtext_key] for r in queries}
    log(f"corpus={len(corpus_text)} queries={len(query_text)} qrels={len(qrels)}")

    # query_id -> [positive corpus_ids]
    pos_map: dict[str, list[str]] = {}
    for r in qrels:
        score = r.get("score", 1)
        if score and int(score) > 0:
            pos_map.setdefault(str(r[rq_key]), []).append(str(r[rc_key]))

    # BM25 index over the whole corpus for hard-negative mining
    log("building BM25 index over corpus (one-off, ~1 min) ...")
    corpus_ids = list(corpus_text.keys())
    bm25 = BM25Okapi([tok_bm25(corpus_text[cid]) for cid in corpus_ids])

    triples = []
    qids = list(pos_map.keys())
    if max_queries:
        qids = qids[:max_queries]
    for i, qid in enumerate(qids):
        if qid not in query_text:
            continue
        q = query_text[qid]
        positives = set(pos_map[qid])
        scores = bm25.get_scores(tok_bm25(q))
        order = sorted(range(len(corpus_ids)), key=lambda j: -scores[j])
        negs = []
        for j in order:
            cid = corpus_ids[j]
            if cid in positives:
                continue
            negs.append(corpus_text[cid])
            if len(negs) >= neg_per_pos:
                break
        for pid in positives:
            if pid in corpus_text:
                triples.append({"query": q, "positive": corpus_text[pid], "negatives": negs})
        if (i + 1) % 100 == 0:
            log(f"  mined {i + 1}/{len(qids)} queries")
    log(f"Zalo triples: {len(triples)}")
    return triples


def load_indomain(path: str | None) -> list[dict]:
    if not path or not Path(path).exists():
        log(f"in-domain triples not found at {path}; skipping")
        return []
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    log(f"in-domain triples: {len(rows)}")
    return rows


# ── dataset ───────────────────────────────────────────────────────
class PairDataset(Dataset):
    """Flatten triples into (query, passage, label) — 1 for positive, 0 for negatives."""

    def __init__(self, triples: list[dict]):
        self.samples: list[tuple[str, str, float]] = []
        for t in triples:
            self.samples.append((t["query"], t["positive"], 1.0))
            for n in t["negatives"]:
                self.samples.append((t["query"], n, 0.0))
        random.shuffle(self.samples)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        return self.samples[i]


class Collator:
    """Top-level (picklable) collate — required for DataLoader workers on Windows spawn."""

    def __init__(self, tokenizer, max_len: int):
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __call__(self, batch):
        queries, passages, labels = zip(*batch)
        enc = self.tokenizer(
            list(queries), list(passages),
            padding=True, truncation=True, max_length=self.max_len, return_tensors="pt",
        )
        return enc, torch.tensor(labels, dtype=torch.float)


# ── training loop (hand-written) ─────────────────────────────────
def train(args) -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"device={device}  base={args.base_model}")

    triples = []
    if not args.skip_zalo:
        triples += build_zalo_triples(args.neg_per_pos, args.max_queries)
    triples += load_indomain(args.indomain)
    if not triples:
        raise SystemExit("No training triples. Provide --indomain or enable Zalo.")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(args.base_model, num_labels=1).to(device)
    # Gradient checkpointing trades compute for memory — lets a 568M cross-encoder
    # fine-tune on a 16GB GPU (P100). use_cache must be off for checkpointing.
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    ds = PairDataset(triples)
    loader = DataLoader(
        ds, batch_size=args.batch_size, shuffle=True,
        collate_fn=Collator(tokenizer, args.max_len), num_workers=args.num_workers, drop_last=True,
    )
    accum = max(1, args.grad_accum)
    steps_per_epoch = len(loader) // accum
    total_steps = steps_per_epoch * args.epochs
    warmup = int(0.1 * total_steps)
    log(f"training samples={len(ds)}  batches/epoch={len(loader)}  "
        f"optim-steps/epoch={steps_per_epoch}  (batch={args.batch_size} x accum={accum})")

    loss_fn = nn.BCEWithLogitsLoss()
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)

    def lr_lambda(step):  # linear warmup then linear decay
        if step < warmup:
            return step / max(1, warmup)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup))

    sched = torch.optim.lr_scheduler.LambdaLR(optim, lr_lambda)
    scaler = torch.amp.GradScaler("cuda", enabled=(device == "cuda"))

    model.train()
    step = 0
    for epoch in range(args.epochs):
        running = 0.0
        optim.zero_grad(set_to_none=True)
        for bidx, (enc, labels) in enumerate(loader):
            enc = {k: v.to(device) for k, v in enc.items()}
            labels = labels.to(device)
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=(device == "cuda")):
                logits = model(**enc).logits.squeeze(-1)
                loss = loss_fn(logits, labels) / accum
            scaler.scale(loss).backward()
            running += loss.item() * accum
            if (bidx + 1) % accum == 0:  # apply an optimizer step every `accum` batches
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optim)
                scaler.update()
                sched.step()
                optim.zero_grad(set_to_none=True)
                step += 1
                if step % args.log_every == 0:
                    log(f"epoch {epoch} step {step}/{total_steps} loss {running/(args.log_every*accum):.4f} lr {sched.get_last_lr()[0]:.2e}")
                    running = 0.0

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)
    log(f"saved fine-tuned reranker -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", default="BAAI/bge-reranker-v2-m3")
    ap.add_argument("--indomain", default="train_indomain.jsonl")
    ap.add_argument("--out", default="bge-reranker-dienbien")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--grad-accum", type=int, default=2, help="optimizer step every N batches")
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--neg-per-pos", type=int, default=7)
    ap.add_argument("--max-queries", type=int, default=None, help="cap Zalo queries (debug)")
    ap.add_argument("--skip-zalo", action="store_true", help="in-domain only")
    ap.add_argument("--num-workers", type=int, default=2, help="DataLoader workers (0 on Windows)")
    ap.add_argument("--log-every", type=int, default=20)
    train(ap.parse_args())


if __name__ == "__main__":
    main()
