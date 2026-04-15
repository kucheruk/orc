#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concrete adapter for tasks.ports.ProcessProbe — OS-backed implementation."""
from __future__ import annotations

from .process import is_pid_alive


class OsProcessProbe:
    """Process liveness probe backed by os.kill(pid, 0)."""

    def is_alive(self, pid: int) -> bool:
        return is_pid_alive(pid)


DEFAULT_PROCESS_PROBE = OsProcessProbe()
