#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DEPLOY_USER="${DEPLOY_USER:-devz}"
DEPLOY_HOST="${DEPLOY_HOST:-220.154.142.131}"
DEPLOY_DIR="${DEPLOY_DIR:-/home/devz/ai-daily-brief-rss}"
DRY_RUN="${DRY_RUN:-}"

RSYNC_FLAGS=(
  -az
  --delete
  --exclude .git/
  --exclude .env
  --exclude '.env.backup-*'
  --exclude .venv/
  --exclude logs/
  --exclude __pycache__/
  --exclude .pytest_cache/
  --exclude .ruff_cache/
  --exclude .DS_Store
  --exclude tmp/
  --exclude data/state/
)

if [ -n "$DRY_RUN" ]; then
  RSYNC_FLAGS+=(--dry-run --itemize-changes)
fi

rsync "${RSYNC_FLAGS[@]}" "$APP_DIR/" "$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_DIR/"
