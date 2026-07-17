"""Pure string splitting helpers (no metadata, no config). Adapted from aks-advisor."""

import re


def hard_split(text: str, max_chars: int) -> list[str]:
    """Split text with no paragraph breaks at line boundaries.

    A single line longer than max_chars becomes its own (oversized) chunk.
    """
    chunks: list[str] = []
    current = ""
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
    """Split text on blank lines so each piece stays <= max_chars where possible."""
    if len(text) <= max_chars:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current = ""
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
