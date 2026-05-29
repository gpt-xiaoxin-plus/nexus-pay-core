#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROXY_PORT="${PROXY_PORT:-18080}"
mkdir -p captures

TS="$(date '+%Y%m%d_%H%M%S')"
export GOPAY_CAPTURE_JSONL="$ROOT/captures/gopay_flows_$TS.jsonl"
FLOW_FILE="$ROOT/captures/full_$TS.mitm"

echo "mitmdump 代理端口: $PROXY_PORT"
echo "GoPay JSONL: $GOPAY_CAPTURE_JSONL"
echo "完整 mitm flow: $FLOW_FILE"
echo "云手机安装证书: http://mitm.it"

exec mitmdump \
  --listen-host 0.0.0.0 \
  --listen-port "$PROXY_PORT" \
  --set block_global=false \
  -w "$FLOW_FILE" \
  -s "$ROOT/addons/gopay_capture_filter.py"

