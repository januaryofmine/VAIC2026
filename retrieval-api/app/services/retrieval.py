"""Hybrid retrieval for Q&A — dense vector + Postgres full-text, fused with RRF.

Dense vector alone struggles inside one homogeneous document (all chunks score
~the same; keyword queries like "Quan điểm" get missed). Adding a lexical arm and
fusing with Reciprocal Rank Fusion surfaces literal-term matches. Always scoped to
one document_id; noise chunks (headings/page numbers) are filtered by length.
"""

import re

import psycopg
from psycopg.rows import dict_row

from app.services.embedding import embed_query

# Common Vietnamese function words — drop from the lexical query so it keys on content.
_STOPWORDS = {
    "của", "này", "là", "và", "các", "những", "một", "có", "cho", "được", "gì",
    "ở", "với", "để", "về", "theo", "trong", "khi", "như", "đã", "sẽ", "bị",
    "gồm", "nào", "ra", "đến", "hay", "thì", "mà", "cũng", "vào",
}
_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹ]+")

_VECTOR_SQL = """
    SELECT id::text, position, page, section, text,
           1 - (embedding <=> %(vector)s::vector) AS score
    FROM chunks
    WHERE document_id = %(doc)s::uuid AND length(btrim(text)) >= %(min_chars)s
    ORDER BY embedding <=> %(vector)s::vector
    LIMIT %(limit)s
"""

_KEYWORD_SQL = """
    SELECT id::text, position, page, section, text,
           ts_rank(to_tsvector('simple', text), to_tsquery('simple', %(tsq)s)) AS score
    FROM chunks
    WHERE document_id = %(doc)s::uuid AND length(btrim(text)) >= %(min_chars)s
          AND to_tsvector('simple', text) @@ to_tsquery('simple', %(tsq)s)
    ORDER BY score DESC
    LIMIT %(limit)s
"""

# Neighbour expansion: a matched chunk's section often spills into adjacent chunks
# (e.g. a "Quan điểm" list split across positions). Pull those neighbours for context.
_NEIGHBOR_SQL = """
    SELECT id::text, position, page, section, text
    FROM chunks
    WHERE document_id = %(doc)s::uuid AND length(btrim(text)) >= %(min_chars)s
          AND position = ANY(%(positions)s)
"""


def build_ts_query(question: str) -> str | None:
    """Turn a question into an OR-of-prefixes tsquery, e.g. 'quan:* | điểm:*'.

    Returns None if nothing usable is left (then the keyword arm is skipped).
    """
    seen: set[str] = set()
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(question):
        t = raw.lower()
        if len(t) >= 2 and t not in _STOPWORDS and t not in seen:
            seen.add(t)
            tokens.append(t)
    if not tokens:
        return None
    return " | ".join(f"{t}:*" for t in tokens)


def rrf_fuse(ranked_lists: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion: combine ranked id lists into a single score per id."""
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, doc_id in enumerate(lst):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


def _run(conn: psycopg.Connection, sql: str, params: dict) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def retrieve(
    conn: psycopg.Connection,
    question: str,
    document_id: str,
    top_k: int,
    *,
    over_fetch_multiplier: int = 6,
    rrf_k: int = 60,
    min_chunk_chars: int = 30,
    neighbor_radius: int = 1,
    expand_top: int = 5,
) -> list[dict]:
    pool = max(top_k * over_fetch_multiplier, top_k)

    vec_rows = _run(
        conn,
        _VECTOR_SQL,
        {
            "vector": embed_query(question),
            "doc": document_id,
            "min_chars": min_chunk_chars,
            "limit": pool,
        },
    )

    tsq = build_ts_query(question)
    kw_rows = (
        _run(
            conn,
            _KEYWORD_SQL,
            {"tsq": tsq, "doc": document_id, "min_chars": min_chunk_chars, "limit": pool},
        )
        if tsq
        else []
    )

    fused = rrf_fuse([[r["id"] for r in vec_rows], [r["id"] for r in kw_rows]], k=rrf_k)
    by_id = {r["id"]: r for r in (*kw_rows, *vec_rows)}  # vec wins ties (has cosine)

    ranked_ids = sorted(fused, key=lambda i: fused[i], reverse=True)[:top_k]
    results = []
    for doc_id in ranked_ids:
        row = dict(by_id[doc_id])
        row["score"] = round(fused[doc_id], 6)  # expose the fused RRF score
        results.append(row)

    if neighbor_radius > 0 and results:
        have = {r["position"] for r in results}
        wanted: set[int] = set()
        for r in results[:expand_top]:
            for d in range(-neighbor_radius, neighbor_radius + 1):
                p = r["position"] + d
                if p >= 0 and p not in have:
                    wanted.add(p)
        if wanted:
            extras = _run(
                conn,
                _NEIGHBOR_SQL,
                {"doc": document_id, "positions": list(wanted), "min_chars": min_chunk_chars},
            )
            for e in sorted(extras, key=lambda x: x["position"]):
                row = dict(e)
                row["score"] = 0.0  # context neighbour, not a ranked hit
                results.append(row)

    return results
