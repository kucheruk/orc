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

from .kanban_card import KanbanCard, read_card, write_card
from .kanban_constants import (
    COS_PRIORITY,
    DEFAULT_WIP_LIMITS,
    INDEX_FILENAME,
    STAGE_ORDER,
    STAGES,
    WIP_STAGES,
)

_logger = logging.getLogger(__name__)


class KanbanBoard:
    """In-memory snapshot of the kanban board backed by the tasks/ folder tree."""

    def __init__(self, tasks_dir: Path) -> None:
        self._tasks_dir = tasks_dir
        self._lock = threading.Lock()
        self._cards: list[KanbanCard] = []
        self._wip_limits: dict[str, int] = dict(DEFAULT_WIP_LIMITS)
        self.on_move: Optional[Callable[[str, str, str, str], None]] = None  # (card_id, from, to, reason)
        self.on_action_change: Optional[Callable[[str, str, str, str], None]] = None  # (card_id, old, new, role)
        self.refresh()

    # ── State hydration ─────────────────────────────────────────

    def refresh(self) -> None:
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
                    if c.loop_count >= threshold and not c.assigned_agent]

    def blocked_cards(self) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards
                    if c.action == "Blocked" and not c.assigned_agent]

    def detect_wip_deadlock(self) -> str:
        """Detect WIP deadlock conditions. Returns diagnostic string or '' if no deadlock.

        A WIP deadlock occurs when work exists but no agent can pick it because:
        - A WIP-limited stage is full AND all its cards have unmet dependencies
        - The stages feeding those dependencies cannot be processed due to WIP constraints
        """
        with self._lock:
            non_done = [c for c in self._cards if c.stage != "8_Done"]
            if not non_done:
                return ""
            # Check if ANY card is assignable (not assigned, correct action, deps met)
            assignable = [c for c in non_done if not c.assigned_agent]
            if not assignable:
                return ""  # cards exist but all assigned — not a deadlock, just busy

            # Check Todo: full + all cards have unmet deps
            done_ids = {c.id for c in self._cards if c.stage == "8_Done"}
            todo = [c for c in self._cards if c.stage == "3_Todo"]
            todo_limit = self._wip_limits.get("3_Todo", 999)
            todo_full = len(todo) >= todo_limit and todo_limit < 999

            if todo_full and todo:
                todo_all_blocked = all(
                    any(dep not in done_ids for dep in c.dependencies)
                    for c in todo if c.dependencies
                )
                # Also check: are there cards WITHOUT deps that could move?
                todo_no_deps = [c for c in todo if not c.dependencies and not c.assigned_agent]
                if todo_all_blocked and not todo_no_deps:
                    # Find which Estimate cards are the blocking deps
                    estimate = [c for c in self._cards if c.stage == "2_Estimate"]
                    needed_deps = set()
                    for c in todo:
                        for dep in c.dependencies:
                            if dep not in done_ids:
                                needed_deps.add(dep)
                    blocking_estimate = [c for c in estimate if c.id in needed_deps]
                    if blocking_estimate:
                        blocked_ids = ", ".join(c.id for c in blocking_estimate[:5])
                        todo_ids = ", ".join(c.id for c in todo[:5])
                        return (
                            f"WIP deadlock: Todo full ({len(todo)}/{todo_limit}) with all deps unmet. "
                            f"Blocked by Estimate cards: [{blocked_ids}]. "
                            f"Todo cards waiting: [{todo_ids}]"
                        )

            # Check broader starvation: Coding/Review/Testing all empty, no work can be pulled
            coding = [c for c in self._cards if c.stage == "4_Coding"]
            review = [c for c in self._cards if c.stage == "5_Review"]
            testing = [c for c in self._cards if c.stage == "6_Testing"]
            handoff = [c for c in self._cards if c.stage == "7_Handoff"]
            active_work = coding + review + testing + handoff
            if not active_work and todo_full:
                return (
                    f"Pipeline starvation: Coding/Review/Testing/Handoff all empty, "
                    f"Todo full ({len(todo)}/{todo_limit}) — work cannot flow"
                )

            # Check circular dependencies
            circular = self._detect_circular_deps(non_done, done_ids)
            if circular:
                return circular

            # Check cards stuck too long in stage (>45 min without updated_at change)
            stuck = self._detect_stuck_cards(non_done)
            if stuck:
                return stuck

            return ""

    def _detect_circular_deps(self, cards: list["KanbanCard"], done_ids: set[str]) -> str:
        """Detect circular dependency chains among active cards."""
        card_ids = {c.id for c in cards}
        dep_graph: dict[str, list[str]] = {}
        for c in cards:
            active_deps = [d for d in c.dependencies if d in card_ids and d not in done_ids]
            if active_deps:
                dep_graph[c.id] = active_deps

        # DFS cycle detection
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {cid: WHITE for cid in dep_graph}
        cycle_path: list[str] = []

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for dep in dep_graph.get(node, []):
                if dep not in color:
                    continue
                if color[dep] == GRAY:
                    cycle_path.append(dep)
                    cycle_path.append(node)
                    return True
                if color[dep] == WHITE and dfs(dep):
                    return True
            color[node] = BLACK
            return False

        for cid in dep_graph:
            if color.get(cid, WHITE) == WHITE:
                if dfs(cid):
                    ids = " → ".join(cycle_path[:5])
                    return f"Circular dependency detected: {ids}. Cards can never unblock."
        return ""

    def _detect_stuck_cards(self, cards: list["KanbanCard"], threshold_minutes: int = 45) -> str:
        """Detect cards stuck in a non-Done stage for too long."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        stuck: list[str] = []
        for c in cards:
            if c.assigned_agent:
                continue  # currently being worked on
            if not c.updated_at:
                continue
            try:
                ts = datetime.fromisoformat(c.updated_at.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                elapsed_min = (now - ts).total_seconds() / 60
                if elapsed_min > threshold_minutes:
                    stuck.append(f"{c.id} ({c.stage}, {int(elapsed_min)}m idle)")
            except Exception:
                continue
        if stuck:
            return f"Cards stuck without progress: {', '.join(stuck[:5])}"
        return ""

    def has_unmet_dependencies(self, card: KanbanCard) -> bool:
        if not card.dependencies:
            return False
        with self._lock:
            done_ids = {c.id for c in self._cards if c.stage == "8_Done"}
        return any(dep not in done_ids for dep in card.dependencies)

    # ── Card operations ─────────────────────────────────────────

    def move_card(self, card: KanbanCard, new_stage: str, *, allow_backward: bool = False,
                  reason: str = "") -> None:
        old_stage = card.stage
        if not allow_backward and STAGE_ORDER.get(new_stage, -1) <= STAGE_ORDER.get(old_stage, -1):
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
                _logger.debug("on_move callback failed for %s", card.id, exc_info=True)

    def save_card(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        card.touch()
        card.refresh_roi()
        write_card(card)
        if old_action and old_action != card.action and self.on_action_change:
            try:
                self.on_action_change(card.id, old_action, card.action, role)
            except Exception:
                _logger.debug("on_action_change callback failed for %s", card.id, exc_info=True)

    def assign_agent(self, card: KanbanCard, agent_id: str) -> None:
        with self._lock:
            card.assigned_agent = agent_id
            card.touch()
            write_card(card)

    def release_agent(self, card: KanbanCard) -> None:
        with self._lock:
            card.assigned_agent = ""
            card.touch()
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
        from .kanban_card import KanbanCard as KC, new_card_body, write_card
        from datetime import datetime, timezone
        card = KC(
            id=card_id, title=title, stage="1_Inbox", action="Product",
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            body=new_card_body(),
        )
        inbox_dir = self._tasks_dir / "1_Inbox"
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
        stage: str = "4_Coding",
        action: str = "Coding",
        cos_justification: str = "",
    ) -> KanbanCard:
        """Create an expedite card directly at the given stage, bypassing inbox."""
        from .kanban_card import KanbanCard as KC, write_card
        from datetime import datetime, timezone
        card = KC(
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
