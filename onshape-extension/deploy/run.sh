#!/usr/bin/env bash
# Start the Onshape Extension backend server.
# Usage: ./run.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXT_DIR="$SCRIPT_DIR/.."

cd "$EXT_DIR"

exec uvicorn backend.app:app \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8420}" \
  --reload
