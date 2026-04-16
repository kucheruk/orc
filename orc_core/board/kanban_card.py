#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban card: YAML frontmatter + markdown body, parse/serialize/validate."""

from __future__ import annotations

from dataclasses import dataclass, field, fields as _dc_fields
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .action_constants import Action, ClassOfService
from .stage_constants import STAGE_INBOX, STAGE_ORDER
from ..text_parse import parse_frontmatter

# Fields agents are NOT allowed to change (Python-only)
PROTECTED_FIELDS: frozenset[str] = frozenset({
    "id", "stage", "roi", "assigned_agent", "created_at",
})

# Fields excluded from YAML frontmatter (runtime-only)
_RUNTIME_FIELDS: frozenset[str] = frozenset({"body", "file_path"})


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
    tokens_spent: int = 0
    token_budget: int = 0    # 0 = no limit; set from effort_score * multiplier
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

    @property
    def is_assigned(self) -> bool:
        return bool(self.assigned_agent)

    @property
    def is_blocked(self) -> bool:
        return self.action == Action.BLOCKED

    @property
    def is_done(self) -> bool:
        from .stage_constants import STAGE_DONE
        return self.stage == STAGE_DONE

    def is_looping(self, threshold: int = 2) -> bool:
        return self.loop_count >= threshold

    @property
    def is_budget_exhausted(self) -> bool:
        return self.token_budget > 0 and self.tokens_spent >= self.token_budget

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
        """Build YAML-serializable dict from dataclass fields (SSOT)."""
        result: dict[str, Any] = {}
        for f in _dc_fields(self):
            if f.name in _RUNTIME_FIELDS:
                continue
            val = getattr(self, f.name)
            if isinstance(val, list):
                val = [str(v) for v in val]
            elif isinstance(val, Enum):
                val = val.value  # StrEnum → plain str for yaml.safe_load compat
            result[f.name] = val
        return result


# ── Parsing ─────────────────────────────────────────────────────


def _normalize_action(raw: str) -> str:
    """Normalize action string to match Action enum casing (e.g., 'coding' → 'Coding')."""
    s = str(raw).strip()
    if not s:
        return Action.PRODUCT
    # Try exact match first
    try:
        return Action(s)
    except ValueError:
        pass
    # Try case-insensitive match
    for member in Action:
        if member.value.lower() == s.lower():
            return member.value
    return s  # return as-is, validation will catch it


def parse_card(text: str, file_path: Path | None = None) -> KanbanCard:
    data, body = parse_frontmatter(text, str(file_path or "<string>"))
    defaults = KanbanCard(id="")
    kwargs: dict[str, Any] = {"body": body, "file_path": file_path}
    for f in _dc_fields(defaults):
        if f.name in _RUNTIME_FIELDS:
            continue
        default_val = getattr(defaults, f.name)
        raw = data.get(f.name, default_val)
        # Per-field coercion
        if f.name == "action":
            kwargs[f.name] = _normalize_action(raw)
        elif f.name == "dependencies":
            kwargs[f.name] = _parse_list(raw)
        elif isinstance(default_val, int):
            kwargs[f.name] = int(raw or 0)
        elif isinstance(default_val, float):
            kwargs[f.name] = float(raw or 0.0)
        else:
            kwargs[f.name] = str(raw or "")
    return KanbanCard(**kwargs)


def validate_card(card: KanbanCard) -> list[str]:
    """Validate card invariants. Delegates to card.validate()."""
    return card.validate()


# Card body section headers — SSOT for all section references
SECTION_PRODUCT = "# 1. Product Requirements"
SECTION_DESIGN = "# 2. Technical Design & DoD"
SECTION_NOTES = "# 3. Implementation Notes"
SECTION_FEEDBACK = "# 4. Feedback & Checklist"


def new_card_body() -> str:
    return (
        f"{SECTION_PRODUCT}\n\n\n"
        f"{SECTION_DESIGN}\n\n\n"
        f"{SECTION_NOTES}\n\n\n"
        f"{SECTION_FEEDBACK}\n"
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
        return [str(v).strip() for v in val if str(v).strip()]
    # Handle comma-separated string: "TASK-1, TASK-2" → ["TASK-1", "TASK-2"]
    s = str(val)
    if "," in s:
        return [part.strip() for part in s.split(",") if part.strip()]
    s = s.strip()
    return [s] if s else []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
