#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional

from .task_types import Task

if TYPE_CHECKING:
    from .monitor_types import MonitorSnapshot

from .git_types import WorktreeSession


class SlotStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    CLOSING = "closing"
    CLOSED = "closed"


# ── Timing constants ────────────────────────────────────────────

MAX_SESSIONS = 4
STAGGER_DELAY_SECONDS = 5.0
MANAGER_POLL_SECONDS = 0.5
INTER_TASK_PAUSE_SECONDS = 2.0
SHUTDOWN_JOIN_TIMEOUT_SECONDS = 15.0

# ── Rate limit constants ────────────────────────────────────────

RATE_LIMIT_MAX_RETRIES = 3
RATE_LIMIT_BASE_BACKOFF_SECONDS = 30.0
RATE_LIMIT_MAX_BACKOFF_SECONDS = 240.0

# ── Error truncation constants ─────────────────────────────────

TRACEBACK_TRUNCATE = 2000
ERROR_TRUNCATE = 500
REASON_TRUNCATE = 200
CONFLICT_ERROR_TRUNCATE = 300


# ── Session slot ─────────────────────────────────────────────────

@dataclass
class SessionSlot:
    session_id: str
    task: Optional[Task] = None
    worktree: Optional[WorktreeSession] = None
    status: SlotStatus = SlotStatus.IDLE
    thread: Optional[threading.Thread] = None
    last_snapshot: Optional[MonitorSnapshot] = None
    error: str = ""
    crash_traceback: str = ""
    role: str = ""

    @property
    def is_active(self) -> bool:
        return self.status in (SlotStatus.RUNNING, SlotStatus.CLOSING)

    def assign_task(self, task: Task) -> None:
        self.task = task

    def clear_task(self) -> None:
        self.task = None

    def mark_crashed(self, exc: BaseException, traceback_text: str = "") -> None:
        self.crash_traceback = traceback_text[:TRACEBACK_TRUNCATE]
        self.error = f"crashed:{type(exc).__name__}"


@dataclass
class TaskContext:
    """Bundles slot + task + worktree + workdir for passing between session methods."""
    slot: SessionSlot
    task: "Task"
    worktree: Optional[WorktreeSession] = None

    @property
    def workdir(self) -> str:
        return self.worktree.worktree_path if self.worktree else ""

    @property
    def session_id(self) -> str:
        return self.slot.session_id

    @property
    def task_id(self) -> str:
        return self.task.task_id


# ── Session ID generator ─────────────────────────────────────────

_NEXT_COUNTER = 0
_COUNTER_LOCK = threading.Lock()


def next_session_id() -> str:
    global _NEXT_COUNTER
    with _COUNTER_LOCK:
        _NEXT_COUNTER += 1
        return f"s{_NEXT_COUNTER}"
