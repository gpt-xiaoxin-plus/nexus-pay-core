#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_python() {
  for candidate in \
    python3.13 \
    python3.12 \
    python3.11 \
    /Users/username/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3
  do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      then
        command -v "$candidate" 2>/dev/null || printf '%s\n' "$candidate"
        return 0
      fi
    elif [ -x "$candidate" ]; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)" || {
  echo "Python 3.11+ is required. Install Python 3.11 or newer, then rerun setup.sh." >&2
  exit 1
}

cd "$ROOT"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -U pip setuptools wheel
.venv/bin/python -m pip install -e app pytest

echo "Ready. Try: ./run_offline.sh"
