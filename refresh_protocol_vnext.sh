#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -x .venv/bin/opai ]; then
  ./setup.sh
fi

CAPTURE="${GOPAY_CAPTURE_XML:-/Users/username/Downloads/Telegram Lite/真机3}"
GOPAY_PLUS="${GOPAY_PLUS_AUTO_ROOT:-/tmp/Gopay_plus_automatic}"
CHATGPT_TOOLKIT="${CHATGPT_PLUS_TOOLKIT_ROOT:-/tmp/chatgpt-plus-automation-toolkit}"
AGREEMENT_PAYMENT="${GPT_AGREEMENT_PAYMENT_ROOT:-/Users/username/Documents/Codex/2026-05-22/warning-don-t-paste-code-into/Gpt-Agreement-Payment}"
ACCOUNT_AUTO="${GOPAY_ACCOUNT_AUTO_ROOT:-/tmp/liangshilin-gopay_account_auto}"

.venv/bin/opai capture bundle "$CAPTURE" \
  --current-root "$ROOT" \
  --reference-root "$GOPAY_PLUS" \
  --reference-root "$CHATGPT_TOOLKIT" \
  --reference-root "$AGREEMENT_PAYMENT" \
  --reference-root "$ACCOUNT_AUTO" \
  --out-json config/protocol_offline_dataset.json \
  --out-md config/protocol_offline_report.md \
  --out-inventory-json config/gopay_protocol_inventory.json \
  --out-inventory-md config/gopay_protocol_inventory.md

.venv/bin/opai protocol build \
  --dataset config/protocol_offline_dataset.json \
  --out-json config/protocol_vnext.json \
  --out-md config/protocol_vnext.md

.venv/bin/opai flow offline \
  --dataset config/protocol_offline_dataset.json \
  --out config/offline_full_flow_result.json
