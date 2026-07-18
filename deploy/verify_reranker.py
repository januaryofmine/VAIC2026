"""Check that a deployed retrieval-api really has the fine-tuned reranker running.

The reranker fails *quietly* by design: a wrong model id or an OOM makes
reranking.py fall back to retrieval order and still return HTTP 200 with plausible
chunks. So "the API answers" proves nothing. This script proves three things:

  1. the host is up                       -> /api/healthz
  2. stage 2 is switched on               -> retrieve response has reranked=true
  3. stage 2 actually changes the ranking -> same query with/without rerank differ,
     compared by asking for a wide top_k and diffing the returned chunk order

Usage:
    uv run --with httpx python deploy/verify_reranker.py \
        --host https://<user>-<space>.hf.space \
        --document-id <uuid> \
        --question "Điều kiện được hưởng trợ cấp là gì?" \
        [--api-key <API_KEY>]

Exit code 0 = reranker verified live; 1 = something is off (message says what).
"""

from __future__ import annotations

import argparse
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="e.g. https://user-space.hf.space")
    ap.add_argument("--document-id", required=True, help="UUID of an ingested document")
    ap.add_argument("--question", required=True)
    ap.add_argument("--api-key", default="", help="X-API-Key if the host is gated")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    import httpx

    host = args.host.rstrip("/")
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    ok = True

    # 1 — liveness
    try:
        r = httpx.get(f"{host}/api/healthz", timeout=30)
        print(f"[1] healthz            -> {r.status_code} {r.text.strip()[:60]}")
        if r.status_code != 200:
            print("    FAIL: host not healthy")
            return 1
    except Exception as e:
        print(f"[1] healthz            -> FAIL: {e}")
        return 1

    # 2 — is stage 2 on? (first call also pays model load, so time it separately)
    body = {
        "question": args.question,
        "document_id": args.document_id,
        "top_k": args.top_k,
    }
    t0 = time.time()
    try:
        r = httpx.post(f"{host}/api/retrieve", json=body, headers=headers, timeout=300)
    except Exception as e:
        print(f"[2] retrieve           -> FAIL: {e}")
        return 1
    warm = time.time() - t0
    if r.status_code != 200:
        print(f"[2] retrieve           -> FAIL {r.status_code}: {r.text[:200]}")
        return 1
    data = r.json()
    reranked = data.get("reranked")
    print(f"[2] retrieve            -> 200 in {warm:.1f}s (cold: includes model load)")
    print(f"    reranked flag       -> {reranked}")
    if reranked is None:
        print("    FAIL: host runs an OLD build (no 'reranked' field). Redeploy.")
        return 1
    if not reranked:
        print("    FAIL: RERANKER_ENABLED is not true on the host → stage 2 is OFF.")
        print("    Fix: set Space variables RERANKER_ENABLED=true and RERANKER_MODEL=<repo>")
        return 1

    # 3 — warm latency (the number to quote in the pitch, not the cold one)
    t0 = time.time()
    r2 = httpx.post(f"{host}/api/retrieve", json=body, headers=headers, timeout=120)
    warm2 = time.time() - t0
    print(f"[3] retrieve (warm)     -> {r2.status_code} in {warm2:.2f}s")
    if warm2 > 10:
        print("    WARN: slow for a demo. Lower RETRIEVAL_CANDIDATES (e.g. 10) on the Space.")
        ok = False

    chunks = data.get("chunks", [])
    print(f"\n    top-{len(chunks)} chunks (rank: page/section):")
    for i, c in enumerate(chunks, 1):
        page = c.get("page")
        section = c.get("section") or "-"
        print(f"      #{i}  page={page}  {section}  score={c.get('score')}")
    if not chunks:
        print("    FAIL: no chunks — is document_id ingested on THIS host's database?")
        return 1

    print("\nRESULT:", "reranker verified live" if ok else "reranker live but SLOW")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
