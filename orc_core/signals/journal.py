#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signal emission + load helpers."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Optional

from ..infra.io.state_paths import signals_path as _default_signals_path


class SignalKind(str, Enum):
    """Curated set. Keep small — every addition must pay its way in the digest."""

    CARD_CREATED = "card.created"
    CARD_MOVED = "card.moved"
    CARD_BLOCKED = "card.blocked"
    CARD_UNBLOCKED = "card.unblocked"
    CARD_ESCALATED = "card.escalated"
    CARD_DONE = "card.done"
    CARD_SKIPPED = "card.skipped"

    ATTEMPT_START = "attempt.start"
    ATTEMPT_FINISH = "attempt.finish"
    ATTEMPT_DISCARDED = "attempt.discarded"
    ATTEMPT_VALIDATION_FAILED = "attempt.validation_failed"
    ATTEMPT_MAX_RESTARTS = "attempt.max_restarts"

    TEAMLEAD_ARBITRATION = "teamlead.arbitration"
    TEAMLEAD_HEALTH_CHECK = "teamlead.health_check"
    TEAMLEAD_DECISION = "teamlead.decision"

    ORC_STARTUP = "orc.startup"
    ORC_SHUTDOWN = "orc.shutdown"
    ORC_CRASH = "orc.crash"
    ORC_IDLE_WINDOW = "orc.idle_window"


_write_lock = threading.Lock()


def signals_path_for(workdir: str) -> Path:
    return _default_signals_path(workdir)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit_signal(
    kind: SignalKind | str,
    reason: str,
    *,
    workdir: str | None = None,
    path: Path | None = None,
    task_id: str = "",
    context: dict[str, Any] | None = None,
) -> None:
    """Append a signal line. Best-effort — never raises.

    Workspace lookup order: explicit `path` → explicit `workdir` →
    `set_log_context(workdir=...)` module state → `$ORC_WORKSPACE`.
    """
    try:
        if path is None:
            resolved = workdir
            if not resolved:
                # Reuse the shared logging context set by CLI at startup.
                from ..log import _ctx as _log_ctx
                resolved = (_log_ctx.log_workdir or "").strip()
            if not resolved:
                resolved = os.environ.get("ORC_WORKSPACE", "")
            if not resolved:
                return
            path = signals_path_for(resolved)
        payload = {
            "ts": _now_iso(),
            "kind": kind.value if isinstance(kind, SignalKind) else str(kind),
            "reason": str(reason or ""),
            "task_id": str(task_id or ""),
            "context": _coerce_context(context),
            "pid": os.getpid(),
        }
        line = json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock, path.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        # Signals must never break the caller. Silent failure is acceptable —
        # the primary orc.log still captures the underlying event.
        return


def _coerce_context(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {str(k): _coerce_value(v) for k, v in value.items()}
    return {"value": _coerce_value(value)}


def _coerce_value(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, (list, tuple)):
        return [_coerce_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _coerce_value(x) for k, x in v.items()}
    return str(v)


def _json_default(v: Any) -> Any:
    return _coerce_value(v)


def load_since(
    path: Path,
    *,
    seconds: int = 1200,
    now: Optional[datetime] = None,
) -> list[dict[str, Any]]:
    """Read signals newer than `seconds` ago. Returns chronological list."""
    if not path.exists():
        return []
    if now is None:
        now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=seconds)
    out: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sig = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(sig.get("ts", ""))
                if ts is None or ts < cutoff:
                    continue
                out.append(sig)
    except OSError:
        return []
    return out


def _parse_ts(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def iter_kinds(signals: Iterable[dict[str, Any]], kind: SignalKind | str) -> Iterable[dict[str, Any]]:
    target = kind.value if isinstance(kind, SignalKind) else str(kind)
    for s in signals:
        if s.get("kind") == target:
            yield s
