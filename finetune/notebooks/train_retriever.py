"""Fine-tune the e5 bi-encoder (stage-1 retrieval) with contrastive LoRA.

Why this and not more reranker training: on the 33-question test the reranker
already recovers everything stage 1 hands it, but stage 1 itself only reaches
Recall@1 0.6970 and drops one positive out of the top-5 entirely. A reranker can
only reorder what retrieval surfaces, so that miss is unfixable downstream. The
ceiling moved to e5 — so train e5.

Loss: InfoNCE over [own positive] + [own BM25 hard negatives] + [every other
query's positive and negatives in the batch]. Hard negatives matter here because
in-batch negatives alone are near-trivial: two chunks from different documents
are easy to tell apart, while the confusable ones live inside the same document.

Mirrors train_reranker.py's mechanics (native loop, AdamW, linear warmup, AMP,
gradient checkpointing, LoRA, merge_and_unload) so the two are comparable.

Example (Kaggle):
    python train_retriever.py \
        --train /kaggle/input/vaic-finetune/data/train_dienbien_v2.jsonl \
        --out /kaggle/working/e5-dienbien \
        --epochs 8 --batch-size 4 --max-len 320
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_jsonl(p: str) -> list[dict]:
    return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]


class TripleSet(Dataset):
    """One row = one query + its positive + its hard negatives."""

    def __init__(self, rows: list[dict], n_neg: int):
        self.rows, self.n_neg = rows, n_neg

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int):
        r = self.rows[i]
        negs = list(r.get("negatives", []))[: self.n_neg]
        # keep the doc count identical across rows so the batch tensor is regular;
        # short rows repeat their last negative rather than pad with empties.
        while len(negs) < self.n_neg:
            negs.append(negs[-1] if negs else r["positive"])
        return r["query"], r["positive"], negs


class Collator:
    """Top-level (not a closure) so DataLoader workers pickle it on Windows spawn."""

    def __init__(self, tok, max_len: int):
        self.tok, self.max_len = tok, max_len

    def __call__(self, batch):
        queries = [f"query: {q}" for q, _, _ in batch]
        docs: list[str] = []
        for _, pos, negs in batch:
            docs.append(f"passage: {pos}")
            docs.extend(f"passage: {n}" for n in negs)
        enc_q = self.tok(queries, padding=True, truncation=True,
                         max_length=self.max_len, return_tensors="pt")
        enc_d = self.tok(docs, padding=True, truncation=True,
                         max_length=self.max_len, return_tensors="pt")
        return enc_q, enc_d


def mean_pool(hidden: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    m = mask.unsqueeze(-1).float()
    return (hidden * m).sum(1) / m.sum(1).clamp(min=1e-9)


def encode(model, enc, device) -> torch.Tensor:
    enc = {k: v.to(device) for k, v in enc.items()}
    out = model(**enc).last_hidden_state
    return F.normalize(mean_pool(out, enc["attention_mask"]), dim=-1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--out", default="e5-dienbien")
    ap.add_argument("--base-model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--grad-accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--max-len", type=int, default=320)
    ap.add_argument("--n-neg", type=int, default=4)
    ap.add_argument("--scale", type=float, default=20.0, help="temperature^-1 for cosine logits")
    ap.add_argument("--warmup-frac", type=float, default=0.1)
    ap.add_argument("--num-workers", type=int, default=0)
    ap.add_argument("--use-lora", action="store_true")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    args = ap.parse_args()

    from transformers import AutoModel, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    rows = load_jsonl(args.train)
    log(f"train rows: {len(rows)} | negatives/row used: {args.n_neg}")

    tok = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModel.from_pretrained(args.base_model)
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    if args.use_lora:
        from peft import LoraConfig, TaskType, get_peft_model

        lconf = LoraConfig(task_type=TaskType.FEATURE_EXTRACTION, r=args.lora_r,
                           lora_alpha=args.lora_alpha, lora_dropout=0.05,
                           target_modules=["query", "key", "value"])
        model = get_peft_model(model, lconf)
        model.enable_input_require_grads()
        model.print_trainable_parameters()

    model = model.to(device)

    ds = TripleSet(rows, args.n_neg)
    dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True,
                    collate_fn=Collator(tok, args.max_len), num_workers=args.num_workers,
                    drop_last=len(ds) > args.batch_size)

    accum = args.grad_accum
    steps_per_epoch = max(1, len(dl) // accum)
    total_steps = steps_per_epoch * args.epochs
    warmup = max(1, int(total_steps * args.warmup_frac))
    log(f"batches/epoch={len(dl)} optim-steps/epoch={steps_per_epoch} "
        f"total-steps={total_steps} warmup={warmup} (batch={args.batch_size} x accum={accum})")

    optim = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                              lr=args.lr, weight_decay=0.01)
    sched = torch.optim.lr_scheduler.LambdaLR(
        optim, lambda s: s / warmup if s < warmup
        else max(0.0, (total_steps - s) / max(1, total_steps - warmup)))
    scaler = torch.amp.GradScaler("cuda", enabled=(device == "cuda"))

    n_doc = 1 + args.n_neg
    model.train()
    for ep in range(1, args.epochs + 1):
        run, seen = 0.0, 0
        for bidx, (enc_q, enc_d) in enumerate(dl):
            with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=(device == "cuda")):
                qv = encode(model, enc_q, device)          # B x d
                dv = encode(model, enc_d, device)          # (B*n_doc) x d
                logits = qv @ dv.T * args.scale            # B x (B*n_doc)
                # each query's positive sits at its own block start; every other
                # column — including other rows' hard negatives — is a negative.
                target = torch.arange(qv.size(0), device=device) * n_doc
                loss = F.cross_entropy(logits, target) / accum

            scaler.scale(loss).backward()
            run += loss.item() * accum
            seen += 1

            if (bidx + 1) % accum == 0:
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
                scaler.step(optim)
                scaler.update()
                sched.step()
                optim.zero_grad(set_to_none=True)

        log(f"epoch {ep}/{args.epochs} loss={run / max(1, seen):.4f} lr={sched.get_last_lr()[0]:.2e}")

    if args.use_lora:
        model = model.merge_and_unload()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    log(f"saved -> {out}")


if __name__ == "__main__":
    main()
