#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thin dispatcher: routes each parsed TeamleadAction to its registered handler."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ....log import log_event
from .decision import TeamleadDecision
from .registry import ActionContext, resolve

if TYPE_CHECKING:
    from ...infra.publisher import KanbanPublisher
    from ....board.kanban_board import KanbanBoard

_logger = logging.getLogger(__name__)


def execute_teamlead_actions(
    board: "KanbanBoard",
    decision: TeamleadDecision,
    publisher: "KanbanPublisher",
    log_path: Path,
    notifier=None,
) -> list[str]:
    """Execute parsed actions against the board. Returns list of error strings."""
    errors: list[str] = []
    if decision.summary:
        publisher.emit("teamlead", "", f"[TL] {decision.summary}")

    for action in decision.actions:
        ctx = ActionContext(
            board=board,
            params=action.params,
            reason=action.reason,
            publisher=publisher,
            log_path=log_path,
            notifier=notifier,
        )
        try:
            resolve(action.type).execute(ctx)
            log_event(log_path, "INFO", "teamlead action executed",
                      action_type=action.type, reason=action.reason,
                      params={k: str(v)[:200] for k, v in action.params.items()})
        except Exception as exc:
            msg = f"{action.type}: {exc}"
            errors.append(msg)
            _logger.warning("Teamlead action failed: %s", msg)
            log_event(log_path, "WARN", "teamlead action failed",
                      action_type=action.type, error=str(exc))

    return errors
