#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports owned by the tasks/ domain.

These protocols and DTOs describe what tasks/ needs from the outside world
(monitor snapshots, stream monitors, I/O, process probes, git probes) without
leaking concrete implementations into domain code. Adapters live under infra/,
agents/, git/.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol


# ── Monitor DTOs ────────────────────────────────────────────────────

@dataclass
class MetricsStore:
    tokens_total: Optional[int] = None
    tokens_status: str = "unknown"
    tokens_source: str = "none"
    files_edited: Optional[int] = None
    command_count: int = 0
    total_lines: int = 0
    total_output_chars: int = 0
    input_bytes: int = 0
    output_bytes: int = 0
    git_added: Optional[int] = None
    git_deleted: Optional[int] = None


@dataclass(frozen=True)
class MonitorSnapshot:
    task_id: str
    started_at: float
    progress_done: int
    progress_total: int
    metrics: MetricsStore
    last_event_type: str
    last_event_note: str
    recent_commands: list[str]
    recent_files: list[str]
    recent_events: list[str]
    reasoning_lines: list[str]
    spinner_idx: int
    last_event_at: float
    progress_remaining: int = 0
    progress_in_progress: int = 0
    progress_added_delta: int = 0
    eta_seconds: Optional[float] = None
    live_phase: str = "starting"
    live_status: str = "starting, no messages yet"
    live_since: float = 0.0
    active_tool_call_count: int = 0
    is_subagent_activity: bool = False


# ── Stream monitor protocols (ISP-split) ────────────────────────────

class ProcessProxy(Protocol):
    pid: Optional[int]
    returncode: Optional[int]

    def poll(self) -> Optional[int]: ...


class MonitorMetrics(Protocol):
    """Metrics and stderr tracking — used by status displays and diagnostics."""

    metrics: MetricsStore
    stderr_count: int
    last_stderr_line: str


class MonitorLifecycle(Protocol):
    """Process lifecycle — used by supervisor to manage the agent process."""

    proc: ProcessProxy
    init_pid: Optional[int]
    process_group_id: Optional[int]

    def stop(self) -> None: ...
    def refresh_process_status(self) -> Optional[int]: ...


class ToolCallManager(Protocol):
    """Active tool call management — used by watchdog and stall detection."""

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]: ...
    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]: ...


class StreamMonitorProtocol(
    MonitorMetrics,
    MonitorLifecycle,
    ToolCallManager,
    Protocol,
):
    """Full contract for stream monitors — composes smaller protocols.

    Concrete monitors implement this implicitly (structural subtyping).
    Consumers should depend on the smallest protocol they need.
    """

    last_output_time: float
    started_at: float
    workdir: str
    run_token: str
    ui_followup_prompt: bool
    result_status: Optional[str]

    def maybe_report(self) -> None: ...
    def get_summary_text(self) -> str: ...


# ── I/O ports ───────────────────────────────────────────────────────

class TaskStateWriter(Protocol):
    """Port for persisting task runtime state (json files, runtime markers)."""

    def write_json(self, path: Path, payload: Any, *, ensure_ascii: bool = False, indent: int = 2) -> None: ...

    def write_text(self, path: Path, content: str, *, encoding: str = "utf-8") -> None: ...

    def delete_runtime_state(self, task_path: Path, log_path: Path, *, reason: str) -> bool: ...

    def init_runtime_state(self, task_path: Path, task_id: str) -> Path: ...

    def read_runtime_payload(self, task_path: Path) -> dict: ...


class StatePathsPort(Protocol):
    """Port for ORC state filesystem layout — keeps tasks/ and agents/ free of
    direct infra.io.state_paths imports."""

    def active_task(self, workdir: str) -> Path: ...

    def tmp_dir(self, workdir: str) -> Path: ...

    def stats(self, workdir: str) -> Path: ...

    def run_root(self, workdir: str, name: str = "backlog-run") -> Path: ...


# ── Process ports ───────────────────────────────────────────────────

class ProcessProbe(Protocol):
    """Port for querying process liveness — used by completion checks."""

    def is_alive(self, pid: int) -> bool: ...


