#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Operator-facing signal journal.

Each signal is an append-only JSON line written to
`{state_root}/analytics/signals.jsonl`. The set of `kind` values is
explicitly curated — not every WARN log is a signal, only events an
operator would want to see in a digest.

Consumers:
- `tail -F signals.jsonl | jq` — live view.
- `orc signals --since 20m` — formatted digest for a rolling window.
- Any external supervisor grepping by `kind`.

See `docs/signals.md` for the catalogue and call sites.
"""

from .journal import (
    SignalKind,
    emit_signal,
    load_since,
    signals_path_for,
)
from .digest import format_digest

__all__ = [
    "SignalKind",
    "emit_signal",
    "load_since",
    "signals_path_for",
    "format_digest",
]
