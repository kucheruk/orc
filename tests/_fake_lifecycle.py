#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No-op ProcessLifecyclePort for tests — records calls for assertions."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


class FakeLifecycle:
    """Test double for ProcessLifecyclePort. Records all calls; never touches OS."""

    def __init__(self) -> None:
        self.is_alive_calls: list[int] = []
        self.kill_own_group_calls: int = 0
        self.terminate_group_calls: list[tuple[Optional[int], Path, str]] = []
        self.build_tree_calls: list[int] = []
        self.kill_tree_calls: list[tuple[Optional[int], Path, str]] = []
        self.sweep_orphans_calls: list[dict] = []
        self.terminate_group_returns: bool = False

    def is_alive(self, pid: int) -> bool:
        self.is_alive_calls.append(pid)
        return False

    def kill_own_group(self) -> None:
        self.kill_own_group_calls += 1

    def terminate_group(self, pgid: Optional[int], log_path: Path, label: str) -> bool:
        self.terminate_group_calls.append((pgid, log_path, label))
        return self.terminate_group_returns

    def build_tree(self, root_pid: int) -> list[int]:
        self.build_tree_calls.append(root_pid)
        return []

    def kill_tree(self, root_pid: Optional[int], log_path: Path, label: str) -> None:
        self.kill_tree_calls.append((root_pid, log_path, label))

    def sweep_orphans(
        self,
        workspace: str,
        log_path: Path,
        label: str,
        *,
        started_after: Optional[float] = None,
        run_token: Optional[str] = None,
    ) -> list[int]:
        self.sweep_orphans_calls.append({
            "workspace": workspace,
            "log_path": log_path,
            "label": label,
            "started_after": started_after,
            "run_token": run_token,
        })
        return []
