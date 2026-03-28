#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Distributes backlog tasks across parallel session queues using AI conflict analysis."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from .logging import log_event
from .session_types import next_session_id
from .task_analyzer import TaskAnalyzer
from .task_source import MarkdownTaskSource, Task

if TYPE_CHECKING:
    from .backend import Backend

TaskSourceFactory = Callable[[Path], MarkdownTaskSource]


class TaskDistributor:
    """Thread-safe task assignment with optional AI-driven conflict analysis."""

    def __init__(
        self,
        *,
        backlog_path: Path,
        task_source_factory: TaskSourceFactory = MarkdownTaskSource,
        single_mode: bool = False,
        selected_task_id: str = "",
        backend: Optional["Backend"] = None,
    ) -> None:
        self._backlog_path = backlog_path
        self._task_source_factory = task_source_factory
        self._single_mode = single_mode
        self._selected_task_id = selected_task_id
        self._backend = backend

        self._lock = threading.Lock()
        self._assigned_ids: set[str] = set()
        self._completed_ids: set[str] = set()
        self._queues: dict[str, list[str]] = {}

    def run_analysis(
        self,
        *,
        workdir: str,
        model: str,
        log_path: Path,
        max_sessions: int,
        existing_session_ids: list[str],
    ) -> None:
        with self._lock:
            open_tasks = self._unassigned_open_tasks()
        if len(open_tasks) <= 1:
            return

        analyzer = TaskAnalyzer(workdir=workdir, model=model, log_path=log_path, backend=self._backend)
        distribution = analyzer.analyze(open_tasks, max_sessions)

        log_event(log_path, "INFO", "task distribution computed",
                  conflicts=len(distribution.conflicts),
                  queues={k: len(v) for k, v in distribution.queues.items()})

        all_sids = list(existing_session_ids)
        while len(all_sids) < max_sessions:
            all_sids.append(next_session_id())

        with self._lock:
            self._queues.clear()
            for queue_idx, task_ids in distribution.queues.items():
                if queue_idx < len(all_sids):
                    self._queues[all_sids[queue_idx]] = task_ids

    def pick_next_task(self, session_id: str = "") -> Optional[Task]:
        with self._lock:
            return self._pick_unlocked(session_id)

    def release_task(self, task_id: str) -> None:
        with self._lock:
            self._assigned_ids.discard(task_id)

    def mark_completed(self, task_id: str) -> None:
        with self._lock:
            self._completed_ids.add(task_id)

    def has_remaining_tasks(self) -> bool:
        with self._lock:
            return bool(self._unassigned_open_tasks())

    @property
    def is_single_mode(self) -> bool:
        return self._single_mode

    def open_task_count(self) -> int:
        with self._lock:
            return len(self._unassigned_open_tasks())

    def has_queued_tasks(self, session_id: str) -> bool:
        with self._lock:
            return bool(self._queues.get(session_id))

    def get_progress(self) -> tuple[int, int, int]:
        """Returns (done, in_progress, total).

        done includes tasks marked [x] in the backlog PLUS tasks completed
        during this run that may not yet be reflected in the base backlog
        (because cherry-pick goes to master, not the working copy).
        """
        with self._lock:
            source = self._task_source_factory(self._backlog_path)
            tasks = source.list_tasks()
            total = len(tasks)
            backlog_done = {t.task_id for t in tasks if t.done}
            done = len(backlog_done | self._completed_ids)
            in_progress = len(self._assigned_ids - self._completed_ids)
            return done, in_progress, total

    # ── Private ──────────────────────────────────────────────────

    def _pick_unlocked(self, session_id: str) -> Optional[Task]:
        source = self._task_source_factory(self._backlog_path)

        if self._single_mode and self._selected_task_id:
            return self._pick_single(source)

        if session_id:
            queued = self._pick_from_queue(source, session_id)
            if queued:
                return queued

        return self._pick_first_open(source)

    def _pick_single(self, source: MarkdownTaskSource) -> Optional[Task]:
        task = source.get_task_by_id(self._selected_task_id)
        if task and not task.done and task.task_id not in self._assigned_ids:
            self._assigned_ids.add(task.task_id)
            return task
        return None

    def _pick_from_queue(self, source: MarkdownTaskSource, session_id: str) -> Optional[Task]:
        queue_ids = self._queues.get(session_id)
        if not queue_ids:
            return None
        while queue_ids:
            next_id = queue_ids.pop(0)
            if next_id in self._assigned_ids:
                continue
            task = source.get_task_by_id(next_id)
            if task and not task.done:
                self._assigned_ids.add(task.task_id)
                return task
        return None

    def _pick_first_open(self, source: MarkdownTaskSource) -> Optional[Task]:
        for task in source.get_open_tasks():
            if task.task_id not in self._assigned_ids:
                self._assigned_ids.add(task.task_id)
                return task
        return None

    def _unassigned_open_tasks(self) -> list[Task]:
        source = self._task_source_factory(self._backlog_path)
        return [t for t in source.get_open_tasks()
                if t.task_id not in self._assigned_ids]
