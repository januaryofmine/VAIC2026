"""Parse data/raw/*.{pdf,txt} into chunks.jsonl, preserving page + section.

Mirrors the production rag-pipeline chunker (parse.py + chunk.py + text_split.py)
so training data matches what serving will index. PDF text via pdfplumber (no
poppler). Section = legal article header "Điều N".

Output: data/chunks.jsonl  {doc_id, filename, position, page, section, text}

Usage:
    .venv/Scripts/python.exe scripts/build_chunks.py
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "data" / "raw"
DEFAULT_OUT = ROOT / "data" / "chunks.jsonl"

MAX_CHARS = 1500
MIN_CHARS = 200
_SECTION_RE = re.compile(r"^\s*(Đi[eề]u\s+\d+)", re.IGNORECASE)


@dataclass
class Block:
    text: str
    page: int | None
    section: str | None


# ── section detection (mirrors parse.detect_section) ──────────────
def detect_section(text: str, current: str | None) -> str | None:
    m = _SECTION_RE.match(text)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return current


# ── string splitting (mirrors helpers/text_split.py) ──────────────
def hard_split(text: str, max_chars: int) -> list[str]:
    chunks, current = [], ""
    for line in text.split("\n"):
        candidate = (current + "\n" + line) if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = line
    if current:
        chunks.append(current)
    return chunks


def split_on_paragraphs(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text] if text.strip() else []
    chunks, current = [], ""
    for para in re.split(r"\n{2,}", text):
        if not para.strip():
            continue
        if len(para) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(hard_split(para, max_chars))
            continue
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


# ── chunk_blocks (mirrors chunk.py) ───────────────────────────────
def chunk_blocks(blocks: list[Block]) -> list[Block]:
    pieces: list[Block] = []
    for b in blocks:
        for part in split_on_paragraphs(b.text, MAX_CHARS):
            pieces.append(Block(part, b.page, b.section))
    merged: list[Block] = []
    for piece in pieces:
        if merged:
            prev = merged[-1]
            same = prev.page == piece.page and prev.section == piece.section
            cand = prev.text + "\n\n" + piece.text
            if same and len(prev.text) < MIN_CHARS and len(cand) <= MAX_CHARS:
                merged[-1] = Block(cand, prev.page, prev.section)
                continue
        merged.append(piece)
    return merged


# ── page -> blocks (mirrors parse._blocks_from_pages) ─────────────
def blocks_from_pages(pages: list[str]) -> list[Block]:
    blocks: list[Block] = []
    current_section: str | None = None
    para_lines: list[str] = []
    para_section: str | None = None
    page_no = 0

    def flush():
        nonlocal para_lines
        text = "\n".join(para_lines).strip()
        if text:
            blocks.append(Block(text, page_no, para_section))
        para_lines = []

    for page_no, page_text in enumerate(pages, start=1):
        para_section = current_section
        for line in page_text.split("\n"):
            if not line.strip():
                flush()
                para_section = current_section
                continue
            new_section = detect_section(line, current_section)
            if new_section != current_section and para_lines:
                flush()
            current_section = new_section
            if not para_lines:
                para_section = current_section
            para_lines.append(line)
        flush()
    return blocks


def pages_from_pdf(path: Path) -> list[str]:
    import pdfplumber

    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for pg in pdf.pages:
            pages.append(pg.extract_text() or "")
    return pages


def text_from_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def slug(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-")[:50]


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=str(DEFAULT_RAW), help="dir of downloaded documents")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="chunks.jsonl to write")
    ap.add_argument("--province", default="", help="tag written onto every chunk")
    args = ap.parse_args()
    RAW, OUT = Path(args.raw), Path(args.out)

    if not RAW.exists():
        print(f"no {RAW}", file=sys.stderr)
        return 1
    # Dedupe case-insensitively (Windows: *.pdf and *.PDF match the same file).
    seen_paths: dict[str, Path] = {}
    for f in RAW.iterdir():
        if f.suffix.lower() in (".pdf", ".txt", ".docx"):
            seen_paths.setdefault(str(f).lower(), f)
    files = sorted(seen_paths.values(), key=lambda p: p.name.lower())
    print(f"{len(files)} raw files")

    rows = []
    skipped = []
    for f in files:
        doc_id = slug(f.stem)
        if f.suffix.lower() == ".pdf":
            pages = pages_from_pdf(f)
            n_pages = len(pages)
        elif f.suffix.lower() == ".docx":
            pages = [text_from_docx(f)]
            n_pages = None
        else:
            pages = [f.read_text(encoding="utf-8", errors="ignore")]
            n_pages = None
        total_chars = sum(len(p) for p in pages)
        if total_chars < 200:  # scanned/image PDF with no extractable text -> skip (needs OCR)
            skipped.append(f.name)
            print(f"  SKIP {f.name}: pages={n_pages} chars={total_chars} (no text - scanned?)")
            continue
        blocks = blocks_from_pages(pages)
        chunks = chunk_blocks(blocks)
        n_dieu = len({c.section for c in chunks if c.section})
        print(f"  {f.name}: pages={n_pages} chars={total_chars} chunks={len(chunks)} articles={n_dieu}")
        for i, c in enumerate(chunks):
            row = {
                "doc_id": doc_id,
                "filename": f.name,
                "position": i,
                "page": c.page,
                "section": c.section,
                "text": c.text,
            }
            if args.province:  # tag the source so train/test can be split by province
                row["province"] = args.province
            rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(rows)} chunks -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
