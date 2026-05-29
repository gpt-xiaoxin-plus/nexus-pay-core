#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[1/5] 工具检查"
for bin in adb mitmproxy mitmweb mitmdump python3; do
  if command -v "$bin" >/dev/null 2>&1; then
    echo "  OK  $bin -> $(command -v "$bin")"
  else
    echo "  MISS $bin"
  fi
done

echo
echo "[2/5] 本机 IP 候选"
for iface in en0 en1; do
  ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
  if [ -n "$ip" ]; then
    echo "  $iface: $ip"
  fi
done

echo
echo "[3/5] ADB 设备"
adb devices -l || true

echo
echo "[4/5] mitmproxy 证书目录"
echo "  $HOME/.mitmproxy"
ls -la "$HOME/.mitmproxy" 2>/dev/null || echo "  还没生成，启动 mitmproxy 后会自动生成。"

echo
echo "[5/5] 当前目录"
echo "  $ROOT"

