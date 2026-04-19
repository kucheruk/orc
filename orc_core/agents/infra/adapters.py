#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Protocol adapter classes that bridge extracted services to Runner protocols.

Adapters depend on the underlying services directly (not on
KanbanSessionManager), so they can be constructed in the composition
root before the session manager exists.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Mapping

if TYPE_CHECKING:
    from ..session.types import SessionSlot
    from ...tasks.completion.outcomes import TaskOutcomeTracker
    from .directive_queue import DirectiveQueue
    from .notification_service import NotificationService
    from .request_factory import KanbanRequestFactory
    from ..session.pool import SessionPool


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
    __slots__ = ("_svc",)

    def __init__(self, svc: NotificationService) -> None:
        self._svc = svc

    def notify_card_blocked(self, card_id: str, count: int, reason: str) -> None:
        self._svc.notify_card_blocked(card_id, count, reason)

    def notify_escalation(self, card_id: str, title: str, stage: str, loop_count: int) -> None:
        self._svc.notify_escalation(card_id, title, stage, loop_count)

    def notify_cycle_autounblock(self, from_id: str, to_id: str, decomposition_id: str) -> None:
        self._svc.notify_cycle_autounblock(from_id, to_id, decomposition_id)

    def notify_stale_assignments_released(self, count: int) -> None:
        self._svc.notify_stale_assignments_released(count)

    def notify_completion(self, card, role, old_stage, old_action, old_cos, elapsed) -> None:
        self._svc.notify_completion(card, role, old_stage, old_action, old_cos, elapsed)


class StateManagerAdapter:
    __slots__ = ("_factory", "_outcomes")

    def __init__(self, factory: KanbanRequestFactory, outcomes: TaskOutcomeTracker) -> None:
        self._factory = factory
        self._outcomes = outcomes

    def mark_dirty(self) -> None:
        self._outcomes.mark_dirty()

    def make_request(
        self,
        task,
        prompt: str,
        workdir: str,
        session_id: str,
        commit_phase: bool,
        ttl: float,
        agent_env: Mapping[str, str] | None = None,
    ):
        return self._factory.make(
            task=task,
            prompt=prompt,
            workdir=workdir,
            session_id=session_id,
            commit_phase=commit_phase,
            task_ttl=ttl,
            agent_env=agent_env,
        )


class DirectiveAdapter:
    __slots__ = ("_queue",)

    def __init__(self, queue: DirectiveQueue) -> None:
        self._queue = queue

    def pop_directive(self):
        return self._queue.pop()


class SessionControllerAdapter:
    """Implements IncidentSessionController — adds/removes worker sessions.

    Takes the pool and the worker-thread target directly so construction
    never needs a back-reference to KanbanSessionManager.
    """

    __slots__ = ("_pool", "_worker_target")

    def __init__(self, pool: SessionPool, worker_target: Callable[["SessionSlot"], None]) -> None:
        self._pool = pool
        self._worker_target = worker_target

    def add_session(self):
        return self._pool.request_add(target=self._worker_target)

    def remove_session(self, session_id: str) -> None:
        self._pool.request_remove(session_id)
