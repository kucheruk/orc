#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Registry of polymorphic teamlead action handlers.

Each action type is a class implementing ``execute(ctx)`` and registers
itself under a string key via ``@register_action("...")`` at import time.
The dispatcher looks up handlers here by action type.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ...infra.publisher import KanbanPublisher
    from ....board.kanban_board import KanbanBoard


@dataclass
class ActionContext:
    """Bundle of dependencies each ActionHandler needs to run."""
    board: "KanbanBoard"
    params: dict[str, Any]
    reason: str
    publisher: "KanbanPublisher"
    log_path: Path | None = None
    notifier: Any = None  # RunnerNotifier; optional for actions that ping operator


class ActionHandler(Protocol):
    """Port for executing one teamlead action type."""
    def execute(self, ctx: ActionContext) -> None: ...


_REGISTRY: dict[str, ActionHandler] = {}


def register_action(name: str):
    """Register an ActionHandler class under a string action type."""
    def decorator(cls: type) -> type:
        _REGISTRY[name] = cls()
        return cls
    return decorator


def resolve(action_type: str) -> ActionHandler:
    handler = _REGISTRY.get(action_type)
    if handler is None:
        raise ValueError(f"Unknown action type: {action_type}")
    return handler
