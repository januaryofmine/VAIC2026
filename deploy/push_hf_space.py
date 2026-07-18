"""Create the HF Space (Docker), upload retrieval-api + rag-pipeline, and set its
runtime env (DATABASE_URL secret + CORS/reranker variables).

Secrets (HF_TOKEN, HF_USER, DATABASE_URL) are read from a secrets file so nothing
sensitive is passed on the command line.

Usage:
    python deploy/push_hf_space.py --secrets <path> [--space vaic-retrieval]
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
    args = ap.parse_args()

    sec = read_secrets(Path(args.secrets))
    token = sec.get("HF_TOKEN")
    user = sec.get("HF_USER")
    db_url = sec.get("DATABASE_URL")
    if not token or not user:
        print("ERROR: HF_TOKEN / HF_USER missing in secrets file", file=sys.stderr)
        return 1

    from huggingface_hub import HfApi

    api = HfApi(token=token)
    repo_id = f"{user}/{args.space}"

    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    print(f"space ready: https://huggingface.co/spaces/{repo_id}")

    # Runtime env: DATABASE_URL as a secret; the rest as public variables.
    if db_url:
        api.add_space_secret(repo_id=repo_id, key="DATABASE_URL", value=db_url)
        print("set secret DATABASE_URL")
    api.add_space_variable(repo_id=repo_id, key="CORS_ORIGINS", value='["*"]')
    api.add_space_variable(repo_id=repo_id, key="RERANKER_ENABLED", value="false")
    print("set variables CORS_ORIGINS, RERANKER_ENABLED")

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
