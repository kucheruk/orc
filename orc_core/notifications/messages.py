#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Localised message formatters for card-lifecycle Telegram notifications.

Each formatter returns a `(severity, text)` tuple. `NotificationService`
honours severity against `ORC_NOTIFY_MODE`:

- `normal` (default): only `Severity.NORMAL` messages reach Telegram.
- `debug`: both `NORMAL` and `INFO` are sent.

See `docs/notifications.md` for the policy behind each formatter.
"""

from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    INFO = "info"       # bookkeeping, routine progress, auto-healing
    NORMAL = "normal"   # operator-actionable (blocks, done, escalation)


def format_card_blocked(card_id: str, count: int, reason: str) -> tuple[Severity, str]:
    return Severity.NORMAL, (
        f"\U0001f6ab {card_id} заблокирована после {count} подряд ошибок: {reason}"
    )


def format_escalation(card_id: str, title: str, stage: str, loop_count: int) -> tuple[Severity, str]:
    return Severity.NORMAL, (
        f"\U0001f6a8 {card_id} BLOCKED\n"
        f"  {title}\n"
        f"  Stage: {stage}, loops: {loop_count}\n"
        f"  Use /unblock {card_id} <directive> to resume"
    )


def format_cycle_autounblock(from_id: str, to_id: str, decomposition_id: str) -> tuple[Severity, str]:
    return Severity.INFO, (
        "\U0001f9e9 ORC auto-unblock\n"
        f"Cycle `{from_id}->{to_id}` rewired.\n"
        f"Created/used `{decomposition_id}` to decompose coupling."
    )


def format_stale_assignments_released(count: int) -> tuple[Severity, str]:
    return Severity.INFO, (
        f"\U0001f9ef ORC auto-unblock released {count} stale assignment(s)."
    )


def format_blocked_accumulation(cards: list[tuple[str, str]]) -> tuple[Severity, str]:
    """Single aggregated alert when multiple cards are stuck in Blocked."""
    lines = [f"\U0001f6d1 {len(cards)} card(s) blocked — human review needed:"]
    for card_id, stage in cards[:10]:
        lines.append(f"  - {card_id} ({stage})")
    if len(cards) > 10:
        lines.append(f"  … and {len(cards) - 10} more")
    lines.append("Use /unblock <ID> <directive> in TUI to resume each.")
    return Severity.NORMAL, "\n".join(lines)


def format_card_skipped(card_id: str, reason: str = "") -> tuple[Severity, str]:
    text = f"\u23e9 {card_id} skipped \u2192 8_Done"
    if reason:
        text += f"\n  reason: {reason}"
    return Severity.NORMAL, text


def format_orc_startup(workspace: str, max_sessions: int) -> tuple[Severity, str]:
    return Severity.NORMAL, (
        f"\U0001f7e2 ORC started\n"
        f"  workspace: {workspace}\n"
        f"  max sessions: {max_sessions}"
    )


def format_orc_shutdown(reason: str = "") -> tuple[Severity, str]:
    text = "\U0001f534 ORC shutdown"
    if reason:
        text += f" ({reason})"
    return Severity.NORMAL, text


def with_teamlead_signature(severity: Severity, text: str) -> tuple[Severity, str]:
    """Prefix a teamlead-originated message with a consistent signature."""
    return severity, f"**Teamlead**: {text}"
