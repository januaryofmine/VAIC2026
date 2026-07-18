"""Vercel Python entrypoint — exposes the FastAPI ASGI app.

The assembler (deploy/build_vercel_api.py) copies retrieval-api's `app/` package
and `rag-pipeline/` next to this file, and sets RAG_PIPELINE_DIR so ingestion can
import them. Vercel's @vercel/python serves the exported `app`.
"""

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
# rag-pipeline modules (imported lazily by the ingest endpoint)
os.environ.setdefault("RAG_PIPELINE_DIR", str(_HERE / "rag-pipeline"))
sys.path.insert(0, str(_HERE / "rag-pipeline"))

from app.main import app  # noqa: E402  (retrieval-api package copied alongside)
