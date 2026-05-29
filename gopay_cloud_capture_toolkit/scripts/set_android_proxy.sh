#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/config.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/config.env"
fi

SERIAL="${1:-${ADB_SERIAL:-}}"
PROXY_PORT="${PROXY_PORT:-18080}"
HOST_IP="${HOST_IP:-}"

if [ -z "$SERIAL" ]; then
  echo "用法: HOST_IP=<电脑IP> $0 <云手机ADB地址>"
  echo "例:  HOST_IP=192.168.1.8 $0 127.0.0.1:7252"
  exit 2
fi

if [ -z "$HOST_IP" ]; then
  HOST_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
fi

if [ -z "$HOST_IP" ]; then
  echo "没检测到 HOST_IP，请手动指定：HOST_IP=你的电脑IP $0 $SERIAL"
  exit 2
fi

adb -s "$SERIAL" shell settings put global http_proxy "$HOST_IP:$PROXY_PORT"
echo "已设置云手机代理: $HOST_IP:$PROXY_PORT"
adb -s "$SERIAL" shell settings get global http_proxy

