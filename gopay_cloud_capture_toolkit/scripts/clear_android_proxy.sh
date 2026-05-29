#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f "$ROOT/config.env" ]; then
  # shellcheck disable=SC1091
  source "$ROOT/config.env"
fi

SERIAL="${1:-${ADB_SERIAL:-}}"
if [ -z "$SERIAL" ]; then
  echo "用法: $0 <云手机ADB地址>"
  echo "例:  $0 127.0.0.1:7252"
  exit 2
fi

adb -s "$SERIAL" shell settings put global http_proxy :0
adb -s "$SERIAL" shell settings delete global http_proxy >/dev/null 2>&1 || true
echo "已清理云手机代理"
adb -s "$SERIAL" shell settings get global http_proxy || true

