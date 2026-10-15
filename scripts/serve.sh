#!/usr/bin/env bash
# Serve site/ locally: scripts/serve.sh [port]   (build the API first: python -m ukpm build)
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m http.server "${1:-8080}" --directory site
