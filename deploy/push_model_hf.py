"""Upload the fine-tuned reranker to the HF Hub so the Space can load it by name.

The model is a full merged checkpoint (~2.3 GB), so we do NOT bake it into the
Docker image — that would make every build push gigabytes. Instead it lives in a
Hub model repo and `RERANKER_MODEL=<user>/<repo>` is enough: sentence-transformers'
CrossEncoder accepts a Hub repo id exactly like a local path.

Usage:
    uv run --with huggingface_hub python deploy/push_model_hf.py \
        --secrets deploy/.secrets \
        [--model-dir finetune/models/bge-reranker-lora] \
        [--repo bge-reranker-dienbien] [--private]

Prints the RERANKER_MODEL value to set on the Space when it finishes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "finetune" / "models" / "bge-reranker-lora"

# A CrossEncoder checkpoint needs these to load; anything else (optimizer state,
# training logs) is dead weight in a serving repo.
REQUIRED = ("config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json")


def read_secrets(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


CARD = """---
license: apache-2.0
base_model: BAAI/bge-reranker-v2-m3
pipeline_tag: text-ranking
language: [vi]
tags: [reranker, cross-encoder, vietnamese, legal, paperless-meetings]
---

# bge-reranker-dienbien

Cross-encoder reranker fine-tuned (LoRA, merged) from `BAAI/bge-reranker-v2-m3`
on Vietnamese legal/administrative documents (Điện Biên province public
resolutions and decisions) for the VAIC2026 *Paperless Meetings* project.

It is stage 2 of a two-stage retrieval pipeline: `multilingual-e5-large` fetches
candidates by embedding cosine, then this model re-scores each (question, passage)
pair so the passage that actually answers the question ranks first — which is what
makes page/article citations correct.

## Held-out results (18 clean questions, none seen in training)

| Setup | Recall@1 | MRR | nDCG@5 |
|---|---|---|---|
| e5 retrieval only | 0.722 | 0.819 | 0.865 |
| + bge-reranker-v2-m3 (base) | 0.833 | 0.898 | 0.924 |
| **+ this fine-tune** | **0.889** | **0.944** | **0.959** |

## Usage

```python
from sentence_transformers import CrossEncoder

model = CrossEncoder("REPO_ID")
scores = model.predict([("Điều kiện hưởng trợ cấp là gì?", "Điều 5. ...")])
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secrets", required=True, help="file with HF_TOKEN / HF_USER")
    ap.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR))
    ap.add_argument("--repo", default="bge-reranker-dienbien")
    ap.add_argument(
        "--private",
        action="store_true",
        help="private repo — then the Space needs an HF_TOKEN secret to pull it",
    )
    args = ap.parse_args()

    sec = read_secrets(Path(args.secrets))
    token, user = sec.get("HF_TOKEN"), sec.get("HF_USER")
    if not token or not user:
        print("ERROR: HF_TOKEN / HF_USER missing in secrets file", file=sys.stderr)
        return 1

    model_dir = Path(args.model_dir)
    if not model_dir.is_dir():
        print(f"ERROR: model dir not found: {model_dir}", file=sys.stderr)
        return 1
    missing = [f for f in REQUIRED if not (model_dir / f).exists()]
    if missing:
        print(f"ERROR: {model_dir} is missing {missing}", file=sys.stderr)
        return 1

    size_gb = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file()) / 1e9
    repo_id = f"{user}/{args.repo}"
    print(f"uploading {model_dir} ({size_gb:.2f} GB) -> {repo_id}")

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id=repo_id, repo_type="model", private=args.private, exist_ok=True)

    # Write the card first so the repo is self-describing even mid-upload.
    (model_dir / "README.md").write_text(CARD.replace("REPO_ID", repo_id), encoding="utf-8")

    api.upload_folder(
        repo_id=repo_id,
        repo_type="model",
        folder_path=str(model_dir),
        commit_message="fine-tuned Vietnamese legal reranker (merged LoRA)",
    )

    print(f"\ndone: https://huggingface.co/{repo_id}")
    print("\nSet on the Space (push_hf_space.py does this for you):")
    print("  RERANKER_ENABLED=true")
    print(f"  RERANKER_MODEL={repo_id}")
    if args.private:
        print("  HF_TOKEN=<read token>   # required: repo is private")
    return 0


if __name__ == "__main__":
    sys.exit(main())
