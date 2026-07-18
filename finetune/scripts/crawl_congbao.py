"""Harvest direct PDF/DOC file URLs from congbao.dienbien.gov.vn (Lotus Domino).

The gov portal has a broken TLS chain, so we disable verification (public docs,
read-only). Category listing pages link to NoiDung pages; each NoiDung page has a
`/$file/<name>.pdf|doc` attachment. We collect those attachment URLs.

Output: appends unique file URLs to sources.txt.

Usage:
    uv run python scripts/crawl_congbao.py --max 25
"""

from __future__ import annotations

import argparse
import re
import urllib.parse
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources.txt"
BASE = "https://congbao.dienbien.gov.vn"
HEADERS = {"User-Agent": "Mozilla/5.0 VAIC2026-research/0.1"}

# Category listings (Nghị quyết + Quyết định), paginated via &Start=N.
CATEGORIES = [
    "/congbao/congbao.nsf/$DocsByCate?OpenForm=&view=DocumentsByType&RestrictToCategory=Ngh%E1%BB%8B+quy%E1%BA%BFt",
    "/congbao/congbao.nsf/$DocsByCate?OpenForm=&view=DocumentsByType&RestrictToCategory=Quy%E1%BA%BFt+%C4%91%E1%BB%8Bnh",
]
FILE_RE = re.compile(r"/\$file/", re.IGNORECASE)


def get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=60, verify=False)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def abs_url(href: str) -> str:
    return urllib.parse.urljoin(BASE, href)


def harvest_detail_links(listing_html: str) -> list[str]:
    soup = BeautifulSoup(listing_html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "NoiDung" in href or "ParentUNID" in href or FILE_RE.search(href):
            out.append(abs_url(href))
    return out


def file_url_from_detail(detail_url: str) -> str | None:
    if FILE_RE.search(detail_url):
        return detail_url
    try:
        html = get(detail_url)
    except Exception:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if FILE_RE.search(a["href"]):
            return abs_url(a["href"])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=25, help="max file URLs to collect")
    args = ap.parse_args()

    existing = set()
    if SOURCES.exists():
        existing = {
            ln.strip() for ln in SOURCES.read_text(encoding="utf-8").splitlines()
        }

    file_urls: list[str] = []
    seen = set()
    for cat in CATEGORIES:
        for start in (1, 31, 61):  # a few pages each
            if len(file_urls) >= args.max:
                break
            listing = f"{BASE}{cat}&Start={start}"
            try:
                html = get(listing)
            except Exception as e:
                print(f"listing fail {listing}: {e}")
                continue
            details = harvest_detail_links(html)
            print(f"{listing} -> {len(details)} detail links")
            for d in details:
                if len(file_urls) >= args.max:
                    break
                furl = file_url_from_detail(d)
                if furl and furl not in seen:
                    seen.add(furl)
                    file_urls.append(furl)
                    print(f"  file: {furl}")

    new = [u for u in file_urls if u not in existing]
    with SOURCES.open("a", encoding="utf-8") as f:
        for u in new:
            f.write(u + "\n")
    print(f"\nAdded {len(new)} new URLs to {SOURCES} (total collected {len(file_urls)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
