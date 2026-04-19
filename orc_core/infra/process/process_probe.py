#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concrete adapter for tasks.ports.ProcessProbe — OS-backed implementation."""
from __future__ import annotations

import psutil

from .process import is_pid_alive


class OsProcessProbe:
    """Process liveness probe backed by os.kill(pid, 0) and psutil for child count."""

    def is_alive(self, pid: int) -> bool:
        return is_pid_alive(pid)

    def active_children_count(self, pid: int) -> int:
        if not isinstance(pid, int) or pid <= 0:
            return 0
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
            return 0
        active = 0
        for child in children:
            try:
                if child.status() != psutil.STATUS_ZOMBIE:
                    active += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                continue
        return active


DEFAULT_PROCESS_PROBE = OsProcessProbe()
