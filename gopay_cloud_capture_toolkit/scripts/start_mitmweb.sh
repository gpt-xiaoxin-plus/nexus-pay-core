#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROXY_PORT="${PROXY_PORT:-18080}"
MITMWEB_PORT="${MITMWEB_PORT:-18081}"
mkdir -p captures
TS="$(date '+%Y%m%d_%H%M%S')"
export GOPAY_CAPTURE_JSONL="$ROOT/captures/gopay_flows_web_$TS.jsonl"

echo "mitmweb 代理端口: $PROXY_PORT"
echo "mitmweb 页面: http://127.0.0.1:$MITMWEB_PORT"
echo "云手机安装证书: http://mitm.it"
echo "GoPay JSONL: $GOPAY_CAPTURE_JSONL"

exec mitmweb \
  --listen-host 0.0.0.0 \
  --listen-port "$PROXY_PORT" \
  --web-host 127.0.0.1 \
  --web-port "$MITMWEB_PORT" \
  --set block_global=false \
  -s "$ROOT/addons/gopay_capture_filter.py"