class ProcessLifecyclePort(Protocol):
    """Port for OS process lifecycle operations — keeps tasks/ and agents/
    free of direct infra.process imports."""

    def is_alive(self, pid: int) -> bool: ...

    def kill_own_group(self) -> None: ...

    def terminate_group(self, pgid: Optional[int], log_path: Path, label: str) -> bool: ...

    def build_tree(self, root_pid: int) -> list[int]: ...

    def kill_tree(self, root_pid: Optional[int], log_path: Path, label: str) -> None: ...

    def sweep_orphans(
        self,
        workspace: str,
        log_path: Path,
        label: str,
        *,
        started_after: Optional[float] = None,
        run_token: Optional[str] = None,
    ) -> list[int]: ...


# ── Git ports ───────────────────────────────────────────────────────

class GitDiffProbe(Protocol):
    """Port for retrieving git diff stats — used by execution to capture
    snapshot-time diffs without importing git/ directly."""

    def get_numstat(self, workdir: str, *, cached: bool = False, timeout: float = 10.0) -> Optional[str]: ...


@dataclass(frozen=True)
class PreflightResult:
    """Outcome of main-branch integration preflight, neutral to git specifics."""

    ok: bool
    error: str = ""
    safe_tracked: tuple[str, ...] = ()
    safe_untracked: tuple[str, ...] = ()
    unsafe_tracked: tuple[str, ...] = ()
    unsafe_untracked: tuple[str, ...] = ()


class MainIntegrationPreflight(Protocol):
    """Port for main-branch integration preflight — what execution needs to know
    before launching a task that will later cherry-pick into main."""

    def run(
        self,
        *,
        base_workdir: str,
        main_branch: str,
        extra_safe_paths: frozenset[str] = frozenset(),
    ) -> PreflightResult: ...

    def classify_error(self, error: str) -> str: ...


@dataclass(frozen=True)
class IntegrationOutcome:
    """Outcome of a branch-into-main merge (neutral to git internals)."""

    ok: bool
    conflict: bool
    already_integrated: bool = False
    error: str = ""


class GitIntegrationPort(Protocol):
    """Bundled port for git operations needed by tasks/ and agents/runners/.

    Gathers the low-level shell primitives (run, run_with_log), porcelain
    parsing helpers, autocommit, commit-message factories, and main-branch
    integration operations into one seam. Concrete implementation lives in
    `git/task_adapters.py::SubprocessGitIntegration`.
    """

    # ── shell primitives ──────────────────────────────────────────
    def run(self, workdir: str, args: list[str], *, timeout: float = 30.0) -> tuple[bool, str, str, int]: ...

    def run_with_log(
        self, workdir: str, log_path: Path, args: list[str], *, label: str
    ) -> tuple[bool, str, str, int]: ...

    # ── porcelain helpers ─────────────────────────────────────────
    def status_porcelain(self, workdir: str, log_path: Path) -> tuple[bool, str]: ...

    def parse_porcelain(self, porcelain: str) -> tuple[list[str], list[str]]: ...

    def is_runtime_artifact(self, path: str) -> bool: ...

    def split_runtime_artifacts(self, paths: list[str]) -> tuple[list[str], list[str]]: ...

    # ── autocommit ────────────────────────────────────────────────
    def attempt_autocommit_fallback(
        self, workdir: str, log_path: Path, task_id: str, task_text: str
    ) -> bool: ...

    # ── naming / messages ─────────────────────────────────────────
    def task_branch_name(self, task_id: str) -> str: ...

    def board_commit_message(self) -> str: ...

    def sync_commit_message(self) -> str: ...

    # ── integration ───────────────────────────────────────────────
    def has_commits_ahead_of_branch(self, workdir: str, branch: str, log_path: Path) -> bool: ...

    def merge_task_branch_into_main(
        self,
        *,
        base_workdir: str,
        branch_name: str,
        task_id: str,
        task_title: str,
        log_path: Path,
        main_branch: str,
        skip_preflight: bool = False,
    ) -> IntegrationOutcome: ...

    def abort_merge(self, workdir: str) -> bool: ...

    def classify_main_integration_error(self, error: str) -> str: ...
