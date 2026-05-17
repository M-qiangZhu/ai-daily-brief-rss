#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PORT="${PORT:-19401}"

cd "$APP_DIR/docs"
exec python3 -m http.server "$PORT" --bind 0.0.0.0
