#!/usr/bin/env bash
# Self-service deploy cho paperless-ui lên đúng domain theo branch.
#
#   ./deploy/deploy-ui.sh dev     -> https://paperless-ui-dev.vercel.app   (branch dev)
#   ./deploy/deploy-ui.sh main    -> https://paperless-ui.vercel.app       (production)
#
# Auth (chọn 1):
#   - Có VERCEL_TOKEN trong .env  -> deploy bằng token, KHÔNG cần login (khuyến nghị cho team).
#   - Hoặc `vercel login` 1 lần (được mời vào team `paperlessvaic`).
# Quy trình: git checkout <branch> && ./deploy/deploy-ui.sh <branch>
set -e

ENV="${1:-dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Nạp VERCEL_TOKEN từ .env nếu có (dòng: VERCEL_TOKEN=...)
[ -z "$VERCEL_TOKEN" ] && [ -f "$ROOT/.env" ] && \
  VERCEL_TOKEN=$(grep -E '^VERCEL_TOKEN=' "$ROOT/.env" | head -1 | cut -d= -f2-)
TOKEN_ARG=""
[ -n "$VERCEL_TOKEN" ] && TOKEN_ARG="--token=$VERCEL_TOKEN"

cd "$ROOT/paperless-ui"

if [ "$ENV" = "main" ] || [ "$ENV" = "prod" ]; then
  echo "Deploying MAIN (production) -> paperless-ui.vercel.app"
  vercel deploy --prod --yes $TOKEN_ARG
  echo "Done: https://paperless-ui.vercel.app"
else
  echo "Deploying DEV -> paperless-ui-dev.vercel.app"
  url=$(vercel deploy --yes $TOKEN_ARG 2>&1 | grep -oE 'https://[a-z0-9-]+\.vercel\.app' | head -1)
  [ -z "$url" ] && { echo "ERROR: could not parse deploy URL"; exit 1; }
  vercel alias set "$url" paperless-ui-dev.vercel.app $TOKEN_ARG
  echo "Done: https://paperless-ui-dev.vercel.app -> $url"
fi
