"""Error-message truncation limits shared across packages.

Kept separate from any domain to avoid cross-package cycles (e.g. agents/session_types
re-exporting to git/). Values are in characters.
"""
from __future__ import annotations

TRACEBACK_TRUNCATE = 2000
ERROR_TRUNCATE = 500
REASON_TRUNCATE = 200
CONFLICT_ERROR_TRUNCATE = 300
