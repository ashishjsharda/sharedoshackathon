#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python scripts/seed.py
echo "Starting TrustMesh Arena services on :8000"
exec python arena_server.py
