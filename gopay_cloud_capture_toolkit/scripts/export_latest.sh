#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

mkdir -p captures
LATEST_JSONL="$(ls -t captures/gopay_flows_*.jsonl 2>/dev/null | head -n 1 || true)"
LATEST_MITM="$(ls -t captures/full_*.mitm 2>/dev/null | head -n 1 || true)"

if [ -z "$LATEST_JSONL" ] && [ -z "$LATEST_MITM" ]; then
  echo "captures/ 里还没有抓包文件"
  exit 1
fi

TS="$(date '+%Y%m%d_%H%M%S')"
OUT="captures/gopay_capture_export_$TS.zip"
zip -j "$OUT" ${LATEST_JSONL:+"$LATEST_JSONL"} ${LATEST_MITM:+"$LATEST_MITM"} README.md >/dev/null
echo "$ROOT/$OUT"

