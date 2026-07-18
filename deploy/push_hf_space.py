"""Create the HF Space (Docker), upload retrieval-api + rag-pipeline, and set its
runtime env (DATABASE_URL + API_KEY secrets, CORS variable).

Secrets (HF_TOKEN, HF_USER, DATABASE_URL, API_KEY) are read from a secrets file so
nothing sensitive is passed on the command line.

S1 fix vs the original PR: sets an API_KEY secret (gates every /api route except
healthz) and a *scoped* CORS_ORIGINS instead of "*".

Usage:
    uv run --with huggingface_hub python deploy/push_hf_space.py \
        --secrets deploy/.secrets [--space vaic-retrieval] \
        [--cors https://your-ui.vercel.app]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF_SPACE_DIR = ROOT / "deploy" / "hf-space"


def read_secrets(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def build_staging(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(HF_SPACE_DIR / "Dockerfile", dst / "Dockerfile")
    shutil.copy(HF_SPACE_DIR / "README.md", dst / "README.md")
    for pkg in ("retrieval-api", "rag-pipeline"):
        shutil.copytree(
            ROOT / pkg, dst / pkg,
            ignore=shutil.ignore_patterns(
                ".venv", "__pycache__", "*.pyc", ".pytest_cache", "uv.lock", "tests"
            ),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--space", default="vaic-retrieval")
    ap.add_argument(
        "--cors",
        default="",
        help="comma-separated allowed origins for CORS_ORIGINS (scoped, not '*'). "
        "The UI proxy calls server-to-server so this is defense-in-depth; the real "
        "gate is API_KEY.",
    )
    ap.add_argument(
        "--reranker-model",
        default="",
        help="Hub repo id of the fine-tuned reranker (run push_model_hf.py first), "
        "e.g. myuser/bge-reranker-dienbien. Empty = stage-2 rerank stays off.",
    )
    ap.add_argument(
        "--reranker-candidates",
        type=int,
        default=20,
        help="candidates the cross-encoder re-scores per query. Lower = faster on "
        "the Space's 2 vCPU (each pair is a full transformer pass).",
    )
    args = ap.parse_args()

    sec = read_secrets(Path(args.secrets))
    token = sec.get("HF_TOKEN")
    user = sec.get("HF_USER")
    db_url = sec.get("DATABASE_URL")
    api_key = sec.get("API_KEY")
    if not token or not user:
        print("ERROR: HF_TOKEN / HF_USER missing in secrets file", file=sys.stderr)
        return 1
    if not db_url:
        print("ERROR: DATABASE_URL missing in secrets file (run load_schema.py first)",
              file=sys.stderr)
        return 1

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    repo_id = f"{user}/{args.space}"

    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    print(f"space ready: https://huggingface.co/spaces/{repo_id}")

    # Runtime env: DATABASE_URL + API_KEY as secrets; CORS as a public variable.
    api.add_space_secret(repo_id=repo_id, key="DATABASE_URL", value=db_url)
    print("set secret DATABASE_URL")
    if api_key:
        api.add_space_secret(repo_id=repo_id, key="API_KEY", value=api_key)
        print("set secret API_KEY (all /api routes except /api/healthz now gated)")
    else:
        print("WARN: no API_KEY in secrets → API is PUBLIC. Add API_KEY to secure it.")

    # S1: scoped CORS. Default to localhost when no --cors given (update after B4
    # once the Vercel UI domain is known). '*' is intentionally avoided.
    origins = args.cors.strip() or "http://localhost:3000"
    cors_json = "[" + ",".join(f'"{o.strip()}"' for o in origins.split(",")) + "]"
    api.add_space_variable(repo_id=repo_id, key="CORS_ORIGINS", value=cors_json)
    print(f"set variable CORS_ORIGINS={cors_json}")

    # Stage-2 reranker. Set as *variables* (not secrets) on purpose: HF passes Space
    # variables to the Docker build as build args, which is what lets the Dockerfile's
    # `ARG RERANKER_MODEL` preload the checkpoint instead of paying a ~2.3GB download
    # on the first question.
    if args.reranker_model:
        api.add_space_variable(repo_id=repo_id, key="RERANKER_ENABLED", value="true")
        api.add_space_variable(repo_id=repo_id, key="RERANKER_MODEL", value=args.reranker_model)
        api.add_space_variable(
            repo_id=repo_id,
            key="RETRIEVAL_CANDIDATES",
            value=str(args.reranker_candidates),
        )
        print(f"set variables RERANKER_ENABLED=true RERANKER_MODEL={args.reranker_model} "
              f"RETRIEVAL_CANDIDATES={args.reranker_candidates}")
    else:
        print("WARN: no --reranker-model → stage-2 rerank OFF (retrieval falls back to "
              "embedding order; citation accuracy drops)")

    staging = Path(tempfile.mkdtemp()) / "space"
    try:
        build_staging(staging)
        api.upload_folder(
            repo_id=repo_id, repo_type="space", folder_path=str(staging),
            commit_message="deploy retrieval-api + rag-pipeline",
        )
    finally:
        shutil.rmtree(staging.parent, ignore_errors=True)

    print(f"pushed. build starts at https://{user}-{args.space}.hf.space")
    print(f"healthcheck (after build): https://{user}-{args.space}.hf.space/api/healthz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
