#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build role-specific prompts for kanban agents by injecting card and board context."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .kanban_constants import STAGES
from .kanban_pull import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
)

if TYPE_CHECKING:
    from .kanban_board import KanbanBoard
    from .kanban_card import KanbanCard

_BASE_DIR = Path(__file__).resolve().parents[1]
_PROMPTS_DIR = _BASE_DIR / "prompts"

ROLE_TEAMLEAD = "teamlead"
ROLE_TEAMLEAD_TRIAGE = "teamlead_triage"

_PROMPT_FILES: dict[str, str] = {
    ROLE_PRODUCT: "kanban_product.txt",
    ROLE_ARCHITECT: "kanban_architect.txt",
    ROLE_CODER: "kanban_coder.txt",
    ROLE_REVIEWER: "kanban_reviewer.txt",
    ROLE_TESTER: "kanban_tester.txt",
    ROLE_INTEGRATOR: "kanban_integrator.txt",
    ROLE_TEAMLEAD: "kanban_teamlead.txt",
    ROLE_TEAMLEAD_TRIAGE: "kanban_teamlead_triage.txt",
}

# Cache loaded templates
_template_cache: dict[str, str] = {}


def build_prompt(role: str, card: "KanbanCard", board: "KanbanBoard") -> str:
    """Build a complete prompt for the given role, card, and board state."""
    template = _load_template(role)
    card_content = card.to_markdown()
    card_path = str(card.file_path) if card.file_path else f"tasks/{card.stage}/{card.id}.md"
    board_summary = format_board_summary(board)

    return template.format_map(_SafeDict(
        board_summary=board_summary,
        card_path=card_path,
        card_content=card_content,
        card_id=card.id,
        card_stage=card.stage,
        card_action=card.action,
        loop_count=str(card.loop_count),
    ))


def format_board_summary(board: "KanbanBoard") -> str:
    """Format board state as a compact text table for prompts."""
    lines = ["| Stage | Cards | WIP Limit | Free |"]
    lines.append("|-------|-------|-----------|------|")
    summary = board.summary()
    for stage in STAGES:
        info = summary.get(stage, {"count": 0, "wip_limit": 0})
        count = info["count"]
        limit = info["wip_limit"]
        free = max(0, limit - count) if limit > 0 else "∞"
        lines.append(f"| {stage} | {count} | {limit or '∞'} | {free} |")
    return "\n".join(lines)


def _load_template(role: str) -> str:
    if role in _template_cache:
        return _template_cache[role]
    filename = _PROMPT_FILES.get(role)
    if not filename:
        raise ValueError(f"Unknown kanban role: {role}")
    path = _PROMPTS_DIR / filename
    template = path.read_text(encoding="utf-8")
    _template_cache[role] = template
    return template


def clear_template_cache() -> None:
    _template_cache.clear()


class _SafeDict(dict):
    """Dict that returns the key as-is for missing format placeholders."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
