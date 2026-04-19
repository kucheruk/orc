#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Localised message formatters for card-lifecycle Telegram notifications.

Keeping presentation concerns in this module lets use cases and runners emit
structured domain events without embedding locale- or channel-specific text.
"""

from __future__ import annotations


def format_card_blocked(card_id: str, count: int, reason: str) -> str:
    return f"\U0001f6ab {card_id} заблокирована после {count} подряд ошибок: {reason}"


def format_escalation(card_id: str, title: str, stage: str, loop_count: int) -> str:
    return (
        f"\U0001f6a8 {card_id} BLOCKED\n"
        f"  {title}\n"
        f"  Stage: {stage}, loops: {loop_count}\n"
        f"  Use /unblock {card_id} <directive> to resume"
    )


def format_cycle_autounblock(from_id: str, to_id: str, decomposition_id: str) -> str:
    return (
        "\U0001f9e9 ORC auto-unblock\n"
        f"Cycle `{from_id}->{to_id}` rewired.\n"
        f"Created/used `{decomposition_id}` to decompose coupling."
    )


def format_stale_assignments_released(count: int) -> str:
    return f"\U0001f9ef ORC auto-unblock released {count} stale assignment(s)."


def format_blocked_accumulation(cards: list[tuple[str, str]]) -> str:
    """Single aggregated alert when multiple cards are stuck in Blocked.

    cards: list of (card_id, stage) pairs.
    """
    lines = [f"\U0001f6d1 {len(cards)} card(s) blocked — human review needed:"]
    for card_id, stage in cards[:10]:
        lines.append(f"  - {card_id} ({stage})")
    if len(cards) > 10:
        lines.append(f"  … and {len(cards) - 10} more")
    lines.append("Use /unblock <ID> <directive> in TUI to resume each.")
    return "\n".join(lines)
