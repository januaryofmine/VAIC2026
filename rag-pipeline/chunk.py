"""Turn parsed blocks into token-sized, structure-aware chunks.

Why token-based: e5 truncates at 512 tokens, so char-sized chunks could silently
lose their tail at embed time. We pack paragraphs to a token budget (< limit),
overlap consecutive chunks, and never let a chunk cross a section (Điều) boundary.
Every chunk keeps page + section so retrieval can cite them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import groupby
from typing import Callable

from config import config as cfg
from parse import Block

TokenCounter = Callable[[str], int]

_SENT_RE = re.compile(r"(?<=[.;:!?])\s+|\n+")

_tokenizer = None


def _default_count_tokens(text: str) -> int:
    """Token count via the e5 tokenizer (loaded once; small, no full model)."""
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer

        _tokenizer = AutoTokenizer.from_pretrained(cfg.embedding_model)
    return len(_tokenizer.encode(text, add_special_tokens=False))


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None
    section: str | None
    position: int  # 0-based order within the document


def _atomize(text: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Break an oversized block into atoms (sentences, then char slices) <= max_tokens."""
    atoms: list[str] = []
    for sent in _SENT_RE.split(text):
        sent = sent.strip()
        if not sent:
            continue
        if count(sent) <= max_tokens:
            atoms.append(sent)
        else:  # single sentence too long → proportional char slices (last resort)
            approx = max(1, len(sent) * max_tokens // max(count(sent), 1))
            atoms.extend(sent[i : i + approx] for i in range(0, len(sent), approx))
    return atoms


def _pack(
    units: list[tuple[str, int | None]],
    max_tokens: int,
    overlap_tokens: int,
    count: TokenCounter,
) -> list[tuple[str, int | None]]:
    """Pack (sentence, page) units into chunks with trailing overlap.

    Every chunk stays <= max_tokens: the overlap seed only carries trailing units
    that fit within overlap_tokens AND leave room for the incoming unit.
    """
    out: list[tuple[str, int | None]] = []
    current: list[tuple[str, int | None]] = []
    cur_tokens = 0

    def emit() -> None:
        if current:
            out.append((" ".join(t for t, _ in current), current[0][1]))

    for text, page in units:
        tks = count(text)
        if current and cur_tokens + tks > max_tokens:
            emit()
            tail: list[tuple[str, int | None]] = []
            tail_tokens = 0
            for t, p in reversed(current):
                c = count(t)
                if tail_tokens + c > overlap_tokens or tail_tokens + c + tks > max_tokens:
                    break
                tail.insert(0, (t, p))
                tail_tokens += c
            current = list(tail)
            cur_tokens = tail_tokens
        current.append((text, page))
        cur_tokens += tks
    emit()
    return out


def chunk_blocks(
    blocks: list[Block] | tuple[Block, ...],
    *,
    max_tokens: int = cfg.chunk_max_tokens,
    overlap_tokens: int = cfg.chunk_overlap_tokens,
    min_chars: int = cfg.chunk_min_chars,
    count_tokens: TokenCounter | None = None,
) -> list[Chunk]:
    count = count_tokens or _default_count_tokens
    chunks: list[Chunk] = []
    pos = 0

    # Group consecutive blocks by section so a chunk never crosses a Điều boundary.
    for section, group in groupby(blocks, key=lambda b: b.section):
        # Break every block into sentence atoms (each <= max_tokens) so packing +
        # overlap are fine-grained and no chunk can exceed the token budget.
        units: list[tuple[str, int | None]] = []
        for b in group:
            units.extend((atom, b.page) for atom in _atomize(b.text, max_tokens, count))

        for text, page in _pack(units, max_tokens, overlap_tokens, count):
            if len(text.strip()) < min_chars:
                continue  # drop noise fragments
            chunks.append(Chunk(text=text, page=page, section=section, position=pos))
            pos += 1

    return chunks
