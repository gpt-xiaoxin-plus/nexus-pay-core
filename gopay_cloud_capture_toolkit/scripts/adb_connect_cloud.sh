#!/usr/bin/env bash
set -euo pipefail

SERIAL="${1:-${ADB_SERIAL:-}}"
if [ -z "$SERIAL" ]; then
  echo "用法: $0 <云手机ADB地址>"
  echo "例:  $0 127.0.0.1:7252"
  exit 2
fi

adb disconnect "$SERIAL" >/dev/null 2>&1 || true
adb connect "$SERIAL"
adb -s "$SERIAL" get-state
adb -s "$SERIAL" shell getprop ro.product.model || true
adb -s "$SERIAL" shell getprop ro.build.version.release || true

