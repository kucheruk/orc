#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""No-op ProcessLifecyclePort + StatePathsPort + TaskStateWriter for tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


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


class FakeStateWriter:
    """Test double for TaskStateWriter — performs real atomic-ish writes for integration scenarios."""

    def __init__(self) -> None:
        self.deleted_runtime_paths: list[Path] = []

    def write_json(self, path: Path, payload: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=ensure_ascii, indent=indent), encoding="utf-8")

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)

    def delete_runtime_state(self, task_path: Path, log_path: Path, *, reason: str) -> bool:
        runtime = task_path.with_name("orc-task-runtime.json")
        self.deleted_runtime_paths.append(runtime)
        if runtime.exists():
            runtime.unlink()
            return True
        return False

    def init_runtime_state(self, task_path: Path, task_id: str) -> Path:
        runtime = task_path.with_name("orc-task-runtime.json")
        runtime.parent.mkdir(parents=True, exist_ok=True)
        runtime.write_text(
            json.dumps({"version": 1, "task_id": task_id, "active_seconds": 0.0}),
            encoding="utf-8",
        )
        return runtime

    def read_runtime_payload(self, task_path: Path) -> dict:
        runtime = task_path.with_name("orc-task-runtime.json")
        if not runtime.exists():
            return {}
        try:
            payload = json.loads(runtime.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}


class FakeStatePaths:
    """Test double for StatePathsPort — derives paths under tmpdir/.orc."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def active_task(self, workdir: str) -> Path:
        return Path(workdir) / ".cursor" / "orc-task.json"

    def tmp_dir(self, workdir: str) -> Path:
        return Path(workdir) / ".orc" / "tmp"

    def stats(self, workdir: str) -> Path:
        return Path(workdir) / ".orc" / "analytics" / "stats.json"

    def run_root(self, workdir: str, name: str = "backlog-run") -> Path:
        return Path(workdir) / ".orc" / "runs" / name
