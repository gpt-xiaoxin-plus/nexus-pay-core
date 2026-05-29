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

if [ ! -x .venv/bin/opai ]; then
  ./setup.sh
fi

if [ -z "${OPAI_HEROSMS_API_KEY:-}" ] && [ -z "${OPAI_HEROSMS_API_KEY_FILE:-}" ]; then
  echo "Missing Hero-SMS API key. Set OPAI_HEROSMS_API_KEY or OPAI_HEROSMS_API_KEY_FILE in config/runtime.env." >&2
  exit 1
fi

.venv/bin/opai worker run "$@"
