"""Harvest direct PDF links from congbao.sonla.gov.vn (Lotus Domino).

Unlike Điện Biên (where the attachment URL is assembled in JS), Sơn La renders the
`<UNID>/$file/<name>.pdf` reference straight into the detail page HTML — the only
catch is that filenames contain spaces, so the token must be matched up to the
extension rather than to whitespace.

Flow: ListAllDocuments view (paginated) -> detail pages -> $file/*.pdf -> sources file.

Usage:
    .venv/Scripts/python.exe scripts/harvest_sonla.py --max 30 --out sources_provinces.txt
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from pathlib import Path

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://congbao.sonla.gov.vn"
HEADERS = {"User-Agent": "Mozilla/5.0 VAIC2026-research/0.1"}

# <32-hex UNID>/$file/<name that may contain spaces>.pdf
FILE_RE = re.compile(
    r"([0-9A-Fa-f]{32}/\$file/[^\"'<>\\\r\n]*?\.(?:pdf|docx?))", re.IGNORECASE
)
DETAIL_RE = re.compile(r"/congbao\.nsf/str/([0-9A-Fa-f]{32})")


def get(url: str) -> str:
    r = requests.get(url, headers=HEADERS, verify=False, timeout=45)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def detail_links(listing_html: str) -> list[str]:
    """UNIDs of documents linked from a listing page."""
    out, seen = [], set()
    for m in DETAIL_RE.finditer(listing_html):
        unid = m.group(1)
        if unid not in seen:
            seen.add(unid)
            out.append(f"{BASE}/congbao.nsf/str/{unid}")
    # also plain anchors, in case the view renders them differently
    soup = BeautifulSoup(listing_html, "html.parser")
    for a in soup.find_all("a", href=True):
        if "/str/" in a["href"]:
            u = urllib.parse.urljoin(BASE + "/congbao.nsf/", a["href"])
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


def file_url(detail_html: str) -> str | None:
    m = FILE_RE.search(detail_html)
    if not m:
        return None
    return f"{BASE}/congbao.nsf/" + urllib.parse.quote(m.group(1), safe="/$")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=30)
    ap.add_argument("--out", default=str(ROOT / "sources_provinces.txt"))
    args = ap.parse_args()

    out_path = Path(args.out)
    existing = set()
    if out_path.exists():
        existing = {l.strip() for l in out_path.read_text(encoding="utf-8").splitlines()}

    # These views render the `<UNID>/$file/<name>.pdf` anchors directly in the list,
    # so we never need to open each detail page.
    found: list[str] = []
    for view in ("VanBanQPPL2", "VanBan"):
        for start in (1, 31, 61, 91, 121, 151):
            if len(found) >= args.max:
                break
            listing = f"{BASE}/congbao.nsf/{view}?OpenView&Start={start}"
            try:
                html = get(listing)
            except Exception as e:
                print(f"{view} Start={start} FAIL: {e}")
                continue
            hits = [m.group(1) for m in FILE_RE.finditer(html)]
            new_here = 0
            for h in dict.fromkeys(hits):
                if len(found) >= args.max:
                    break
                furl = f"{BASE}/congbao.nsf/" + urllib.parse.quote(h, safe="/$")
                if furl not in existing and furl not in found:
                    found.append(furl)
                    new_here += 1
            print(f"{view} Start={start}: {len(hits)} file-links, +{new_here} moi")

    with out_path.open("a", encoding="utf-8") as f:
        for u in found:
            f.write(u + "\n")
    print(f"\nAdded {len(found)} URLs -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
