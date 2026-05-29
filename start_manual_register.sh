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

.venv/bin/opai worker manual-register "$@"
