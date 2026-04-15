#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Production adapter for ProcessLifecyclePort.

Tonkik facade over psutil-backed utilities in process.py and process_groups.py.
Lives in infra/ so business code can depend on the port (tasks/ports.py)
instead of importing concrete process helpers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .process import (
    ORPHAN_SWEEP_COMMAND_MARKERS,
    build_process_tree,
    is_pid_alive,
    kill_orphan_project_processes,
    kill_process_tree,
)
from .process_groups import kill_own_process_group, terminate_process_group


class SubprocessProcessLifecycle:
    """Default ProcessLifecyclePort implementation backed by os/psutil utilities."""

    def is_alive(self, pid: int) -> bool:
        return is_pid_alive(pid)

    def kill_own_group(self) -> None:
        kill_own_process_group()

    def terminate_group(self, pgid: Optional[int], log_path: Path, label: str) -> bool:
        return terminate_process_group(pgid, log_path, label)

    def build_tree(self, root_pid: int) -> list[int]:
        return build_process_tree(root_pid)

    def kill_tree(self, root_pid: Optional[int], log_path: Path, label: str) -> None:
        kill_process_tree(root_pid, log_path, label)

    def sweep_orphans(
        self,
        workspace: str,
        log_path: Path,
        label: str,
        *,
        started_after: Optional[float] = None,
        run_token: Optional[str] = None,
    ) -> list[int]:
        return kill_orphan_project_processes(
            workspace,
            log_path,
            label,
            started_after=started_after,
            command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
            run_token=run_token,
        )
