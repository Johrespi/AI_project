#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv no está instalado o no está en PATH."
  echo "Instálalo con: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

uv run python app.py
