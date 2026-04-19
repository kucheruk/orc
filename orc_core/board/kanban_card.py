#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban card domain aggregate — invariants and mutators only.

Serialization (markdown ↔ dataclass) lives in `kanban_card_serializer.py`;
section helpers live in `card_sections.py`. This module stays free of
storage-format concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .action_constants import Action, ClassOfService
from .stage_constants import STAGE_INBOX, STAGE_ORDER

# Fields agents are NOT allowed to change (Python-only)
PROTECTED_FIELDS: frozenset[str] = frozenset({
    "id", "stage", "roi", "assigned_agent", "created_at", "state_version",
})

# Fields excluded from YAML frontmatter (runtime-only). Consumed by the
# serializer module; colocated with the dataclass so the two stay in sync.
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
    state_version: int = 0
    body: str = ""
    tokens_spent: int = 0
    # Tokens consumed by attempts whose result was discarded (ORC restart,
    # stale fingerprint, validation failure). Subtracted from tokens_spent
    # when gating the budget so "not agent's fault" burn does not block a card.
    tokens_discarded: int = 0
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
        self.refresh_roi()
        self.updated_at = _now_iso()

    def advance_state_version(self) -> None:
        self.state_version += 1

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
    def tokens_spent_net(self) -> int:
        """Tokens spent on kept attempts (discarded restarts subtracted)."""
        return max(0, self.tokens_spent - self.tokens_discarded)

    @property
    def is_budget_exhausted(self) -> bool:
        return self.token_budget > 0 and self.tokens_spent_net >= self.token_budget

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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
