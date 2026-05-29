#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -x .venv/bin/opai ]; then
  ./setup.sh
fi

echo "== Rebuild protocol vNext =="
./refresh_protocol_vnext.sh

echo
echo "== Protocol status =="
.venv/bin/opai protocol status --profile config/protocol_vnext.json

echo
echo "== Offline full-flow =="
./run_offline.sh

echo
echo "== Tests =="
.venv/bin/python -m pytest app/tests -q

echo
echo "READY: protocol package, offline flow, and tests passed."
