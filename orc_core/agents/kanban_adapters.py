#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocol adapter classes that bridge KanbanSessionManager to Runner protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .kanban_session_manager import KanbanSessionManager
    from .session_pool import SessionPool


class LifecycleAdapter:
    """Implements RunnerLifecycle by delegating to SessionPool."""

    __slots__ = ("_pool",)

    def __init__(self, pool: SessionPool) -> None:
        self._pool = pool

    def should_continue(self, slot) -> bool:
        return self._pool.should_continue(slot)

    def sleep(self, seconds: float) -> None:
        self._pool.sleep_fn(seconds)


class NotifierAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def send_telegram(self, message: str) -> None:
        self._mgr._send_telegram(message)

    def notify_completion(self, card, role, old_stage, old_action, old_cos, elapsed) -> None:
        self._mgr._notify_completion(card, role, old_stage, old_action, old_cos, elapsed)


class StateManagerAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def mark_dirty(self) -> None:
        self._mgr._mark_state_dirty()

    def make_request(self, task, prompt: str, workdir: str, session_id: str, commit_phase: bool, ttl: float):
        return self._mgr._make_request(task, prompt, workdir, session_id, commit_phase, ttl)


class DirectiveAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def pop_directive(self):
        return self._mgr._pop_directive()


class SessionControllerAdapter:
    __slots__ = ("_mgr",)

    def __init__(self, mgr: KanbanSessionManager) -> None:
        self._mgr = mgr

    def add_session(self):
        return self._mgr.request_add_session()

    def remove_session(self, session_id: str) -> None:
        self._mgr.request_remove_session(session_id)
