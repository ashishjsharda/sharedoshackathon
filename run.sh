#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python -m pip install -q -r requirements.txt
python scripts/seed.py
echo "Starting TrustMesh on :8000"
exec python main.py
