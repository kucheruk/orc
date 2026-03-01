#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is not installed. Install from https://docs.astral.sh/uv/" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[worktree-setup] syncing dependencies"
uv sync --dev

echo "[worktree-setup] validating runtime/test dependencies"
uv run python - <<'PY'
from importlib.util import find_spec
import sys

required = ("rich", "textual", "psutil", "pytest")
missing = [name for name in required if find_spec(name) is None]
if missing:
    print(f"missing dependencies: {', '.join(missing)}", file=sys.stderr)
    raise SystemExit(1)
print("ok: all required dependencies are available")
PY

echo "[worktree-setup] done"
