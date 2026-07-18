#!/usr/bin/env bash
# Self-service deploy cho paperless-ui lên đúng domain theo branch.
#
#   ./deploy/deploy-ui.sh dev     -> https://paperless-ui-dev.vercel.app   (branch dev)
#   ./deploy/deploy-ui.sh main    -> https://paperless-ui.vercel.app       (production)
#
# Yêu cầu 1 lần: được mời vào Vercel team `paperlessvaic` + `vercel login`.
# Quy trình: git checkout <branch> && ./deploy/deploy-ui.sh <branch>
set -e

ENV="${1:-dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/paperless-ui"

if [ "$ENV" = "main" ] || [ "$ENV" = "prod" ]; then
  echo "Deploying MAIN (production) -> paperless-ui.vercel.app"
  vercel deploy --prod --yes
  echo "Done: https://paperless-ui.vercel.app"
else
  echo "Deploying DEV -> paperless-ui-dev.vercel.app"
  url=$(vercel deploy --yes 2>&1 | grep -oE 'https://[a-z0-9-]+\.vercel\.app' | head -1)
  [ -z "$url" ] && { echo "ERROR: could not parse deploy URL"; exit 1; }
  vercel alias set "$url" paperless-ui-dev.vercel.app
  echo "Done: https://paperless-ui-dev.vercel.app -> $url"
fi
