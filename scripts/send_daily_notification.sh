#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PUBLIC_URL="${PUBLIC_URL:-http://220.154.142.131:19401}"
LOCK_FILE="${NOTIFY_LOCK_FILE:-/tmp/ai-daily-brief-notify.lock}"
UV_BIN="${UV_BIN:-$HOME/.local/bin/uv}"

if [ ! -x "$UV_BIN" ]; then
  UV_BIN="$(command -v uv)"
fi

cd "$APP_DIR"

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

mkdir -p logs

flock -n "$LOCK_FILE" "$UV_BIN" run ai-daily-brief \
  --notify-only \
  --timezone Asia/Shanghai \
  --public-url "$PUBLIC_URL" \
  >> "logs/notification.log" 2>&1
