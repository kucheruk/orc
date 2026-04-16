#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification formatting for kanban card lifecycle events."""

from .kanban_card import SECTION_NOTES, KanbanCard
from .stage_constants import STAGE_DONE, STAGE_SHORT_NAMES


def extract_card_summary(card: KanbanCard) -> str:
    """Extract last implementation/integration note block from card body."""
    body = card.body or ""
    # Find section 3 content
    in_section3 = False
    section3_lines: list[str] = []
    for line in body.splitlines():
        if line.startswith(SECTION_NOTES[:5]):  # "# 3." — robust match
            in_section3 = True
            continue
        if in_section3 and line.startswith("# "):
            break
        if in_section3:
            section3_lines.append(line)
    if not section3_lines:
        return ""
    # Take last non-empty paragraph (integrator's summary is appended last)
    text = "\n".join(section3_lines).strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return ""
    last = paragraphs[-1]
    # Truncate for telegram readability
    if len(last) > 500:
        last = last[:497] + "..."
    return last


def format_completion_message(
    card: KanbanCard,
    role: str,
    old_stage: str,
    old_action: str,
    old_cos: str,
    elapsed: float,
    progress: tuple[int, int, int],
) -> str | None:
    """Format a rich notification message for a card lifecycle event.

    Returns None if the transition is not notification-worthy.
    """
    mins = elapsed / 60.0
    new_stage = card.stage
    new_action = card.action

    # Only notify on meaningful transitions
    stage_changed = old_stage != new_stage
    became_expedite = card.class_of_service == "expedite" and old_cos != "expedite"
    is_done = new_stage == STAGE_DONE

    if not stage_changed and not became_expedite:
        return None

    fr = STAGE_SHORT_NAMES.get(old_stage, old_stage)
    to = STAGE_SHORT_NAMES.get(new_stage, new_stage)

    icon = "\u2705" if is_done else "\U0001f504"
    if became_expedite:
        icon = "\U0001f525"

    lines = [f"{icon} {card.id}: {card.title}"]
    lines.append(f"  {role} ({mins:.0f}m): {fr} \u2192 {to}")
    if old_action != new_action:
        lines.append(f"  Action: {old_action} \u2192 {new_action}")
    if became_expedite:
        lines.append(f"  EXPEDITE: {card.cos_justification or 'no reason'}")

    if is_done:
        summary = extract_card_summary(card)
        if summary:
            lines.append(f"\n{summary}")

    done, _ip, total = progress
    lines.append(f"\nProgress: {done}/{total}")

    return "\n".join(lines)
