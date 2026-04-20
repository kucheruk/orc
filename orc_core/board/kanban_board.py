#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban board facade: wires collaborators, exposes the public board API."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Iterator, Optional

from .board_card_index import BoardCardIndex
from .board_card_persistence import BoardCardPersistence
from .board_hydration import BoardHydration
from .board_listeners import BoardListenerBus
from .board_movement import BoardMovementService
from .board_queries import BoardQueries
from .card_prioritizer import pick_best as _pick_best
from .card_repository import CardRepository
from .clock import Clock, SystemClock
from .kanban_card import KanbanCard
from .wip_manager import WIPManager


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
        self._last_stage_mtimes: dict[str, float] = {}
        self._parse_errors: list[tuple[str, str]] = []
        cards_view = lambda: self._cards
        self._listeners = BoardListenerBus(self._lock)
        self._hydration = BoardHydration(tasks_dir, repo)
        self._index = BoardCardIndex(tasks_dir, cards_view=cards_view, lock=self._lock)
        self._queries = BoardQueries(cards_view=cards_view, wip=self._wip, lock=self._lock)
        self._movement = BoardMovementService(
            tasks_dir, repo=repo, wip=self._wip,
            cards_view=cards_view, lock=self._lock, listeners=self._listeners,
        )
        self._persistence = BoardCardPersistence(
            repo=repo, lock=self._lock, listeners=self._listeners,
        )
        self.refresh(force=True)

    # ── Event listeners ────────────────────────────────────────

    def on_move(self, listener: Callable[[str, str, str, str], None]) -> None:
        self._listeners.on_move(listener)

    def on_action_change(self, listener: Callable[[str, str, str, str], None]) -> None:
        self._listeners.on_action_change(listener)

    # ── State hydration ─────────────────────────────────────────

    def refresh(self, *, force: bool = False) -> None:
        if not force and self._hydration.is_fresh(self._last_stage_mtimes):
            return
        with self._lock:
            result = self._hydration.rebuild(self._wip)
            self._reconcile_cards_in_place(result.cards)
            self._parse_errors = list(result.parse_errors)
            self._last_stage_mtimes = result.stage_mtimes

    def _reconcile_cards_in_place(self, fresh_cards: list[KanbanCard]) -> None:
        """Sync in-memory cards with fresh hydration WITHOUT discarding identity.

        The obvious `self._cards[:] = fresh_cards` also works — until you
        remember that other parts of the runtime hold live references to
        existing card instances (the most common being `card` in
        WorkerAssignmentRunner.execute, captured from the assignment and
        carried across every subsequent call including the post-apply
        _sync_tokens_and_budget). Swapping the list orphans every such
        reference: the orphan keeps its pre-mutation (stage, action,
        file_path, state_version) values while the board moves on.

        The downstream accident played out like this on jeeves 2026-04-20:
          1. apply_card_update_result mutates `current` (identical to the
             single `board._cards[id]` instance at that moment), saves
             action=Coding, and move_cards the file 6_Testing → 4_Coding.
          2. The trailing board.refresh() inside apply swaps _cards with
             freshly-parsed instances — the original `card` reference in
             worker_assignment now points at an orphan holding the stale
             6_Testing/Testing state.
          3. process_completed_task emits `attempt.finish` with the
             orphan's `stage` (6_Testing) instead of the post-apply
             stage (4_Coding), which is how the jeeves logs consistently
             showed "applied" signals with the wrong stage.
          4. _sync_tokens_and_budget(card) calls save_card on the
             orphan. persistence.save reads the orphan's file_path
             (tasks/6_Testing/…), which no longer exists because move
             relocated the file; _peek_state_version returns None, the
             external-edit guard does not fire, and write_text_atomic
             RECREATES tasks/6_Testing/ASSIST-003-C.md from the orphan's
             stale fields (action=Testing, stage=6_Testing) with just
             tokens_spent bumped.
          5. The next hydration sees the same card in two stage
             directories and _dedup_cards keeps the newer updated_at
             (i.e. the orphan's save) and deletes the post-apply copy
             in 4_Coding. Apply's stage change is silently wiped.

        Reconciling in place keeps every live reference pointing at the
        single shared instance for that id, so post-apply code sees the
        post-apply state and the whole chain of stale-path writes
        cannot happen.
        """
        from dataclasses import fields as dataclass_fields
        field_names = [f.name for f in dataclass_fields(KanbanCard)]
        existing: dict[str, KanbanCard] = {c.id: c for c in self._cards}
        reconciled: list[KanbanCard] = []
        for fresh in fresh_cards:
            alive = existing.pop(fresh.id, None)
            if alive is None:
                reconciled.append(fresh)
                continue
            for name in field_names:
                setattr(alive, name, getattr(fresh, name))
            reconciled.append(alive)
        # Cards that vanished from disk (e.g. merged into a parent, deleted
        # by the operator) drop out of _cards entirely; any outside
        # reference becomes semantically orphan but that is unavoidable —
        # the card no longer exists.
        self._cards[:] = reconciled

    @property
    def parse_errors(self) -> list[tuple[str, str]]:
        """Files that failed to parse during last refresh — (path, error)."""
        with self._lock:
            return list(self._parse_errors)

    # ── Per-card locking ──────────────────────────────────────────

    def _get_card_lock(self, card_id: str) -> threading.Lock:
        return self._index.get_card_lock(card_id)

    def locked_card(self, card_id: str) -> Iterator[None]:
        """Serialize mutations to a single card across threads."""
        return self._index.locked_card(card_id)

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
            return [c for c in self._cards
                    if c.stage == stage and c.action == action and not c.assigned_agent]

    def card_by_id(self, card_id: str) -> Optional[KanbanCard]:
        with self._lock:
            return next((c for c in self._cards if c.id == card_id), None)

    def find_card_file(self, card_id: str) -> Optional[Path]:
        """Search all stage directories for a card file by ID."""
        return self._index.find_file(card_id)

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
        return self._queries.looping(threshold)

    def blocked_cards(self) -> list[KanbanCard]:
        return self._queries.blocked()

    def arbitration_cards(self) -> list[KanbanCard]:
        return self._queries.needs_arbitration()

    def detect_wip_deadlock(self) -> str:
        """Detect WIP deadlock conditions. Returns diagnostic string or '' if healthy."""
        with self._lock:
            return self._wip.detect_deadlock(list(self._cards))

    def has_unmet_dependencies(self, card: KanbanCard) -> bool:
        return self._queries.has_unmet_dependencies(card)

    def summary(self) -> dict[str, dict[str, int]]:
        return self._queries.summary()

    # ── Card operations ─────────────────────────────────────────

    def move_card(self, card: KanbanCard, new_stage: str, *, allow_backward: bool = False,
                  reason: str = "") -> None:
        self._movement.move_card(card, new_stage, allow_backward=allow_backward, reason=reason)

    def _apply_deferred_moves(self) -> None:
        self._movement.apply_deferred_moves()

    def save_card(self, card: KanbanCard, *, old_action: str = "", role: str = "") -> None:
        self._persistence.save(card, old_action=old_action, role=role)

    def assign_agent(self, card: KanbanCard, agent_id: str) -> None:
        self._persistence.assign(card, agent_id)

    def release_agent(self, card: KanbanCard) -> None:
        self._persistence.release(card)

    def set_wip_limit(self, stage: str, limit: int) -> None:
        """Write WIP limit to _index.md and update in-memory cache."""
        with self._lock:
            self._wip.set_limit(self._tasks_dir, stage, limit, repo=self.repo)

    def pick_best(self, stage: str, action: str, *, check_deps: bool = True) -> Optional[KanbanCard]:
        candidates = self.cards_with_action(stage, action)
        return _pick_best(
            candidates,
            check_deps=self.has_unmet_dependencies if check_deps else None,
            all_cards=self.cards,
        )

    def register_card(self, card: KanbanCard) -> None:
        """Attach a pre-built card (persisted by a factory) to the in-memory list."""
        self._index.register(card)

    def next_card_id(self) -> str:
        return self._index.next_id()
