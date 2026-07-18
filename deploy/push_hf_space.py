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

    # Backend-driven prep-pack: after embedding, this Space calls {BFF_URL}/api/internal
    # /prep-pack so summary/terms/questions are generated + stored without a user opening
    # the doc. BFF_URL = the Vercel UI URL (public, not a secret). Omit → trigger off.
    bff_url = sec.get("BFF_URL")
    if bff_url:
        api.add_space_variable(repo_id=repo_id, key="BFF_URL", value=bff_url)
        print(f"set variable BFF_URL={bff_url}")
    else:
        print("WARN: no BFF_URL in secrets → prep-pack is generated only on doc open.")

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
