#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports for tasks.completion: external services injected from composition root."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class NotifyPort(Protocol):
    """Outbound notification channel (e.g. Telegram)."""

    def send(self, message: str) -> None: ...


@runtime_checkable
class BacklogQueryPort(Protocol):
    """Queries backlog state referenced by a task-runtime payload file."""

    def is_task_done(self, task_path: Path) -> bool: ...


class NoopNotify:
    """NotifyPort that silently swallows messages — safe default for tests."""

    def send(self, message: str) -> None:
        return None
