#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import os
import sys
from pathlib import Path


def _default_state_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "orc"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "orc"
    return Path.home() / ".local" / "state" / "orc"


def resolve_state_root() -> Path:
    raw = str(os.environ.get("ORC_STATE_ROOT") or "").strip()
    root = Path(raw).expanduser() if raw else _default_state_root()
    return root.resolve()


def repo_key(workdir: str) -> str:
    resolved = str(Path(workdir).resolve())
    digest = hashlib.sha1(resolved.encode("utf-8"), usedforsecurity=False).hexdigest()
    return digest[:16]


def _repo_root(workdir: str) -> Path:
    return resolve_state_root() / "repos" / repo_key(workdir)


def config_dir() -> Path:
    return resolve_state_root() / "config"


def runtime_dir() -> Path:
    return resolve_state_root() / "runtime"


def repo_data_dir(workdir: str) -> Path:
    return _repo_root(workdir)


def repo_logs_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "logs"


def repo_prompts_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "prompts"


def repo_raw_stream_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "raw-stream"


def repo_analytics_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "analytics"


def sessions_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "sessions"


def worktree_registry_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "worktrees"


def worktrees_root(workdir: str) -> Path:
    return resolve_state_root() / "worktrees" / repo_key(workdir)


def artifacts_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "artifacts"


def active_task_path(workdir: str) -> Path:
    return _repo_root(workdir) / "active-task.json"


def task_runtime_path(workdir: str) -> Path:
    return _repo_root(workdir) / "active-task-runtime.json"


def active_session_path(workdir: str) -> Path:
    return _repo_root(workdir) / "active-session.json"


def session_path(workdir: str, session_id: str) -> Path:
    return sessions_dir(workdir) / f"{session_id}.json"


def worktree_record_path(workdir: str, session_id: str) -> Path:
    return worktree_registry_dir(workdir) / f"{session_id}.json"


def stats_path(workdir: str) -> Path:
    return repo_analytics_dir(workdir) / "stats.json"


def metrics_path(workdir: str) -> Path:
    return runtime_dir() / "metrics" / f"{repo_key(workdir)}.json"


def lock_path(workdir: str) -> Path:
    return runtime_dir() / "locks" / f"{repo_key(workdir)}.lock"


def app_log_path(workdir: str) -> Path:
    return repo_logs_dir(workdir) / "orc.log"


def hook_log_path(workdir: str) -> Path:
    return repo_logs_dir(workdir) / "orc-hook.log"


def run_root(workdir: str, name: str = "backlog-run") -> Path:
    return _repo_root(workdir) / "runs" / name


def tmp_dir(workdir: str) -> Path:
    return _repo_root(workdir) / "tmp"


def model_selection_path(workdir: str = "") -> Path:
    if str(workdir or "").strip():
        return _repo_root(workdir) / "config" / "model-selection.json"
    return config_dir() / "model-selection.json"


def role_settings_path(workdir: str = "") -> Path:
    if str(workdir or "").strip():
        return _repo_root(workdir) / "config" / "role-settings.json"
    return config_dir() / "role-settings.json"


def telegram_config_path() -> Path:
    return config_dir() / "telegram.json"


def cursor_task_shim_path(workdir: str) -> Path:
    return Path(workdir) / ".cursor" / "orc-task.json"


def parallel_session_dir(workdir: str, session_id: str) -> Path:
    return _repo_root(workdir) / "parallel" / session_id


def parallel_task_path(workdir: str, session_id: str) -> Path:
    return parallel_session_dir(workdir, session_id) / "active-task.json"


def parallel_runtime_path(workdir: str, session_id: str) -> Path:
    return parallel_session_dir(workdir, session_id) / "active-task-runtime.json"


def integration_report_path(workdir: str, session_id: str, task_id: str) -> Path:
    return _repo_root(workdir) / "integration-reports" / f"{session_id}__{task_id}.json"


def kanban_state_path(workdir: str) -> Path:
    return _repo_root(workdir) / "kanban-state.json"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

