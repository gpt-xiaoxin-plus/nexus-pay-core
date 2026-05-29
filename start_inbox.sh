#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ -f config/runtime.env ]; then
  set -a
  # shellcheck disable=SC1091
  . config/runtime.env
  set +a
fi

if [ ! -x .venv/bin/python ]; then
  ./setup.sh
fi

HOST="${OPAI_PAYMENT_INBOX_HOST:-127.0.0.1}"
PORT="${OPAI_PAYMENT_INBOX_PORT:-19080}"

PYTHONPATH=app/src .venv/bin/python app/src/opai/core/payment_inbox.py \
  --host "$HOST" \
  --port "$PORT" \
  --storage "${OPAI_PAYMENT_INBOX_PATH:-config/payment_inbox.json}"
