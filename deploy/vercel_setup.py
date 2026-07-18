"""One-off Vercel setup via API using the local CLI's stored auth token:
  1. Disable Vercel Authentication (SSO) on the project so preview (dev) URLs are public.
  2. Create a shareable Access Token for team deploys (`vercel deploy --token=...`).

Secrets are read from / written to files — never printed.

Usage:
    python deploy/vercel_setup.py --project paperless-ui --team paperlessvaic --secrets <path>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import requests

AUTH = Path.home() / "AppData/Roaming/xdg.data/com.vercel.cli/auth.json"
API = "https://api.vercel.com"


def read_oauth_token() -> str:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    tok = data.get("token") or data.get("accessToken")
    if not tok:
        # some versions nest it; scan values
        for v in data.values():
            if isinstance(v, str) and len(v) > 20:
                tok = v
                break
    if not tok:
        raise RuntimeError("no token in auth.json")
    return tok


def write_secret(secrets: Path, key: str, value: str) -> None:
    lines = []
    if secrets.exists():
        lines = [l for l in secrets.read_text(encoding="utf-8").splitlines()
                 if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    secrets.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="paperless-ui")
    ap.add_argument("--team", default="paperlessvaic")
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--make-token", action="store_true")
    args = ap.parse_args()

    tok = read_oauth_token()
    h = {"Authorization": f"Bearer {tok}"}

    # resolve teamId
    teams = requests.get(f"{API}/v2/teams", headers=h, timeout=30).json().get("teams", [])
    team = next((t for t in teams if t.get("slug") == args.team), None)
    if not team:
        print(f"ERROR: team {args.team} not found (teams: {[t.get('slug') for t in teams]})", file=sys.stderr)
        return 1
    team_id = team["id"]

    # 1. disable SSO protection so preview URLs are public
    r = requests.patch(
        f"{API}/v9/projects/{args.project}?teamId={team_id}",
        headers=h, json={"ssoProtection": None}, timeout=30,
    )
    if r.status_code < 300:
        print(f"OK: disabled Vercel Authentication on {args.project} (preview URLs now public)")
    else:
        print(f"WARN: patch ssoProtection -> {r.status_code}: {r.text[:200]}")

    # 2. optional shareable access token
    if args.make_token:
        rt = requests.post(
            f"{API}/v3/user/tokens", headers=h, json={"name": "vaic-team-deploy"}, timeout=30,
        )
        if rt.status_code < 300:
            bearer = rt.json().get("bearerToken")
            if bearer:
                write_secret(Path(args.secrets), "VERCEL_TOKEN", bearer)
                print("OK: created shareable Access Token -> saved as VERCEL_TOKEN in secrets file")
        else:
            print(f"WARN: create token -> {rt.status_code}: {rt.text[:200]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
