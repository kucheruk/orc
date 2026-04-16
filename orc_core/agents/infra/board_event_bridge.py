#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bridge between KanbanBoard lifecycle events and TUI publisher + state persistence."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from ...board.kanban_distributor import KanbanDistributor
from ...board.stage_constants import STAGE_SHORT_NAMES
from ...git.project_hooks import fire_hooks
from .publisher import KanbanPublisher
from ..session.state_persistence import save_kanban_state

if TYPE_CHECKING:
    from ..session.pool import SessionPool
    from ...tasks.completion.outcomes import TaskOutcomeTracker


class BoardEventBridge:
    """Wires KanbanBoard → publisher (TUI events) and persists outcomes state."""

    _MIN_PUBLISH_INTERVAL_SECONDS = 1.5

    def __init__(
        self,
        *,
        workdir: str,
        distributor: KanbanDistributor,
        publisher: KanbanPublisher,
        outcomes: "TaskOutcomeTracker",
        pool: "SessionPool",
    ) -> None:
        self._workdir = workdir
        self._distributor = distributor
        self._publisher = publisher
        self._outcomes = outcomes
        self._pool = pool
        self._last_board_publish_at = 0.0

    def wire(self) -> None:
        """Install move/action-change listeners on the board."""
        board = self._distributor.board

        def _on_move(cid: str, frm: str, to: str, reason: str) -> None:
            self._publisher.log_move(cid, frm, to, reason)
            card = board.card_by_id(cid)
            fire_hooks(self._workdir, "on_move", {
                "ORC_CARD_ID": cid,
                "ORC_CARD_TITLE": card.title if card else "",
                "ORC_FROM_STAGE": STAGE_SHORT_NAMES.get(frm, frm),
                "ORC_TO_STAGE": STAGE_SHORT_NAMES.get(to, to),
                "ORC_REASON": reason,
            })

        board.on_move(_on_move)
        board.on_action_change(
            lambda cid, old, new, role: self._publisher.log_action_change(cid, old, new, role)
        )

    def publish_board_state(self) -> None:
        """Refresh board, push snapshot to TUI, persist outcomes if dirty."""
        now = time.time()
        should_publish = (now - self._last_board_publish_at) >= self._MIN_PUBLISH_INTERVAL_SECONDS
        if should_publish:
            self._distributor.refresh()
            self._publisher.publish_board(self._distributor.board, self._pool.session_snapshots)
            self._last_board_publish_at = now
        if self._outcomes.is_dirty():
            snapshot = self._outcomes.state_snapshot()
            save_kanban_state(
                self._workdir,
                snapshot["card_fail_counts"],
                snapshot["arbitrated_at_loop"],
                snapshot["applied_result_runs"],
            )
            self._outcomes.clear_dirty()
