#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban card: YAML frontmatter + markdown body, parse/serialize/validate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .kanban_constants import STAGE_INBOX, STAGE_ORDER, Action, ClassOfService
from .text_parse import parse_frontmatter

# Fields agents are NOT allowed to change (Python-only)
PROTECTED_FIELDS: frozenset[str] = frozenset({
    "id", "stage", "roi", "assigned_agent", "created_at",
})


@dataclass
class KanbanCard:
    id: str
    title: str = ""
    stage: str = STAGE_INBOX
    action: str = Action.PRODUCT
    class_of_service: str = ClassOfService.STANDARD
    cos_justification: str = ""
    deadline: str = ""
    value_score: int = 0
    effort_score: int = 0
    roi: float = 0.0
    dependencies: list[str] = field(default_factory=list)
    loop_count: int = 0
    assigned_agent: str = ""
    created_at: str = ""
    updated_at: str = ""
    body: str = ""
    # runtime — not serialized
    file_path: Path | None = field(default=None, repr=False)

    def compute_roi(self) -> float:
        if self.effort_score <= 0:
            return 0.0
        return round(self.value_score / self.effort_score, 2)

    def refresh_roi(self) -> None:
        self.roi = self.compute_roi()

    def touch(self) -> None:
        self.updated_at = _now_iso()

    # ── Domain operations ────────────────────────────────────────

    def can_move_to(self, target_stage: str, *, allow_backward: bool = False) -> bool:
        """Check if this card can transition to target_stage."""
        if allow_backward:
            return target_stage != self.stage
        return STAGE_ORDER.get(target_stage, -1) > STAGE_ORDER.get(self.stage, -1)

    def assign(self, agent_id: str) -> None:
        self.assigned_agent = agent_id
        self.touch()

    def release(self) -> None:
        self.assigned_agent = ""
        self.touch()

    def block(self, reason: str = "") -> None:
        self.action = Action.BLOCKED
        if reason:
            self.body += f"\n\n## Block Reason\n{reason}\n"
        self.touch()

    def unblock(self, directive: str = "") -> None:
        if directive:
            self.body += f"\n\n## Human Directive\n{directive}\n"
        self.action = Action.CODING
        self.loop_count = 0
        self.touch()

    def validate(self) -> list[str]:
        """Validate card invariants. Returns list of error messages (empty = valid)."""
        errors: list[str] = []
        if not self.id:
            errors.append("Card must have an id")
        if self.class_of_service == ClassOfService.EXPEDITE and not self.cos_justification:
            errors.append("Expedite cards require cos_justification")
        if self.class_of_service == ClassOfService.FIXED_DATE and not self.deadline:
            errors.append("Fixed-date cards require a deadline")
        if not (0 <= self.value_score <= 100):
            errors.append(f"value_score {self.value_score} out of 0-100 range")
        if not (0 <= self.effort_score <= 100):
            errors.append(f"effort_score {self.effort_score} out of 0-100 range")
        try:
            Action(self.action)
        except ValueError:
            errors.append(f"Invalid action: {self.action}")
        try:
            ClassOfService(self.class_of_service)
        except ValueError:
            errors.append(f"Invalid class_of_service: {self.class_of_service}")
        return errors

    # ── Serialization ───────────────────────────────────────────

    def to_markdown(self) -> str:
        fm = _build_frontmatter(self)
        return f"---\n{fm}---\n\n{self.body}"

    def frontmatter_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "stage": str(self.stage),
            "action": str(self.action),
            "class_of_service": str(self.class_of_service),
            "cos_justification": self.cos_justification,
            "deadline": self.deadline,
            "value_score": self.value_score,
            "effort_score": self.effort_score,
            "roi": self.roi,
            "dependencies": [str(d) for d in self.dependencies],
            "loop_count": self.loop_count,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Parsing ─────────────────────────────────────────────────────


def parse_card(text: str, file_path: Path | None = None) -> KanbanCard:
    data, body = parse_frontmatter(text, str(file_path or "<string>"))
    card = KanbanCard(
        id=str(data.get("id", "")),
        title=str(data.get("title", "")),
        stage=str(data.get("stage", STAGE_INBOX)),
        action=str(data.get("action", Action.PRODUCT)),
        class_of_service=str(data.get("class_of_service", ClassOfService.STANDARD)),
        cos_justification=str(data.get("cos_justification", "")),
        deadline=str(data.get("deadline", "") or ""),
        value_score=int(data.get("value_score", 0)),
        effort_score=int(data.get("effort_score", 0)),
        roi=float(data.get("roi", 0.0)),
        dependencies=_parse_list(data.get("dependencies")),
        loop_count=int(data.get("loop_count", 0)),
        assigned_agent=str(data.get("assigned_agent", "") or ""),
        created_at=str(data.get("created_at", "") or ""),
        updated_at=str(data.get("updated_at", "") or ""),
        body=body,
        file_path=file_path,
    )
    return card


def read_card(path: Path) -> KanbanCard:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_card(text, file_path=path)


def write_card(card: KanbanCard, path: Path | None = None) -> None:
    from .atomic_io import write_text_atomic

    target = path or card.file_path
    if target is None:
        raise ValueError("No path specified for card write")
    write_text_atomic(target, card.to_markdown())
    card.file_path = target


def validate_card(card: KanbanCard) -> list[str]:
    """Validate card invariants. Delegates to card.validate()."""
    return card.validate()


def new_card_body() -> str:
    return (
        "# 1. Product Requirements\n\n\n"
        "# 2. Technical Design & DoD\n\n\n"
        "# 3. Implementation Notes\n\n\n"
        "# 4. Feedback & Checklist\n"
    )


# ── Helpers ─────────────────────────────────────────────────────


def _build_frontmatter(card: KanbanCard) -> str:
    return yaml.dump(
        card.frontmatter_dict(),
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def _parse_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(v) for v in val]
    return [str(val)]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
