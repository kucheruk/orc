#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban board: reads cards from folder structure, enforces WIP limits, moves cards."""

from __future__ import annotations

import logging
import re
import shutil
import threading
from pathlib import Path
from typing import Callable, Optional

import yaml

from .kanban_board_health import detect_wip_deadlock as _detect_wip_deadlock
from .kanban_card import KanbanCard, read_card, write_card, new_card_body
from .kanban_constants import (
    COS_PRIORITY,
    DEFAULT_WIP_LIMITS,
    INDEX_FILENAME,
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_INBOX,
    STAGE_ORDER,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
    STAGES,
    WIP_STAGES,
)

_logger = logging.getLogger(__name__)


class KanbanBoard:
    """In-memory snapshot of the kanban board backed by the tasks/ folder tree."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._lock = threading.RLock()
        self._cards: list[KanbanCard] = []
        self._wip_limits: dict[str, int] = dict(DEFAULT_WIP_LIMITS)
        self._card_locks: dict[str, threading.Lock] = {}
        self._last_stage_mtimes: dict[str, float] = {}
        self.on_move: Optional[Callable[[str, str, str, str], None]] = None  # (card_id, from, to, reason)
        self.on_action_change: Optional[Callable[[str, str, str, str], None]] = None  # (card_id, old, new, role)
        self.refresh(force=True)

    # ── State hydration ─────────────────────────────────────────

    def refresh(self, *, force: bool = False) -> None:
        if not force and self._is_fresh():
            return
        with self._lock:
            self._cards = []
            self._wip_limits = dict(DEFAULT_WIP_LIMITS)
            for stage in STAGES:
                stage_dir = self._tasks_dir / stage
                if not stage_dir.is_dir():
                    continue
                self._read_index(stage_dir, stage)
                self._read_cards(stage_dir, stage)
            self._recompute_roi()
            self._last_stage_mtimes = self._scan_stage_mtimes()

    def _is_fresh(self) -> bool:
        """Check if any stage directory has been modified since last refresh."""
        if not self._last_stage_mtimes:
            return False
        return self._scan_stage_mtimes() == self._last_stage_mtimes

    def _scan_stage_mtimes(self) -> dict[str, float]:
        result: dict[str, float] = {}
        for stage in STAGES:
            stage_dir = self._tasks_dir / stage
            if stage_dir.is_dir():
                try:
                    result[stage] = stage_dir.stat().st_mtime
                except OSError:
                    pass
        return result

    def _read_index(self, stage_dir: Path, stage: str) -> None:
        idx = stage_dir / INDEX_FILENAME
        if not idx.exists():
            return
        try:
            text = idx.read_text(encoding="utf-8")
            m = re.match(r"\A---\n(.*?\n)---", text, re.DOTALL)
            if m:
                data = yaml.safe_load(m.group(1)) or {}
                limit = data.get("wip_limit")
                if isinstance(limit, int) and limit > 0:
                    self._wip_limits[stage] = limit
        except Exception as exc:
            _logger.warning("Failed to read %s: %s", idx, exc)

    def _read_cards(self, stage_dir: Path, stage: str) -> None:
        for md in sorted(stage_dir.glob("*.md")):
            if md.name == INDEX_FILENAME:
                continue
            try:
                card = read_card(md)
                card.stage = stage  # trust folder over frontmatter
                self._cards.append(card)
            except Exception as exc:
                _logger.warning("Failed to parse card %s: %s", md, exc)

    def _recompute_roi(self) -> None:
        for card in self._cards:
            card.refresh_roi()

    # ── Per-card locking ──────────────────────────────────────────

    def card_lock(self, card_id: str) -> threading.Lock:
        """Return a per-card lock, creating it lazily. Thread-safe."""
        with self._lock:
            if card_id not in self._card_locks:
                self._card_locks[card_id] = threading.Lock()
            return self._card_locks[card_id]

    # ── Queries ─────────────────────────────────────────────────

    @property
    def cards(self) -> list[KanbanCard]:
        with self._lock:
            return list(self._cards)

    def cards_in_stage(self, stage: str) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards if c.stage == stage]

    def cards_with_action(self, stage: str, action: str) -> list[KanbanCard]:
        with self._lock:
            return [
                c for c in self._cards
                if c.stage == stage and c.action == action and not c.assigned_agent
            ]

    def card_by_id(self, card_id: str) -> Optional[KanbanCard]:
        with self._lock:
            for c in self._cards:
                if c.id == card_id:
                    return c
        return None

    def find_card_file(self, card_id: str) -> Optional[Path]:
        """Search all stage directories for a card file by ID.

        Use when the cached ``file_path`` may be stale (e.g. another agent
        moved the card while an agent was running).
        """
        filename = f"{card_id}.md"
        for stage in STAGES:
            candidate = self._tasks_dir / stage / filename
            if candidate.exists():
                return candidate
        return None

    def stage_count(self, stage: str) -> int:
        with self._lock:
            return sum(1 for c in self._cards if c.stage == stage)

    def wip_limit(self, stage: str) -> int:
        return self._wip_limits.get(stage, 999)

    def has_wip_room(self, stage: str) -> bool:
        if stage not in WIP_STAGES:
            return True
        return self.stage_count(stage) < self.wip_limit(stage)

    def wip_free(self, stage: str) -> int:
        if stage not in WIP_STAGES:
            return 999
        return max(0, self.wip_limit(stage) - self.stage_count(stage))

    def looping_cards(self, threshold: int = 2) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards
                    if c.loop_count >= threshold and not c.assigned_agent
                    and c.stage != STAGE_DONE]

    def blocked_cards(self) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards
                    if c.action == "Blocked" and not c.assigned_agent
                    and c.stage != STAGE_DONE]

    def _apply_deferred_moves(self) -> None:
        """Move cards whose action doesn't match their stage (stuck after restart)."""
        _EXPECTED_STAGE = {
            (STAGE_TESTING, "Integrating"): STAGE_HANDOFF,
            (STAGE_HANDOFF, "Done"): STAGE_DONE,
            (STAGE_CODING, "Reviewing"): STAGE_REVIEW,
            (STAGE_REVIEW, "Testing"): STAGE_TESTING,
            # Integrator reject paths
            (STAGE_HANDOFF, "Reviewing"): STAGE_REVIEW,
            (STAGE_HANDOFF, "Testing"): STAGE_TESTING,
            # Tester/reviewer bounce-back
            (STAGE_TESTING, "Coding"): STAGE_CODING,
            (STAGE_REVIEW, "Coding"): STAGE_CODING,
        }
        for card in list(self._cards):
            if card.assigned_agent:
                continue
            target = _EXPECTED_STAGE.get((card.stage, card.action))
            if target and self.has_wip_room(target):
                _logger.info("Deferred move: %s %s → %s (action=%s)",
                             card.id, card.stage, target, card.action)
                is_backward = STAGE_ORDER.get(target, 0) < STAGE_ORDER.get(card.stage, 0)
                self.move_card(card, target, allow_backward=is_backward,
                               reason=f"deferred: {card.action}")

    def detect_wip_deadlock(self) -> str:
        """Detect WIP deadlock conditions. Returns diagnostic string or '' if healthy."""
        with self._lock:
            return _detect_wip_deadlock(list(self._cards), dict(self._wip_limits))

    def has_unmet_dependencies(self, card: KanbanCard) -> bool:
        if not card.dependencies:
            return False
        with self._lock:
            done_ids = {c.id for c in self._cards if c.stage == STAGE_DONE}
        return any(dep not in done_ids for dep in card.dependencies)

    # ── Card operations ─────────────────────────────────────────

    def move_card(self, card: KanbanCard, new_stage: str, *, allow_backward: bool = False,
                  reason: str = "") -> None:
        old_stage = card.stage
        if not card.can_move_to(new_stage, allow_backward=allow_backward):
            raise ValueError(f"Cannot move card {card.id} from {old_stage} to {new_stage} (must move right)")

        old_path = card.file_path
        if old_path is None:
            raise ValueError(f"Card {card.id} has no file_path")

        new_dir = self._tasks_dir / new_stage
        new_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_dir / old_path.name

        with self._lock:
            # Re-check WIP inside the lock to avoid TOCTOU race
            if new_stage in WIP_STAGES:
                count = sum(1 for c in self._cards if c.stage == new_stage)
                limit = self._wip_limits.get(new_stage, 999)
                if count >= limit:
                    raise ValueError(f"WIP limit reached for {new_stage}")
            shutil.move(str(old_path), str(new_path))
            card.stage = new_stage
            card.file_path = new_path
            card.touch()
            write_card(card, new_path)

        if self.on_move:
            try:
                self.on_move(card.id, old_stage, new_stage, reason)
            except Exception:
                _logger.warning("on_move callback failed for %s", card.id, exc_info=True)

    def save_card(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        with self._lock:
            card.touch()
            card.refresh_roi()
            write_card(card)
        if old_action and old_action != card.action and self.on_action_change:
            try:
                self.on_action_change(card.id, old_action, card.action, role)
            except Exception:
                _logger.warning("on_action_change callback failed for %s", card.id, exc_info=True)

    def assign_agent(self, card: KanbanCard, agent_id: str) -> None:
        with self._lock:
            card.assign(agent_id)
            write_card(card)

    def release_agent(self, card: KanbanCard) -> None:
        with self._lock:
            card.release()
            write_card(card)

    def set_wip_limit(self, stage: str, limit: int) -> None:
        """Write WIP limit to _index.md and update in-memory cache."""
        if stage not in STAGES:
            raise ValueError(f"Unknown stage: {stage}")
        stage_dir = self._tasks_dir / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        idx = stage_dir / INDEX_FILENAME
        idx.write_text(f"---\nwip_limit: {limit}\n---\n", encoding="utf-8")
        with self._lock:
            self._wip_limits[stage] = limit

    # ── Sorting ─────────────────────────────────────────────────

    def pick_best(self, stage: str, action: str, *, check_deps: bool = True) -> Optional[KanbanCard]:
        candidates = self.cards_with_action(stage, action)
        if check_deps:
            candidates = [c for c in candidates if not self.has_unmet_dependencies(c)]
        if not candidates:
            return None
        return sorted(candidates, key=_priority_key)[0]

    # ── Board summary (for prompts / TUI) ───────────────────────

    def summary(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for stage in STAGES:
            count = self.stage_count(stage)
            limit = self._wip_limits.get(stage, 0)
            result[stage] = {"count": count, "wip_limit": limit}
        return result

    # ── Card creation ───────────────────────────────────────────

    def create_inbox_card(self, card_id: str, title: str) -> KanbanCard:
        from datetime import datetime, timezone
        card = KanbanCard(
            id=card_id, title=title, stage=STAGE_INBOX, action="Product",
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            body=new_card_body(),
        )
        inbox_dir = self._tasks_dir / STAGE_INBOX
        inbox_dir.mkdir(parents=True, exist_ok=True)
        path = inbox_dir / f"{card_id}.md"
        write_card(card, path)
        with self._lock:
            self._cards.append(card)
        return card

    def create_expedite_card(
        self,
        card_id: str,
        title: str,
        body: str,
        *,
        stage: str = STAGE_CODING,
        action: str = "Coding",
        cos_justification: str = "",
    ) -> KanbanCard:
        """Create an expedite card directly at the given stage, bypassing inbox."""
        from datetime import datetime, timezone
        card = KanbanCard(
            id=card_id, title=title, stage=stage, action=action,
            class_of_service="expedite",
            cos_justification=cos_justification,
            value_score=100, effort_score=20,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            body=body,
        )
        stage_dir = self._tasks_dir / stage
        stage_dir.mkdir(parents=True, exist_ok=True)
        path = stage_dir / f"{card_id}.md"
        write_card(card, path)
        with self._lock:
            self._cards.append(card)
        return card

    def next_card_id(self) -> str:
        with self._lock:
            nums = []
            for c in self._cards:
                parts = c.id.rsplit("-", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
            next_num = max(nums, default=0) + 1
        return f"TASK-{next_num:03d}"


def _priority_key(card: KanbanCard) -> tuple[int, str, float]:
    cos_rank = COS_PRIORITY.get(card.class_of_service, 9)
    deadline = card.deadline if card.class_of_service == "fixed-date" else "9999-12-31"
    return (cos_rank, deadline, -card.roi)
