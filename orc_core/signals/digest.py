#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a human-readable digest for a window of signals."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .journal import SignalKind


def format_digest(signals: list[dict[str, Any]], *, window_seconds: int) -> str:
    mins = max(window_seconds // 60, 1)
    if not signals:
        return f"No signals in the last {mins} min."

    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in signals:
        by_kind[s.get("kind", "")].append(s)

    lines: list[str] = [
        f"## Signals digest — last {mins} min ({len(signals)} events)",
    ]

    lines.extend(_section_pipeline(by_kind))
    lines.extend(_section_problems(by_kind))
    lines.extend(_section_teamlead(by_kind))
    lines.extend(_section_orc(by_kind))

    return "\n".join(line for line in lines if line is not None)


def _hhmmss(ts: str) -> str:
    # "2026-04-19T22:45:01+00:00" -> "22:45:01"
    return ts[11:19] if len(ts) >= 19 else ts


def _section_pipeline(by_kind: dict[str, list[dict[str, Any]]]) -> list[str]:
    done = by_kind.get(SignalKind.CARD_DONE.value, [])
    moved = by_kind.get(SignalKind.CARD_MOVED.value, [])
    blocked = by_kind.get(SignalKind.CARD_BLOCKED.value, [])
    unblocked = by_kind.get(SignalKind.CARD_UNBLOCKED.value, [])
    escalated = by_kind.get(SignalKind.CARD_ESCALATED.value, [])
    skipped = by_kind.get(SignalKind.CARD_SKIPPED.value, [])
    created = by_kind.get(SignalKind.CARD_CREATED.value, [])
    if not (done or moved or blocked or unblocked or escalated or skipped or created):
        return []
    lines = ["", "### Pipeline"]
    if done:
        ids = _uniq([s.get("task_id", "?") for s in done])
        lines.append(f"- {len(done)} → Done: " + ", ".join(ids))
    if skipped:
        ids = _uniq([s.get("task_id", "?") for s in skipped])
        lines.append(f"- {len(skipped)} skipped: " + ", ".join(ids))
    if blocked:
        lines.append(f"- {len(blocked)} blocked:")
        for s in blocked:
            ctx = s.get("context", {}) or {}
            detail = ""
            if "tokens_spent" in ctx and "token_budget" in ctx:
                detail = f" tokens={ctx['tokens_spent']}/{ctx['token_budget']}"
            role = ctx.get("role", "")
            role_s = f" role={role}" if role else ""
            lines.append(
                f"    * {s.get('task_id', '?')} — {s.get('reason', '?')}{role_s}{detail}"
            )
    if escalated:
        ids = _uniq([s.get("task_id", "?") for s in escalated])
        lines.append(f"- {len(escalated)} escalated: " + ", ".join(ids))
    if unblocked:
        ids = _uniq([s.get("task_id", "?") for s in unblocked])
        lines.append(f"- {len(unblocked)} unblocked: " + ", ".join(ids))
    if created:
        ids = _uniq([s.get("task_id", "?") for s in created])
        lines.append(f"- {len(created)} created: " + ", ".join(ids))
    if moved:
        # Summarise stage transitions as a histogram so we don't print 80 lines.
        hist = Counter((s.get("context", {}).get("from", "?"),
                        s.get("context", {}).get("to", "?")) for s in moved)
        parts = [f"{fr}→{to}×{n}" for (fr, to), n in hist.most_common()]
        lines.append(f"- {len(moved)} stage moves: " + ", ".join(parts))
    return lines


def _section_problems(by_kind: dict[str, list[dict[str, Any]]]) -> list[str]:
    vf = by_kind.get(SignalKind.ATTEMPT_VALIDATION_FAILED.value, [])
    disc = by_kind.get(SignalKind.ATTEMPT_DISCARDED.value, [])
    mx = by_kind.get(SignalKind.ATTEMPT_MAX_RESTARTS.value, [])
    if not (vf or disc or mx):
        return []
    lines = ["", "### Problems"]
    if vf:
        pair = Counter(
            (s.get("task_id", "?"), (s.get("context", {}) or {}).get("role", ""))
            for s in vf
        )
        parts = [f"{t} ({r}) ×{n}" if r else f"{t} ×{n}" for (t, r), n in pair.most_common()]
        lines.append(f"- {len(vf)} validation_failed: " + ", ".join(parts))
        # Show unique failure reasons once to help diagnosis.
        reasons = _uniq([s.get("reason", "") for s in vf if s.get("reason")])
        for r in reasons[:3]:
            lines.append(f"    * reason: {r}")
    if disc:
        total_tokens = sum(int((s.get("context") or {}).get("tokens", 0) or 0) for s in disc)
        by_reason = Counter(s.get("reason", "?") for s in disc)
        parts = [f"{reason}×{n}" for reason, n in by_reason.most_common()]
        lines.append(
            f"- {len(disc)} discarded attempts "
            f"({total_tokens:,} tokens total): " + ", ".join(parts)
        )
    if mx:
        ids = _uniq([s.get("task_id", "?") for s in mx])
        lines.append(f"- {len(mx)} max_restarts: " + ", ".join(ids))
    return lines


def _section_teamlead(by_kind: dict[str, list[dict[str, Any]]]) -> list[str]:
    hc = by_kind.get(SignalKind.TEAMLEAD_HEALTH_CHECK.value, [])
    arb = by_kind.get(SignalKind.TEAMLEAD_ARBITRATION.value, [])
    dec = by_kind.get(SignalKind.TEAMLEAD_DECISION.value, [])
    if not (hc or arb or dec):
        return []
    lines = ["", "### Teamlead"]
    if hc:
        diag_counts = Counter(s.get("reason", "?") for s in hc)
        parts = [f"{reason}×{n}" for reason, n in diag_counts.most_common(3)]
        lines.append(f"- {len(hc)} health checks: " + ", ".join(parts))
    if arb:
        ids = _uniq([s.get("task_id", "?") for s in arb])
        lines.append(f"- {len(arb)} arbitrations: " + ", ".join(ids))
    if dec:
        actions = Counter()
        for s in dec:
            for a in (s.get("context", {}) or {}).get("actions", []) or []:
                actions[str(a)] += 1
        if actions:
            parts = [f"{a}×{n}" for a, n in actions.most_common(5)]
            lines.append(f"- {len(dec)} decisions, actions: " + ", ".join(parts))
        else:
            lines.append(f"- {len(dec)} decisions")
    return lines


def _section_orc(by_kind: dict[str, list[dict[str, Any]]]) -> list[str]:
    entries: list[tuple[str, str, str]] = []
    for kind in (
        SignalKind.ORC_STARTUP.value,
        SignalKind.ORC_SHUTDOWN.value,
        SignalKind.ORC_CRASH.value,
        SignalKind.ORC_IDLE_WINDOW.value,
    ):
        for s in by_kind.get(kind, []):
            entries.append((_hhmmss(s.get("ts", "")), kind, s.get("reason", "")))
    if not entries:
        return []
    entries.sort()
    lines = ["", "### ORC lifecycle"]
    for t, kind, reason in entries:
        suffix = f" — {reason}" if reason else ""
        lines.append(f"- {t} {kind}{suffix}")
    return lines


def _uniq(items: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for x in items:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out
