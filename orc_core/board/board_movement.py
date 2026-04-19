#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Move cards across stages: enforce WIP + direction rules, persist, fire listeners."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from .board_listeners import BoardListenerBus
from .card_repository import CardRepository
from .kanban_card import KanbanCard
from .kanban_card_serializer import card_to_markdown
from .movement_rules import resolve_deferred_target
from .stage_constants import STAGE_ORDER
from .wip_manager import WIPManager

_logger = logging.getLogger(__name__)

CardsView = Callable[[], list[KanbanCard]]


class BoardMovementService:
    """Atomic stage transitions with WIP check, filesystem move, and rollback."""

    def __init__(
        self,
        tasks_dir: Path,
        *,
        repo: CardRepository,
        wip: WIPManager,
        cards_view: CardsView,
        lock: threading.RLock,
        listeners: BoardListenerBus,
    ) -> None:
        self._tasks_dir = tasks_dir
        self._repo = repo
        self._wip = wip
        self._cards_view = cards_view
        self._lock = lock
        self._listeners = listeners

    def move_card(self, card: KanbanCard, new_stage: str, *,
                  allow_backward: bool = False, reason: str = "") -> None:
        old_stage = card.stage
        if not card.can_move_to(new_stage, allow_backward=allow_backward):
            raise ValueError(
                f"Cannot move card {card.id} from {old_stage} to {new_stage} (must move right)"
            )

        old_path = card.file_path
        if old_path is None:
            raise ValueError(f"Card {card.id} has no file_path")

        new_dir = self._tasks_dir / new_stage

        with self._lock:
            # Re-check WIP inside the lock to avoid TOCTOU race
            count = sum(1 for c in self._cards_view() if c.stage == new_stage)
            self._wip.check_wip_for_move(new_stage, count)
            new_path = self._repo.move_card_file(old_path, new_dir)
            old_updated_at = card.updated_at
            old_state_version = card.state_version
            try:
                card.stage = new_stage
                card.file_path = new_path
                card.touch()
                card.advance_state_version()
                self._repo.write_card_text(new_path, card_to_markdown(card))
            except Exception:
                try:
                    self._repo.move_card_file(new_path, old_path.parent)
                except Exception:
                    _logger.error("rollback move_card_file failed for %s", card.id, exc_info=True)
                card.stage = old_stage
                card.file_path = old_path
                card.updated_at = old_updated_at
                card.state_version = old_state_version
                raise

        self._listeners.fire_move(card.id, old_stage, new_stage, reason)

    def apply_deferred_moves(self) -> None:
        """Move cards whose action doesn't match their stage (stuck after restart)."""
        for card in list(self._cards_view()):
            if card.assigned_agent:
                continue
            target = resolve_deferred_target(card.stage, card.action)
            if target and self._has_wip_room(target):
                _logger.info("Deferred move: %s %s → %s (action=%s)",
                             card.id, card.stage, target, card.action)
                is_backward = STAGE_ORDER.get(target, 0) < STAGE_ORDER.get(card.stage, 0)
                self.move_card(card, target, allow_backward=is_backward,
                               reason=f"deferred: {card.action}")

    def _has_wip_room(self, stage: str) -> bool:
        count = sum(1 for c in self._cards_view() if c.stage == stage)
        return self._wip.has_wip_room(stage, count)
