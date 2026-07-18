"""Blob storage for the original uploaded files (PDF/DOCX).

Filesystem-backed today (a Docker volume in prod, a local dir in dev). Everything
goes through BlobStorage so a later switch to S3/MinIO only touches this file —
see Slice 17 in local/TODO.md. Files are keyed by content hash, so an identical
re-upload maps to the same path (dedup) and is written at most once.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

_CHUNK = 1 << 20  # 1 MiB, so hashing a large PDF never loads it all into memory


def sha256_file(path: str | Path) -> str:
    """SHA-256 of a file's bytes (streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(_CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def default_data_dir() -> Path:
    """`$DATA_DIR` or `<repo>/data` (sibling of rag-pipeline/retrieval-api)."""
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "data"


class BlobStorage:
    """Store/read original files under `<root>/documents/<hash>.<ext>`."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else default_data_dir()
        self._docs = self.root / "documents"

    def path_for(self, content_hash: str, ext: str) -> Path:
        return self._docs / f"{content_hash}.{ext.lstrip('.').lower()}"

    def exists(self, content_hash: str, ext: str) -> bool:
        return self.path_for(content_hash, ext).exists()

    def save(self, content_hash: str, ext: str, src_path: str | Path) -> str:
        """Copy src into storage (idempotent) and return the absolute stored path."""
        dest = self.path_for(content_hash, ext)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():  # dedup: identical content already stored → skip copy
            shutil.copyfile(src_path, dest)
        return str(dest.resolve())
