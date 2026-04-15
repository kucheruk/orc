#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban board: reads cards from folder structure, enforces WIP limits, moves cards."""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Optional

from .clock import Clock, SystemClock
from .card_prioritizer import pick_best as _pick_best
from .card_repository import CardRepository
from .kanban_card import KanbanCard, parse_card
from .stage_constants import STAGES, STAGE_ORDER
from .movement_rules import resolve_deferred_target
from .wip_manager import WIPManager

_logger = logging.getLogger(__name__)


class KanbanBoard:
    """In-memory snapshot of the kanban board backed by the tasks/ folder tree."""

    def __init__(
        self,
        tasks_dir: Path,
        *,
        repo: CardRepository,
        clock: Optional[Clock] = None,
    ) -> None:
        self._tasks_dir = tasks_dir
        self.tasks_dir = tasks_dir
        self.repo: CardRepository = repo
        self.clock: Clock = clock or SystemClock()
        self._lock = threading.RLock()
        self._cards: list[KanbanCard] = []
        self._wip = WIPManager()
        self._card_locks: dict[str, threading.Lock] = {}
        self._last_stage_mtimes: dict[str, float] = {}
        self._move_listeners: list[Callable[[str, str, str, str], None]] = []
        self._action_change_listeners: list[Callable[[str, str, str, str], None]] = []
        self._parse_errors: list[tuple[str, str]] = []
        self.refresh(force=True)

    # ── Event listeners ────────────────────────────────────────

    def on_move(self, listener: Callable[[str, str, str, str], None]) -> None:
        with self._lock:
            self._move_listeners.append(listener)

    def on_action_change(self, listener: Callable[[str, str, str, str], None]) -> None:
        with self._lock:
            self._action_change_listeners.append(listener)

    # ── State hydration ─────────────────────────────────────────

    def refresh(self, *, force: bool = False) -> None:
        if not force and self._is_fresh():
            return
        with self._lock:
            self._cards = []
            self._parse_errors = []
            self._wip.reset()
            for stage in STAGES:
                stage_dir = self._tasks_dir / stage
                if not stage_dir.is_dir():
                    continue
                self._read_index(stage_dir, stage)
                self._read_cards(stage_dir, stage)
            self._recompute_roi()
            self._last_stage_mtimes = self.repo.scan_stage_mtimes(self._tasks_dir)

    def _is_fresh(self) -> bool:
        """Check if any stage directory has been modified since last refresh."""
        if not self._last_stage_mtimes:
            return False
        return self.repo.scan_stage_mtimes(self._tasks_dir) == self._last_stage_mtimes

    def _read_index(self, stage_dir: Path, stage: str) -> None:
        try:
            data = self.repo.read_index_data(stage_dir)
            if data:
                limit = data.get("wip_limit")
                self._wip.set_limit_from_index(stage, limit)
        except Exception as exc:
            _logger.warning("Failed to read index in %s: %s", stage_dir, exc)

    def _read_cards(self, stage_dir: Path, stage: str) -> None:
        for md in self.repo.list_card_files(stage_dir):
            try:
                text = self.repo.read_card_text(md)
                card = parse_card(text, file_path=md)
                card.stage = stage  # trust folder over frontmatter
                self._cards.append(card)
            except Exception as exc:
                _logger.error("CARD LOST — failed to parse %s: %s", md, exc, exc_info=True)
                self._parse_errors.append((str(md), str(exc)))

    def _recompute_roi(self) -> None:
        for card in self._cards:
            card.refresh_roi()

    @property
    def parse_errors(self) -> list[tuple[str, str]]:
        """Files that failed to parse during last refresh — (path, error)."""
        with self._lock:
            return list(self._parse_errors)

    # ── Per-card locking ──────────────────────────────────────────

    def _get_card_lock(self, card_id: str) -> threading.Lock:
        """Return a per-card lock, creating it lazily. Thread-safe."""
        with self._lock:
            if card_id not in self._card_locks:
                self._card_locks[card_id] = threading.Lock()
            return self._card_locks[card_id]

    @contextmanager
    def locked_card(self, card_id: str) -> Iterator[None]:
        """Serialize mutations to a single card across threads.

        Callers enter this block before any read-modify-write cycle that
        must not interleave with another agent touching the same card.
        The underlying Lock is an internal detail.
        """
        lock = self._get_card_lock(card_id)
        with lock:
            yield

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
        return self._wip.wip_limit(stage)

    def has_wip_room(self, stage: str) -> bool:
        return self._wip.has_wip_room(stage, self.stage_count(stage))

    def wip_free(self, stage: str) -> int:
        return self._wip.wip_free(stage, self.stage_count(stage))

    def looping_cards(self, threshold: int = 2) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards
                    if c.is_looping(threshold) and not c.is_assigned
                    and not c.is_done]

    def blocked_cards(self) -> list[KanbanCard]:
        with self._lock:
            return [c for c in self._cards
                    if c.is_blocked and not c.is_assigned
                    and not c.is_done]

    def _apply_deferred_moves(self) -> None:
        """Move cards whose action doesn't match their stage (stuck after restart)."""
        for card in list(self._cards):
            if card.assigned_agent:
                continue
            target = resolve_deferred_target(card.stage, card.action)
            if target and self.has_wip_room(target):
                _logger.info("Deferred move: %s %s → %s (action=%s)",
                             card.id, card.stage, target, card.action)
                is_backward = STAGE_ORDER.get(target, 0) < STAGE_ORDER.get(card.stage, 0)
                self.move_card(card, target, allow_backward=is_backward,
                               reason=f"deferred: {card.action}")

    def detect_wip_deadlock(self) -> str:
        """Detect WIP deadlock conditions. Returns diagnostic string or '' if healthy."""
        with self._lock:
            return self._wip.detect_deadlock(list(self._cards))

    def has_unmet_dependencies(self, card: KanbanCard) -> bool:
        if not card.dependencies:
            return False
        with self._lock:
            done_ids = {c.id for c in self._cards if c.is_done}
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

        with self._lock:
            # Re-check WIP inside the lock to avoid TOCTOU race
            count = sum(1 for c in self._cards if c.stage == new_stage)
            self._wip.check_wip_for_move(new_stage, count)
            new_path = self.repo.move_card_file(old_path, new_dir)
            try:
                card.stage = new_stage
                card.file_path = new_path
                card.touch()
                self.repo.write_card_text(new_path, card.to_markdown())
            except Exception:
                # Rollback: move file back, restore card state
                try:
                    self.repo.move_card_file(new_path, old_path.parent)
                except Exception:
                    _logger.error("rollback move_card_file failed for %s", card.id, exc_info=True)
                card.stage = old_stage
                card.file_path = old_path
                raise
            listeners = list(self._move_listeners)

        for listener in listeners:
            try:
                listener(card.id, old_stage, new_stage, reason)
            except Exception:
                _logger.warning("on_move listener failed for %s", card.id, exc_info=True)

    def save_card(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        with self._lock:
            card.touch()
            card.refresh_roi()
            if card.file_path:
                self.repo.write_card_text(card.file_path, card.to_markdown())
        if old_action and old_action != card.action:
            with self._lock:
                listeners = list(self._action_change_listeners)
            for listener in listeners:
                try:
                    listener(card.id, old_action, card.action, role)
                except Exception:
                    _logger.warning("on_action_change listener failed for %s", card.id, exc_info=True)

    def assign_agent(self, card: KanbanCard, agent_id: str) -> None:
        with self._lock:
            card.assign(agent_id)
            if card.file_path:
                self.repo.write_card_text(card.file_path, card.to_markdown())

    def release_agent(self, card: KanbanCard) -> None:
        with self._lock:
            card.release()
            if card.file_path:
                self.repo.write_card_text(card.file_path, card.to_markdown())

    def set_wip_limit(self, stage: str, limit: int) -> None:
        """Write WIP limit to _index.md and update in-memory cache."""
        with self._lock:
            self._wip.set_limit(self._tasks_dir, stage, limit, repo=self.repo)

    # ── Sorting ─────────────────────────────────────────────────

    def pick_best(self, stage: str, action: str, *, check_deps: bool = True) -> Optional[KanbanCard]:
        candidates = self.cards_with_action(stage, action)
        return _pick_best(
            candidates,
            check_deps=self.has_unmet_dependencies if check_deps else None,
        )

    # ── Board summary (for prompts / TUI) ───────────────────────

    def summary(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for stage in STAGES:
            count = self.stage_count(stage)
            limit = self._wip.wip_limit(stage) if self._wip.wip_limit(stage) != 999 else 0
            result[stage] = {"count": count, "wip_limit": limit}
        return result

    # ── Card registration ───────────────────────────────────────

    def register_card(self, card: KanbanCard) -> None:
        """Attach a pre-built card (persisted by a factory) to the in-memory list."""
        with self._lock:
            self._cards.append(card)

    def next_card_id(self) -> str:
        with self._lock:
            nums = []
            for c in self._cards:
                parts = c.id.rsplit("-", 1)
                if len(parts) == 2 and parts[1].isdigit():
                    nums.append(int(parts[1]))
            next_num = max(nums, default=0) + 1
        return f"TASK-{next_num:03d}"
