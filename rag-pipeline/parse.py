"""Parse PDF/DOCX into text blocks that carry page + section metadata.

Citation (deliverable #4) depends on this: every block records which page it came
from (PDF) and which legal article it belongs to (section, e.g. "Điều 5").
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Legal article header at the start of a line, e.g. "Điều 5", "Điều 12.".
_SECTION_RE = re.compile(r"^\s*(Điều\s+\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Block:
    """A paragraph-sized unit of text plus where it came from."""

    text: str
    page: int | None      # 1-based page (PDF); None for DOCX (no fixed pages)
    section: str | None   # e.g. "Điều 5" for legal docs; None otherwise


@dataclass(frozen=True)
class ParsedDoc:
    blocks: tuple[Block, ...]
    page_count: int | None


def detect_section(text: str, current: str | None) -> str | None:
    """Return the article label if `text` starts a new 'Điều N', else keep `current`."""
    m = _SECTION_RE.match(text)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()  # "Điều   5" -> "Điều 5"
    return current


def pages_from_pdftotext(raw: str) -> list[str]:
    """pdftotext emits a form-feed (\\f) between pages."""
    return raw.split("\f")


def _blocks_from_pages(pages: list[str]) -> list[Block]:
    """Group lines into paragraphs, tracking the active section at the LINE level.

    Section headers ("Điều N") are often glued mid-block in -layout output, so we
    can't just match paragraph starts. A header line both updates the current
    section and begins a new paragraph, so its article's text is tagged correctly.
    """
    blocks: list[Block] = []
    current_section: str | None = None
    para_lines: list[str] = []
    para_section: str | None = None
    page_no = 0

    def flush() -> None:
        nonlocal para_lines
        text = "\n".join(para_lines).strip()
        if text:
            blocks.append(Block(text=text, page=page_no, section=para_section))
        para_lines = []

    for page_no, page_text in enumerate(pages, start=1):
        para_section = current_section
        for line in page_text.split("\n"):
            if not line.strip():  # blank line = paragraph boundary
                flush()
                para_section = current_section
                continue
            new_section = detect_section(line, current_section)
            if new_section != current_section and para_lines:
                flush()  # a header line starts its own paragraph
            current_section = new_section
            if not para_lines:
                para_section = current_section
            para_lines.append(line)
        flush()

    return blocks


def _pages_from_pdfplumber(path: Path) -> list[str]:
    """Pure-Python PDF text per page (no poppler) — used where pdftotext is absent
    (e.g. serverless cloud hosts). Layout is less precise than `pdftotext -layout`
    but section/page detection still works on the extracted text."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(str(path)) as pdf:
        for pg in pdf.pages:
            pages.append(pg.extract_text() or "")
    return pages


def parse_pdf(path: Path) -> ParsedDoc:
    import shutil

    if shutil.which("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        pages = pages_from_pdftotext(result.stdout)
        if pages and not pages[-1].strip():  # pdftotext leaves a trailing empty page
            pages = pages[:-1]
    else:
        pages = _pages_from_pdfplumber(path)  # fallback: no poppler on this host
    blocks = _blocks_from_pages(pages)
    return ParsedDoc(blocks=tuple(blocks), page_count=len(pages))


def parse_docx(path: Path) -> ParsedDoc:
    from docx import Document  # lazy import so pure-logic tests don't need python-docx

    document = Document(str(path))
    blocks: list[Block] = []
    current_section: str | None = None
    for para in document.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        current_section = detect_section(text, current_section)
        blocks.append(Block(text=text, page=None, section=current_section))
    return ParsedDoc(blocks=tuple(blocks), page_count=None)


def parse(path: str | Path) -> ParsedDoc:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(p)
    if suffix == ".docx":
        return parse_docx(p)
    raise ValueError(f"Unsupported file type: {suffix!r} (expected .pdf or .docx)")
