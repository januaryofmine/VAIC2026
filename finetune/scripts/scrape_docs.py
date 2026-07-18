"""Download public Vietnamese legal documents listed in sources.txt.

Each line of sources.txt is a URL to a PDF (downloaded as-is) or an HTML legal
page (main text extracted to .txt). Saved under data/raw/. Idempotent: skips
files already present.

Usage:
    uv run python scripts/scrape_docs.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # gov TLS chains

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCES = ROOT / "sources.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VAIC2026-research/0.1"
}


def _slug(url: str) -> str:
    h = hashlib.sha1(url.encode()).hexdigest()[:8]
    tail = url.rstrip("/").split("/")[-1][:40].replace("?", "_")
    return f"{tail}_{h}"


def _save_pdf(url: str, dest: Path) -> None:
    r = requests.get(url, headers=HEADERS, timeout=60, verify=False)
    r.raise_for_status()
    dest.write_bytes(r.content)


def _save_html_text(url: str, dest: Path) -> None:
    r = requests.get(url, headers=HEADERS, timeout=60, verify=False)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # Legal portals usually wrap the body in a content div; fall back to <body>.
    main = (
        soup.select_one(".content1, .toanvancontent, #divContent, .fulltext")
        or soup.body
        or soup
    )
    text = "\n".join(
        line.strip() for line in main.get_text("\n").splitlines() if line.strip()
    )
    dest.write_text(text, encoding="utf-8")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    if not SOURCES.exists():
        print(f"Missing {SOURCES}. Add one URL per line.", file=sys.stderr)
        return 1

    urls = [
        ln.strip()
        for ln in SOURCES.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("#")
    ]
    print(f"{len(urls)} sources")

    ok = 0
    for url in urls:
        low = url.lower()
        # Binary doc formats -> download as-is; anything else -> extract HTML text.
        bin_ext = next((e for e in (".pdf", ".docx", ".doc") if low.endswith(e)), None)
        ext = bin_ext or ".txt"
        dest = RAW / (_slug(url) + ext)
        if dest.exists():
            print(f"skip  {dest.name}")
            ok += 1
            continue
        try:
            if bin_ext:
                _save_pdf(url, dest)  # generic binary GET (name is historical)
            else:
                _save_html_text(url, dest)
            print(f"saved {dest.name}  <- {url}")
            ok += 1
        except Exception as e:
            print(f"FAIL  {url}: {e}", file=sys.stderr)

    print(f"\n{ok}/{len(urls)} downloaded into {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
