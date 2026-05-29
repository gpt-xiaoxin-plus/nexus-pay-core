#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -x .venv/bin/opai ]; then
  ./setup.sh
fi

.venv/bin/opai flow offline \
  --dataset config/protocol_offline_dataset.json \
  --out config/offline_full_flow_result.json
