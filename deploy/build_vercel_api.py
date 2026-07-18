"""Assemble a Vercel-deployable staging dir for the retrieval-api (Python).

Layout produced:
    <out>/index.py          # ASGI entrypoint (exposes app)
    <out>/vercel.json       # @vercel/python config
    <out>/requirements.txt  # torch-free deps
    <out>/app/              # retrieval-api package
    <out>/rag-pipeline/     # ingest modules (parse/chunk/embed/db)

Then deploy:
    cd <out> && vercel deploy --prod --yes   # (after `vercel login`)

Usage:
    python deploy/build_vercel_api.py --out deploy/.vercel-api-build
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deploy" / "vercel-api"

_IGNORE = shutil.ignore_patterns(
    ".venv", "__pycache__", "*.pyc", ".pytest_cache", "uv.lock", "tests", ".vercel"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "deploy" / ".vercel-api-build"))
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for f in ("index.py", "vercel.json", "requirements.txt"):
        shutil.copy(SRC / f, out / f)
    shutil.copytree(ROOT / "retrieval-api" / "app", out / "app", ignore=_IGNORE)
    shutil.copytree(ROOT / "rag-pipeline", out / "rag-pipeline", ignore=_IGNORE)

    print(f"assembled Vercel API build at {out}")
    print("next: cd", out, "&& vercel deploy --prod --yes")
    print("remember to set env: EMBEDDING_PROVIDER, <provider key>, DATABASE_URL, "
          "CORS_ORIGINS, ANTHROPIC_API_KEY (optional)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
