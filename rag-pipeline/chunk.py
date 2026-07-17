"""Turn parsed blocks into chunks, preserving page + section on every chunk.

The whole point: metadata must NOT be dropped here — retrieval cites page/section.
"""

from __future__ import annotations

from dataclasses import dataclass

from config import config as cfg
from helpers.text_split import split_on_paragraphs
from parse import Block


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int | None
    section: str | None
    position: int  # 0-based order within the document


def chunk_blocks(
    blocks: list[Block] | tuple[Block, ...],
    max_chars: int = cfg.chunk_max_chars,
    min_chars: int = cfg.chunk_min_chars,
) -> list[Chunk]:
    """Split oversized blocks, then merge small adjacent blocks sharing (page, section)."""
    # 1. Split each block so no piece exceeds max_chars; each piece keeps its page/section.
    pieces: list[Block] = []
    for b in blocks:
        for part in split_on_paragraphs(b.text, max_chars):
            pieces.append(Block(text=part, page=b.page, section=b.section))

    # 2. Merge consecutive small pieces that share (page, section), staying <= max_chars.
    merged: list[Block] = []
    for piece in pieces:
        if merged:
            prev = merged[-1]
            same_scope = prev.page == piece.page and prev.section == piece.section
            candidate = prev.text + "\n\n" + piece.text
            if same_scope and len(prev.text) < min_chars and len(candidate) <= max_chars:
                merged[-1] = Block(text=candidate, page=prev.page, section=prev.section)
                continue
        merged.append(piece)

    # 3. Assign sequential positions.
    return [
        Chunk(text=b.text, page=b.page, section=b.section, position=i)
        for i, b in enumerate(merged)
    ]
