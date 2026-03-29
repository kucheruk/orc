#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, Optional, Protocol

if TYPE_CHECKING:
    from .backend import Backend as BackendProtocol

from .atomic_io import write_json_atomic
from .failure_reasons import build_main_integration_preflight_reason
from .hooks import update_task_restart_count, update_task_stage_metadata, write_task_file
from .logging import debug_log, log_event, timeline_instant, timeline_step_finished, timeline_step_started
from .notify import send_telegram_message
from .process import (
    ORPHAN_SWEEP_COMMAND_MARKERS,
    build_process_tree,
    is_pid_alive,
    kill_orphan_project_processes,
    kill_process_tree,
)
from .process_groups import terminate_process_group
from .quit_signal import is_quit_after_task_requested, is_stop_requested
from .runner import launch_agent_stream_json
from .session_state import save_active_session, save_session_manifest
from .stream_monitor_state import MonitorSnapshot
from .supervisor_lifecycle import wait_for_completion, wait_for_process_exit
from .stage_artifacts import build_stage_artifact_bundle, parse_stage_artifact_status, validate_stage_artifact_output
from .task_state import delete_runtime_state_file, read_task_active_seconds, runtime_state_path
from .task_source import Task
from .text_parse import clean_summary_lines
from .ui import ui_error, ui_info, ui_warn
from .worktree_flow import get_head_commit, integrate_commit_into_main, preflight_main_integration

GIT_COMMAND_TIMEOUT_SECONDS = 20.0
SDLC_FEEDBACK_MAX_ITERATIONS = 3


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass(frozen=True)
class TaskStageSpec:
    stage_id: str
    model: str
    prompt_template: str


@dataclass(frozen=True)
class TaskExecutionRequest:
    task: Task
    backlog_path: Path
    backlog_arg: str
    task_path: Path
    workdir: str
    base_workdir: str
    run_root: Path
    model: str
    commit_model: str
    merge_expert_model: str
    prompt_template: str
    continue_template: str
    commit_template: str
    merge_expert_template: str
    commit_phase: bool
    integrate_to_main: bool
    main_branch: str
    allow_fallback_commits: bool
    poll: float
    stall_timeout: float
    task_ttl: float
    max_restarts: int
    report_interval: float
    summary_lines: int
    nudge_after: int
    nudge_cooldown: float
    nudge_text: str
    commit_stall_timeout: float
    commit_ttl: float
    progress_done: int
    progress_total: int
    progress_in_progress: int = 0
    enforce_stage_artifacts: bool = False
    stage_specs: tuple[TaskStageSpec, ...] = ()
    agent_output_log_path: Optional[str] = None
    agent_env: Optional[Mapping[str, str]] = None
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None


@dataclass(frozen=True)
class TaskExecutionResult:
    status: str
    reason: str = ""
    delay_seconds: float = 0.0
    committed: bool = False


class TaskWorker(Protocol):
    def launch(
        self,
        *,
        workdir: str,
        prompt_path: Path,
        model: str,
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        progress_done: int,
        progress_total: int,
        progress_in_progress: int = 0,
        agent_output_log_path: Optional[str] = None,
        agent_env: Optional[Mapping[str, str]] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        resume_id: Optional[str] = None,
        resume_latest: bool = False,
        resume_prompt: Optional[str] = None,
        timeline_id: str = "",
        attempt: int = 0,
    ):
        ...


class AgentTaskWorker:
    def __init__(self, backend: Optional["BackendProtocol"] = None) -> None:
        self._backend = backend

    def launch(
        self,
        *,
        workdir: str,
        prompt_path: Path,
        model: str,
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        progress_done: int,
        progress_total: int,
        progress_in_progress: int = 0,
        agent_output_log_path: Optional[str] = None,
        agent_env: Optional[Mapping[str, str]] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        resume_id: Optional[str] = None,
        resume_latest: bool = False,
        resume_prompt: Optional[str] = None,
        timeline_id: str = "",
        attempt: int = 0,
    ):
        return launch_agent_stream_json(
            workdir,
            prompt_path,
            model,
            log_path,
            report_interval=report_interval,
            summary_lines=summary_lines,
            task_id=task_id,
            progress_done=progress_done,
            progress_total=progress_total,
            progress_in_progress=progress_in_progress,
            agent_output_log_path=agent_output_log_path,
            agent_env=agent_env,
            snapshot_publisher=snapshot_publisher,
            resume_id=resume_id,
            resume_latest=resume_latest,
            resume_prompt=resume_prompt,
            timeline_id=timeline_id,
            attempt=attempt,
            backend=self._backend,
        )


RESTART_REASON_TEXT = {
    "stalled": "Ты перестал выдавать результат (завис). Переоцени свой подход.",
    "ttl_exceeded": "Ты превысил лимит времени. Сделай коммит текущего прогресса или выбери более простой путь.",
    "process_exited": "Твой процесс неожиданно завершился (возможно, ошибка синтаксиса в bash).",
}


ETA_WINDOW_SIZE = 20


def _update_completion_stats(
    *,
    monitor,
    task_id: str,
    task_path: Path,
    workdir: str,
    log_path: Path,
) -> None:
    """Record token usage and task duration in stats file (replaces stop hook stats logic)."""
    from .state_paths import stats_path as get_stats_path
    from .task_state import read_task_active_seconds

    stats_file = get_stats_path(workdir)
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8")) if stats_file.exists() else {}
    except Exception:
        stats = {}
    stats.setdefault("tokens_total", 0)
    stats.setdefault("tokens_by_task", {})
    stats.setdefault("durations_by_task", {})
    stats.setdefault("recent_durations", [])
    stats.setdefault("active_seconds_total", 0.0)

    # Tokens
    task_tokens = monitor.metrics.tokens_total
    if task_tokens is not None and task_id and task_id not in stats["tokens_by_task"]:
        stats["tokens_by_task"][task_id] = int(task_tokens)
        stats["tokens_total"] = int(stats["tokens_total"]) + int(task_tokens)

    # Duration
    duration = read_task_active_seconds(task_path, expected_task_id=task_id)
    if duration > 0 and task_id and task_id not in stats["durations_by_task"]:
        duration_int = max(int(duration), 0)
        stats["durations_by_task"][task_id] = duration_int
        recent = stats.get("recent_durations") or []
        if not isinstance(recent, list):
            recent = []
        recent.append(duration_int)
        stats["recent_durations"] = recent[-ETA_WINDOW_SIZE:]
        stats["active_seconds_total"] = float(stats.get("active_seconds_total", 0)) + float(duration_int)

    try:
        write_json_atomic(stats_file, stats, ensure_ascii=False, indent=2)
    except Exception as exc:
        log_event(log_path, "WARN", "failed to update completion stats", error=str(exc))


def _restart_backoff_seconds(restart_count: int) -> float:
    # Deterministic capped backoff prevents rapid restart storms.
    return float(min(2 ** max(restart_count - 1, 0), 30))


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _build_agent_output_log_path(run_root: Path, task_id: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task_id or "task"))[:80] or "task"
    return str(run_root / "raw-stream" / f"{stamp}__{safe_task_id}.log")


def _resolve_runtime_backlog_path(request: TaskExecutionRequest) -> Path:
    raw_arg = str(request.backlog_arg or "").strip()
    if not raw_arg:
        return request.backlog_path
    candidate = Path(raw_arg)
    if candidate.is_absolute():
        return candidate
    return Path(request.workdir) / candidate


def _sync_done_task_from_runtime_to_base(
    *,
    task_id: str,
    base_backlog_path: Path,
    runtime_backlog_path: Path,
    log_path: Path,
) -> bool:
    if runtime_backlog_path == base_backlog_path:
        return True
    from .task_source import MarkdownTaskSource

    try:
        base_source = MarkdownTaskSource(base_backlog_path)
        if base_source.is_task_done(task_id):
            return True
        runtime_source = MarkdownTaskSource(runtime_backlog_path)
        if not runtime_source.is_task_done(task_id):
            return False
        found = base_source.mark_task_done(task_id)
        if not found:
            log_event(
                log_path,
                "ERROR",
                "failed to sync done task from runtime backlog: task not found in base backlog",
                task_id=task_id,
                base_backlog_path=str(base_backlog_path),
                runtime_backlog_path=str(runtime_backlog_path),
            )
            return False
        synced = base_source.is_task_done(task_id)
        if synced:
            log_event(
                log_path,
                "INFO",
                "synced done task from runtime backlog into base backlog",
                task_id=task_id,
                base_backlog_path=str(base_backlog_path),
                runtime_backlog_path=str(runtime_backlog_path),
            )
        return synced
    except Exception as exc:
        log_event(
            log_path,
            "ERROR",
            "failed to sync done task from runtime backlog",
            task_id=task_id,
            base_backlog_path=str(base_backlog_path),
            runtime_backlog_path=str(runtime_backlog_path),
            error=str(exc),
        )
        return False


def _should_defer_base_backlog_sync_to_integration(
    *,
    integrate_to_main: bool,
    base_backlog_path: Path,
    runtime_backlog_path: Path,
) -> bool:
    if not integrate_to_main:
        return False
    return runtime_backlog_path != base_backlog_path


def _find_first_stage_index(stage_specs: list[TaskStageSpec], target_stage_id: str) -> Optional[int]:
    normalized_target = str(target_stage_id or "").strip().lower()
    for idx, stage_spec in enumerate(stage_specs):
        current_id = str(stage_spec.stage_id or "").strip().lower()
        if current_id == normalized_target:
            return idx
    return None


def _read_task_report_text(workdir: str, task_id: str, log_path: Path) -> str:
    report_path = Path(workdir) / "tasks" / f"{task_id}.md"
    if not report_path.exists():
        return ""
    try:
        return report_path.read_text(encoding="utf-8").strip()
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task report markdown", task_id=task_id, error=str(exc))
        return ""


def _is_fragmented_summary_lines(lines: list[str]) -> bool:
    if len(lines) < 5:
        return False
    short_lines = sum(1 for line in lines if len(line) <= 12)
    return short_lines >= int(len(lines) * 0.7)


def _normalize_fragmented_summary_text(summary_text: str) -> str:
    lines = [line.strip() for line in (summary_text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    if not _is_fragmented_summary_lines(lines):
        return "\n".join(lines)
    merged = " ".join(lines)
    merged = re.sub(r"\s+([,.;:!?])", r"\1", merged)
    merged = re.sub(r"(\()\s+", r"\1", merged)
    merged = re.sub(r"\s+(\))", r"\1", merged)
    merged = re.sub(r"\s*/\s*", "/", merged)
    merged = re.sub(r"\s*-\s*", "-", merged)
    merged = re.sub(r"\s+", " ", merged).strip()
    return merged


def _format_eta_for_message(eta_seconds: Optional[float]) -> str:
    if eta_seconds is None:
        return "unknown"
    total_seconds = max(int(eta_seconds), 0)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _build_completion_stats_slice(*, monitor, fallback_done: int, fallback_total: int) -> str:
    done = max(int(fallback_done), 0)
    total = max(int(fallback_total), 1)
    remaining = max(total - done, 0)
    eta_seconds: Optional[float] = None

    build_snapshot = getattr(monitor, "build_snapshot", None)
    if callable(build_snapshot):
        try:
            snapshot = build_snapshot()
            done = max(int(getattr(snapshot, "progress_done", done)), 0)
            total = max(int(getattr(snapshot, "progress_total", total)), 1)
            remaining = max(int(getattr(snapshot, "progress_remaining", total - done)), 0)
            snapshot_eta = getattr(snapshot, "eta_seconds", None)
            if isinstance(snapshot_eta, (int, float)):
                eta_seconds = float(snapshot_eta)
        except Exception:
            pass

    tokens_value = getattr(getattr(monitor, "metrics", None), "tokens_total", None)
    commands_value = getattr(getattr(monitor, "metrics", None), "command_count", None)
    files_edited_value = getattr(getattr(monitor, "metrics", None), "files_edited", None)
    tokens_text = str(tokens_value) if isinstance(tokens_value, int) else "unknown"
    commands_text = str(commands_value) if isinstance(commands_value, int) else "unknown"
    files_edited_text = str(files_edited_value) if isinstance(files_edited_value, int) else "unknown"
    tasks_per_hour = _read_tasks_per_hour_from_stats(getattr(monitor, "workdir", ""))
    rate_text = f"{tasks_per_hour:.2f}" if tasks_per_hour is not None else "unknown"
    return (
        "📊 Срез: "
        f"done {done}/{total} | "
        f"left {remaining} | "
        f"ETA {_format_eta_for_message(eta_seconds)} | "
        f"rate {rate_text} tasks/h | "
        f"tokens {tokens_text} | "
        f"commands {commands_text} | "
        f"files {files_edited_text}"
    )


def _read_tasks_per_hour_from_stats(workdir: str) -> Optional[float]:
    from .state_paths import stats_path as get_stats_path

    root = str(workdir or "").strip()
    if not root:
        return None
    stats_path = get_stats_path(root)
    if not stats_path.exists():
        return None
    try:
        payload = json.loads(stats_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    raw = payload.get("recent_durations") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return None
    durations = [int(value) for value in raw if isinstance(value, (int, float)) and value > 0]
    if not durations:
        return None
    avg_seconds = sum(durations[-3:]) / max(len(durations[-3:]), 1)
    if avg_seconds <= 0:
        return None
    return 3600.0 / avg_seconds


def _build_completion_message(*, task_id: str, workdir: str, summary_text: str, log_path: Path, stats_slice: str) -> str:
    header = f"✅ Задача завершена: {task_id}"
    task_report = _read_task_report_text(workdir, task_id, log_path)
    body = ""
    if task_report:
        body = task_report
    else:
        normalized_summary = _normalize_fragmented_summary_text(summary_text)
        if normalized_summary:
            body = normalized_summary
        else:
            body = f"(Отчёт отсутствует: пустой tasks/{task_id}.md и пустой summary.)"
    return "\n\n".join([header, body, stats_slice])


def _cleanup_monitor_processes(monitor, log_path: Path, label: str) -> None:
    root_pid = getattr(monitor, "init_pid", None) or getattr(getattr(monitor, "proc", None), "pid", None)
    process_group_id = getattr(monitor, "process_group_id", None)
    workspace = str(getattr(monitor, "workdir", "") or "")
    started_at = getattr(monitor, "started_at", None)
    run_token = str(getattr(monitor, "run_token", "") or "").strip() or None
    if terminate_process_group(process_group_id, log_path, label=label):
        if isinstance(root_pid, int) and root_pid > 0 and is_pid_alive(root_pid):
            lingering = build_process_tree(root_pid)
            if lingering:
                log_event(
                    log_path,
                    "WARN",
                    "cleanup post-check: lingering process tree",
                    label=label,
                    root_pid=root_pid,
                    pids=lingering,
                )
                kill_process_tree(root_pid, log_path, label=f"{label}-postcheck")
        kill_orphan_project_processes(
            workspace,
            log_path,
            label=f"{label}-orphan-sweep",
            started_after=started_at,
            command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
            run_token=run_token,
        )
        return
    kill_process_tree(root_pid, log_path, label=label)
    kill_orphan_project_processes(
        workspace,
        log_path,
        label=f"{label}-orphan-sweep",
        started_after=started_at,
        command_markers=ORPHAN_SWEEP_COMMAND_MARKERS,
        run_token=run_token,
    )


def _git_status_porcelain(workdir: str, log_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(log_path, "ERROR", "git status timeout", timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS)
        return False, ""
    except Exception as exc:
        log_event(log_path, "ERROR", "git status failed", error=str(exc))
        return False, ""
    if result.returncode != 0:
        log_event(
            log_path,
            "ERROR",
            "git status non-zero",
            returncode=result.returncode,
            stderr=(result.stderr or "")[:500],
        )
        return False, ""
    return True, result.stdout or ""


def _parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    lines = [ln.rstrip("\n") for ln in (porcelain or "").splitlines() if ln.strip()]
    tracked: list[str] = []
    untracked: list[str] = []
    for ln in lines:
        if ln.startswith("?? "):
            untracked.append(ln)
        else:
            tracked.append(ln)
    return tracked, untracked


def _runtime_artifact_paths_from_porcelain_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    runtime: list[str] = []
    non_runtime: list[str] = []
    for ln in lines:
        path = ln[3:].strip() if len(ln) > 3 else ""
        if (
            path.startswith(".orc/")
            or path == ".cursor/orc-task-runtime.json"
            or path == ".cursor/orc-task.json"
            or path == ".cursor/orc-stop-request.json"
        ):
            runtime.append(ln)
        else:
            non_runtime.append(ln)
    return runtime, non_runtime


def _git_run(workdir: str, log_path: Path, args: list[str], label: str) -> tuple[bool, str, str, int]:
    try:
        result = subprocess.run(
            args,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=GIT_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(
            log_path,
            "ERROR",
            "git command timeout",
            label=label,
            timeout_seconds=GIT_COMMAND_TIMEOUT_SECONDS,
            args=" ".join(args),
        )
        return False, "", "timeout", 124
    except Exception as exc:
        log_event(log_path, "ERROR", "git command failed", label=label, error=str(exc), args=" ".join(args))
        return False, "", str(exc), 1
    ok = result.returncode == 0
    if not ok:
        log_event(
            log_path,
            "ERROR",
            "git command non-zero",
            label=label,
            returncode=result.returncode,
            args=" ".join(args),
            stderr=(result.stderr or "")[:500],
        )
    return ok, result.stdout or "", result.stderr or "", int(result.returncode)


def _attempt_autocommit_fallback(workdir: str, log_path: Path, task_id: str, task_text: str) -> bool:
    """
    Optional recovery step for commit phase when tracked changes remain.
    This path is strictly opt-in.
    """
    ok_add, _, _, _ = _git_run(workdir, log_path, ["git", "add", "-A"], label="commit_fallback:add_all")
    if not ok_add:
        return False

    ok_quiet, _, _, rc = _git_run(
        workdir,
        log_path,
        ["git", "diff", "--cached", "--quiet"],
        label="commit_fallback:cached_quiet",
    )
    if ok_quiet:
        return True
    if rc not in (1,):
        return False

    title = f"{task_id}: checkpoint"
    body = "Commit phase fallback: committed remaining changes left after commit phase."
    if task_text:
        body = f"{body}\n\nTask: {task_text}"
    ok_commit, _, _, _ = _git_run(
        workdir,
        log_path,
        ["git", "commit", "-m", title, "-m", body],
        label="commit_fallback:commit",
    )
    return ok_commit


def has_commits_ahead_of_branch(workdir: str, branch: str, log_path: Path) -> bool:
    ok, stdout, stderr, _ = _git_run(
        workdir,
        log_path,
        ["git", "rev-list", "--count", f"{branch}..HEAD"],
        label="integration:ahead_count",
    )
    if not ok:
        log_event(log_path, "ERROR", "failed to detect ahead commits", branch=branch, error=stderr[:200])
        return False
    try:
        return int((stdout or "0").strip() or "0") > 0
    except ValueError:
        log_event(log_path, "ERROR", "invalid ahead count output", branch=branch, output=stdout[:100])
        return False


def classify_main_integration_error(error: str) -> str:
    text = (error or "").strip().lower()
    if not text:
        return "unknown"
    if "dirty before integration" in text:
        return "dirty_base_repo"
    if text.startswith("git status failed"):
        return "git_status_failed"
    if "main branch" in text and "not found" in text:
        return "main_branch_missing"
    if text.startswith("checkout"):
        return "checkout_failed"
    if "timeout" in text:
        return "git_timeout"
    if "cherry-pick" in text or "cherrypick" in text:
        return "cherry_pick_failed"
    return "unknown"


def _run_commit_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
    timeline_id: str,
    attempt: int,
) -> bool:
    commit_started_ms = timeline_step_started(
        timeline_id=timeline_id,
        task_id=task_id,
        step="commit_phase",
        location="orc_core/task_execution.py:_run_commit_phase",
        attempt=attempt,
        data={"model": request.commit_model},
    )
    ok, porcelain = _git_status_porcelain(request.workdir, log_path)
    if ok and not porcelain.strip():
        log_event(log_path, "INFO", "commit phase skipped: clean tree", task_id=task_id)
        ui_info("[orc] commit phase: skip (clean tree)")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="commit_phase",
            location="orc_core/task_execution.py:_run_commit_phase",
            attempt=attempt,
            started_at_ms=commit_started_ms,
            result="completed",
            reason="clean_tree",
        )
        return True

    prompt = request.commit_template.format_map(prompt_vars)
    prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__commit")
    log_event(log_path, "INFO", "commit phase starting", task_id=task_id, prompt_path=str(prompt_path), model=request.commit_model)
    ui_info("[orc] commit phase: starting")

    try:
        monitor = worker.launch(
            workdir=request.workdir,
            prompt_path=prompt_path,
            model=request.commit_model,
            log_path=log_path,
            report_interval=15.0,
            summary_lines=25,
            task_id=f"{task_id}::commit",
            progress_done=request.progress_done,
            progress_total=request.progress_total,
            agent_output_log_path=agent_output_log_path,
            agent_env=request.agent_env,
            snapshot_publisher=request.snapshot_publisher,
            timeline_id=timeline_id,
            attempt=attempt,
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "commit phase launch failed", task_id=task_id, error=str(exc))
        ui_error(f"[orc] commit phase: launch failed ({type(exc).__name__})")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="commit_phase",
            location="orc_core/task_execution.py:_run_commit_phase",
            attempt=attempt,
            started_at_ms=commit_started_ms,
            result="failed",
            reason="launch_failed",
            data={"error": str(exc)},
        )
        return False
    try:
        result = wait_for_process_exit(
            monitor=monitor,
            poll=request.poll,
            stall_timeout=request.commit_stall_timeout,
            task_ttl=request.commit_ttl,
            log_path=log_path,
            label="commit_phase",
            stop_on_followup_prompt=True,
            timeline_id=timeline_id,
            task_id=task_id,
            attempt=attempt,
            escape_requested=is_stop_requested,
        )
    finally:
        monitor.stop()
        _cleanup_monitor_processes(monitor, log_path, label="commit-phase")

    if result != "completed":
        log_event(log_path, "ERROR", "commit phase failed", task_id=task_id, result=result)
        ui_error(f"[orc] commit phase: failed ({result})")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="commit_phase",
            location="orc_core/task_execution.py:_run_commit_phase",
            attempt=attempt,
            started_at_ms=commit_started_ms,
            result="failed",
            reason=result,
        )
        return False

    ok2, porcelain2 = _git_status_porcelain(request.workdir, log_path)
    if ok2 and porcelain2.strip():
        tracked, untracked = _parse_git_porcelain(porcelain2)
        runtime_tracked, non_runtime_tracked = _runtime_artifact_paths_from_porcelain_lines(tracked)
        runtime_untracked, non_runtime_untracked = _runtime_artifact_paths_from_porcelain_lines(untracked)
        if runtime_tracked or runtime_untracked:
            log_event(
                log_path,
                "WARN",
                "commit phase: ignoring runtime artifacts in git status",
                task_id=task_id,
                tracked_runtime=len(runtime_tracked),
                untracked_runtime=len(runtime_untracked),
            )
        tracked = non_runtime_tracked
        untracked = non_runtime_untracked
        log_event(
            log_path,
            "WARN",
            "commit phase left dirty tree",
            task_id=task_id,
            tracked=len(tracked),
            untracked=len(untracked),
            porcelain=porcelain2[:500],
        )
        if not tracked and untracked:
            ui_warn("[orc] commit phase: warning (repo has untracked files)")
            timeline_step_finished(
                timeline_id=timeline_id,
                task_id=task_id,
                step="commit_phase",
                location="orc_core/task_execution.py:_run_commit_phase",
                attempt=attempt,
                started_at_ms=commit_started_ms,
                result="completed",
                reason="untracked_leftovers",
            )
            return True

        if tracked:
            task_text = str(prompt_vars.get("task_text") or "").strip()
            if request.allow_fallback_commits:
                ui_warn("[orc] commit phase: tracked changes remain; attempting fallback commit")
                if not _attempt_autocommit_fallback(request.workdir, log_path, task_id=task_id, task_text=task_text):
                    ui_error("[orc] commit phase: fallback commit failed")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="commit_phase",
                        location="orc_core/task_execution.py:_run_commit_phase",
                        attempt=attempt,
                        started_at_ms=commit_started_ms,
                        result="failed",
                        reason="fallback_failed",
                    )
                    return False

                ok3, porcelain3 = _git_status_porcelain(request.workdir, log_path)
                if ok3 and porcelain3.strip():
                    tracked3, untracked3 = _parse_git_porcelain(porcelain3)
                    if tracked3:
                        log_event(
                            log_path,
                            "ERROR",
                            "commit phase still dirty after fallback",
                            task_id=task_id,
                            tracked=len(tracked3),
                            untracked=len(untracked3),
                            porcelain=porcelain3[:500],
                        )
                        ui_error("[orc] commit phase: still dirty after fallback")
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="commit_phase",
                            location="orc_core/task_execution.py:_run_commit_phase",
                            attempt=attempt,
                            started_at_ms=commit_started_ms,
                            result="failed",
                            reason="dirty_after_fallback",
                        )
                        return False
                    ui_warn("[orc] commit phase: completed (untracked leftovers remain)")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="commit_phase",
                        location="orc_core/task_execution.py:_run_commit_phase",
                        attempt=attempt,
                        started_at_ms=commit_started_ms,
                        result="completed",
                        reason="untracked_leftovers_after_fallback",
                    )
                    return True
                log_event(log_path, "INFO", "commit phase completed after fallback", task_id=task_id)
                ui_info("[orc] commit phase: completed")
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="commit_phase",
                    location="orc_core/task_execution.py:_run_commit_phase",
                    attempt=attempt,
                    started_at_ms=commit_started_ms,
                    result="completed",
                    reason="fallback_commit",
                )
                return True

            log_event(
                log_path,
                "ERROR",
                "commit phase failed: tracked changes remain and fallback disabled",
                task_id=task_id,
                tracked=len(tracked),
                untracked=len(untracked),
                porcelain=porcelain2[:500],
            )
            ui_error("[orc] commit phase: completed but tracked changes remain (fallback disabled)")
            timeline_step_finished(
                timeline_id=timeline_id,
                task_id=task_id,
                step="commit_phase",
                location="orc_core/task_execution.py:_run_commit_phase",
                attempt=attempt,
                started_at_ms=commit_started_ms,
                result="failed",
                reason="tracked_leftovers_fallback_disabled",
            )
            return False
        ui_warn("[orc] commit phase: completed (untracked leftovers remain)")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="commit_phase",
            location="orc_core/task_execution.py:_run_commit_phase",
            attempt=attempt,
            started_at_ms=commit_started_ms,
            result="completed",
            reason="untracked_leftovers",
        )
        return True

    log_event(log_path, "INFO", "commit phase completed", task_id=task_id)
    ui_info("[orc] commit phase: completed")
    timeline_step_finished(
        timeline_id=timeline_id,
        task_id=task_id,
        step="commit_phase",
        location="orc_core/task_execution.py:_run_commit_phase",
        attempt=attempt,
        started_at_ms=commit_started_ms,
        result="completed",
    )
    return True


def run_merge_expert_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
    timeline_id: str,
    attempt: int,
) -> bool:
    merge_started_ms = timeline_step_started(
        timeline_id=timeline_id,
        task_id=task_id,
        step="merge_expert_phase",
        location="orc_core/task_execution.py:run_merge_expert_phase",
        attempt=attempt,
        data={"model": request.merge_expert_model},
    )
    prompt = request.merge_expert_template.format_map(prompt_vars)
    prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__merge_expert")
    log_event(
        log_path,
        "INFO",
        "merge expert phase starting",
        task_id=task_id,
        prompt_path=str(prompt_path),
        model=request.merge_expert_model,
    )
    ui_info("[orc] merge expert phase: starting")

    try:
        monitor = worker.launch(
            workdir=request.base_workdir,
            prompt_path=prompt_path,
            model=request.merge_expert_model,
            log_path=log_path,
            report_interval=15.0,
            summary_lines=25,
            task_id=f"{task_id}::merge-expert",
            progress_done=request.progress_done,
            progress_total=request.progress_total,
            agent_output_log_path=agent_output_log_path,
            agent_env=request.agent_env,
            snapshot_publisher=request.snapshot_publisher,
            timeline_id=timeline_id,
            attempt=attempt,
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "merge expert phase launch failed", task_id=task_id, error=str(exc))
        ui_error(f"[orc] merge expert phase: launch failed ({type(exc).__name__})")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="merge_expert_phase",
            location="orc_core/task_execution.py:run_merge_expert_phase",
            attempt=attempt,
            started_at_ms=merge_started_ms,
            result="failed",
            reason="launch_failed",
            data={"error": str(exc)},
        )
        return False

    try:
        result = wait_for_process_exit(
            monitor=monitor,
            poll=request.poll,
            stall_timeout=request.commit_stall_timeout,
            task_ttl=request.commit_ttl,
            log_path=log_path,
            label="merge_expert_phase",
            stop_on_followup_prompt=True,
            timeline_id=timeline_id,
            task_id=task_id,
            attempt=attempt,
            escape_requested=is_stop_requested,
        )
    finally:
        monitor.stop()
        _cleanup_monitor_processes(monitor, log_path, label="merge-expert-phase")

    if result != "completed":
        log_event(log_path, "ERROR", "merge expert phase failed", task_id=task_id, result=result)
        ui_error(f"[orc] merge expert phase: failed ({result})")
        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="merge_expert_phase",
            location="orc_core/task_execution.py:run_merge_expert_phase",
            attempt=attempt,
            started_at_ms=merge_started_ms,
            result="failed",
            reason=result,
        )
        return False
    log_event(log_path, "INFO", "merge expert phase completed", task_id=task_id)
    ui_info("[orc] merge expert phase: completed")
    timeline_step_finished(
        timeline_id=timeline_id,
        task_id=task_id,
        step="merge_expert_phase",
        location="orc_core/task_execution.py:run_merge_expert_phase",
        attempt=attempt,
        started_at_ms=merge_started_ms,
        result="completed",
    )
    return True


class TaskExecutionEngine:
    def __init__(self, *, worker: Optional[TaskWorker] = None, log_path: Path, backend: Optional["BackendProtocol"] = None) -> None:
        self.worker = worker or AgentTaskWorker(backend=backend)
        self.log_path = log_path

    def execute(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        task_id = request.task.task_id
        timeline_id = f"{task_id}-{uuid.uuid4().hex[:8]}"
        execute_started_ms = timeline_step_started(
            timeline_id=timeline_id,
            task_id=task_id,
            step="task_execute",
            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
            data={"workdir": request.workdir},
        )
        task_text = request.task.text
        base_backlog_path = request.backlog_path
        runtime_backlog_path = _resolve_runtime_backlog_path(request)
        task_runtime_path = runtime_state_path(request.task_path)
        effective_agent_env = dict(request.agent_env or {})
        effective_agent_env.setdefault("ORC_TASK_RUNTIME_FILE", str(task_runtime_path))
        effective_agent_output_log_path = request.agent_output_log_path or _build_agent_output_log_path(request.run_root, task_id)
        log_event(
            self.log_path,
            "INFO",
            "agent output log selected",
            task_id=task_id,
            agent_output_log_path=effective_agent_output_log_path,
        )
        log_event(
            self.log_path,
            "INFO",
            "backlog resolution",
            task_id=task_id,
            base_backlog_path=str(base_backlog_path),
            runtime_backlog_path=str(runtime_backlog_path),
        )
        if request.integrate_to_main:
            preflight = preflight_main_integration(base_workdir=request.base_workdir, main_branch=request.main_branch)
            failure_kind = classify_main_integration_error(preflight.error)
            safe_tracked = tuple(getattr(preflight, "safe_tracked", ()) or ())
            safe_untracked = tuple(getattr(preflight, "safe_untracked", ()) or ())
            unsafe_tracked = tuple(getattr(preflight, "unsafe_tracked", ()) or ())
            unsafe_untracked = tuple(getattr(preflight, "unsafe_untracked", ()) or ())
            debug_log(
                "MI1",
                "orc_core/task_execution.py:TaskExecutionEngine.execute",
                "main integration preflight evaluated",
                {
                    "task_id": task_id,
                    "base_workdir": request.base_workdir,
                    "main_branch": request.main_branch,
                    "ok": preflight.ok,
                    "failure_kind": failure_kind,
                    "error": preflight.error,
                    "safe_tracked": list(safe_tracked[:20]),
                    "safe_untracked": list(safe_untracked[:20]),
                    "unsafe_tracked": list(unsafe_tracked[:20]),
                    "unsafe_untracked": list(unsafe_untracked[:20]),
                },
            )
            if not preflight.ok:
                log_event(
                    self.log_path,
                    "ERROR",
                    "main integration preflight failed",
                    task_id=task_id,
                    branch=request.main_branch,
                    base_workdir=request.base_workdir,
                    integration_failure_kind=failure_kind,
                    error=preflight.error[:500],
                    safe_tracked=list(safe_tracked[:20]),
                    safe_untracked=list(safe_untracked[:20]),
                    unsafe_tracked=list(unsafe_tracked[:20]),
                    unsafe_untracked=list(unsafe_untracked[:20]),
                )
                ui_error(
                    f"❌ Невозможно подготовить интеграцию в {request.main_branch}: {preflight.error}"
                )
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="task_execute",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    started_at_ms=execute_started_ms,
                    result="failed",
                    reason=f"main_integration_preflight_failed:{failure_kind}",
                )
                return TaskExecutionResult(
                    status="failed",
                    reason=build_main_integration_preflight_reason(failure_kind, preflight.error),
                )
        resume_existing = request.task_path.exists()
        resume_id: Optional[str] = None
        worktree_path_value = request.workdir if Path(request.workdir).resolve() != Path(request.base_workdir).resolve() else ""

        def _finalize_completed(current_task_id: str, current_task_text: str, current_tag: str, monitor) -> TaskExecutionResult:
            commit_completed = False
            log_event(self.log_path, "INFO", "task completed", task_id=current_task_id)
            raw_summary_text = monitor.get_summary_text()
            raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
            cleaned_lines = clean_summary_lines(raw_lines)
            if _is_fragmented_summary_lines(cleaned_lines):
                summary_text = _normalize_fragmented_summary_text("\n".join(cleaned_lines))
            else:
                summary_text = "\n".join(cleaned_lines[-request.summary_lines :])
            tokens = monitor.metrics.tokens_total if monitor.metrics.tokens_total is not None else "-"
            files_edited = monitor.metrics.files_edited if monitor.metrics.files_edited is not None else "-"
            ui_info(
                f"[orc] completed stats tokens={tokens} lines={monitor.metrics.total_lines} "
                f"commands={monitor.metrics.command_count} files_edited={files_edited}"
            )
            _update_completion_stats(
                monitor=monitor,
                task_id=current_task_id,
                task_path=request.task_path,
                workdir=request.workdir,
                log_path=self.log_path,
            )
            debug_log(
                "H8",
                "orc_core/task_execution.py:execute:summary",
                "summary prepared",
                {
                    "summary_len": len(summary_text),
                    "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
                },
            )
            stats_slice = _build_completion_stats_slice(
                monitor=monitor,
                fallback_done=request.progress_done,
                fallback_total=request.progress_total,
            )
            completion_message = _build_completion_message(
                task_id=current_task_id,
                workdir=request.workdir,
                summary_text=summary_text,
                log_path=self.log_path,
                stats_slice=stats_slice,
            )
            send_telegram_message(completion_message, self.log_path)
            prompt_vars = SafeDict(
                task_text=current_task_text,
                task_id=current_task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
            )
            force_commit_for_quit_after_task = bool((not request.commit_phase) and is_quit_after_task_requested())
            should_run_commit_phase = bool(request.commit_phase or force_commit_for_quit_after_task)
            if force_commit_for_quit_after_task:
                log_event(
                    self.log_path,
                    "INFO",
                    "commit phase forced by quit-after-task request",
                    task_id=current_task_id,
                )
                ui_info("[orc] commit phase: forced by QUIT AFTER TASK")
            if should_run_commit_phase and not _run_commit_phase(
                self.worker,
                request,
                prompt_vars,
                current_task_id,
                current_tag,
                self.log_path,
                effective_agent_output_log_path,
                timeline_id,
                restart_count,
            ):
                ui_error("❌ Commit phase failed. Stop to avoid accumulating uncommitted changes.")
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=current_task_id,
                    step="task_execute",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    started_at_ms=execute_started_ms,
                    result="failed",
                    reason="commit_phase_failed",
                )
                return TaskExecutionResult(status="failed", reason="commit_phase_failed")
            if should_run_commit_phase:
                commit_completed = True

            if request.integrate_to_main:
                integration_started_ms = timeline_step_started(
                    timeline_id=timeline_id,
                    task_id=current_task_id,
                    step="main_integration",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=restart_count + 1,
                    data={"branch": request.main_branch},
                )
                if not has_commits_ahead_of_branch(request.workdir, request.main_branch, self.log_path):
                    log_event(
                        self.log_path,
                        "INFO",
                        "main integration skipped: no task commit ahead of main",
                        task_id=current_task_id,
                        branch=request.main_branch,
                    )
                    try:
                        request.task_path.unlink(missing_ok=True)
                        delete_runtime_state_file(request.task_path, self.log_path, reason="task_completed")
                    except Exception:
                        pass
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="main_integration",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=restart_count + 1,
                        started_at_ms=integration_started_ms,
                        result="skipped",
                        reason="no_commits_ahead",
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="completed",
                    )
                    return TaskExecutionResult(status="completed", committed=commit_completed)
                try:
                    commit_sha = get_head_commit(request.workdir)
                except Exception as exc:
                    log_event(
                        self.log_path,
                        "ERROR",
                        "cannot resolve task commit sha before main integration",
                        task_id=current_task_id,
                        error=str(exc),
                    )
                    ui_error("❌ Не удалось определить commit задачи для переноса в main.")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="main_integration",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=restart_count + 1,
                        started_at_ms=integration_started_ms,
                        result="failed",
                        reason="integration_commit_sha_failed",
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason="integration_commit_sha_failed",
                    )
                    return TaskExecutionResult(status="failed", reason="integration_commit_sha_failed")

                integration = integrate_commit_into_main(
                    base_workdir=request.base_workdir,
                    commit_sha=commit_sha,
                    task_id=current_task_id,
                    log_path=self.log_path,
                    main_branch=request.main_branch,
                )
                if not integration.ok and integration.conflict:
                    merge_prompt_vars = SafeDict(
                        task_text=current_task_text,
                        task_id=current_task_id,
                        backlog=request.backlog_arg,
                        workspace=request.base_workdir,
                    )
                    if not run_merge_expert_phase(
                        self.worker,
                        request,
                        merge_prompt_vars,
                        current_task_id,
                        current_tag,
                        self.log_path,
                        effective_agent_output_log_path,
                        timeline_id,
                        restart_count,
                    ):
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="main_integration",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            attempt=restart_count + 1,
                            started_at_ms=integration_started_ms,
                            result="failed",
                            reason="merge_expert_phase_failed",
                        )
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason="merge_expert_phase_failed",
                        )
                        return TaskExecutionResult(status="failed", reason="merge_expert_phase_failed")
                    integration = integrate_commit_into_main(
                        base_workdir=request.base_workdir,
                        commit_sha=commit_sha,
                        task_id=current_task_id,
                        log_path=self.log_path,
                        main_branch=request.main_branch,
                    )
                if not integration.ok:
                    failure_kind = classify_main_integration_error(integration.error)
                    log_event(
                        self.log_path,
                        "ERROR",
                        "failed to integrate task commit into main",
                        task_id=current_task_id,
                        commit_sha=commit_sha,
                        integration_failure_kind=failure_kind,
                        error=integration.error[:500],
                    )
                    ui_error(f"❌ Не удалось перенести commit в {request.main_branch}: {integration.error}")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="main_integration",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=restart_count + 1,
                        started_at_ms=integration_started_ms,
                        result="failed",
                        reason=f"main_integration_failed:{failure_kind}",
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason=f"main_integration_failed:{failure_kind}",
                    )
                    return TaskExecutionResult(status="failed", reason="main_integration_failed")
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=current_task_id,
                    step="main_integration",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=restart_count + 1,
                    started_at_ms=integration_started_ms,
                    result="completed",
                )
            try:
                from .task_source import MarkdownTaskSource

                base_done = MarkdownTaskSource(base_backlog_path).is_task_done(current_task_id)
                runtime_done = False
                if runtime_backlog_path != base_backlog_path:
                    runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(current_task_id)
                if runtime_done and not base_done:
                    if _should_defer_base_backlog_sync_to_integration(
                        integrate_to_main=request.integrate_to_main,
                        base_backlog_path=base_backlog_path,
                        runtime_backlog_path=runtime_backlog_path,
                    ):
                        log_event(
                            self.log_path,
                            "ERROR",
                            "backlog invariant violated after main integration: task marked done only in runtime worktree backlog",
                            task_id=current_task_id,
                            base_backlog_path=str(base_backlog_path),
                            runtime_backlog_path=str(runtime_backlog_path),
                            integrate_to_main=request.integrate_to_main,
                        )
                        debug_log(
                            "MI2",
                            "orc_core/task_execution.py:TaskExecutionEngine.execute",
                            "base backlog was not updated by integrated commit",
                            {
                                "task_id": current_task_id,
                                "base_backlog_path": str(base_backlog_path),
                                "runtime_backlog_path": str(runtime_backlog_path),
                            },
                        )
                        ui_error(
                            "❌ После успешной main integration backlog в base не отмечен как done. "
                            "Значит, отметка попала не в task commit, а пыталась догнаться позже."
                        )
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason="worktree_not_integrated_to_base",
                        )
                        return TaskExecutionResult(status="failed", reason="worktree_not_integrated_to_base")
                    synced = _sync_done_task_from_runtime_to_base(
                        task_id=current_task_id,
                        base_backlog_path=base_backlog_path,
                        runtime_backlog_path=runtime_backlog_path,
                        log_path=self.log_path,
                    )
                    if not synced:
                        log_event(
                            self.log_path,
                            "ERROR",
                            "backlog invariant violated after completion: task marked done only in runtime worktree backlog",
                            task_id=current_task_id,
                            base_backlog_path=str(base_backlog_path),
                            runtime_backlog_path=str(runtime_backlog_path),
                        )
                        ui_error(
                            "❌ После завершения задачи backlog в base не синхронизирован с worktree. "
                            "Инвариант worktree -> base нарушен."
                        )
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason="worktree_not_integrated_to_base",
                        )
                        return TaskExecutionResult(status="failed", reason="worktree_not_integrated_to_base")
            except Exception as exc:
                log_event(
                    self.log_path,
                    "ERROR",
                    "failed to validate backlog invariant after completion",
                    task_id=current_task_id,
                    error=str(exc),
                    base_backlog_path=str(base_backlog_path),
                    runtime_backlog_path=str(runtime_backlog_path),
                )
            # Clean up task state files (previously done by stop hook)
            try:
                request.task_path.unlink(missing_ok=True)
                delete_runtime_state_file(request.task_path, self.log_path, reason="task_completed")
            except Exception:
                pass
            timeline_step_finished(
                timeline_id=timeline_id,
                task_id=current_task_id,
                step="task_execute",
                location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                started_at_ms=execute_started_ms,
                result="completed",
            )
            return TaskExecutionResult(status="completed", committed=commit_completed)

        debug_log(
            "H2",
            "orc_core/task_execution.py:execute:task_state",
            "task file state",
            {"task_path": str(request.task_path), "exists": resume_existing},
        )

        persisted_restart_count = 0
        elapsed_before_start = 0.0
        if resume_existing:
            try:
                active = json.loads(request.task_path.read_text(encoding="utf-8"))
                active_task_id = active.get("task_id")
                active_task_text = active.get("task_text")
                active_backlog_raw = str(active.get("backlog_path") or "").strip()
                raw_conversation_id = active.get("conversation_id", None)
                resume_id = str(raw_conversation_id or "").strip() or None
                raw_restart_count = active.get("restart_count", 0)
                try:
                    persisted_restart_count = max(int(raw_restart_count), 0)
                except (TypeError, ValueError):
                    persisted_restart_count = 0
                elapsed_before_start = read_task_active_seconds(request.task_path, expected_task_id=str(active_task_id or ""))
            except Exception as exc:
                log_event(self.log_path, "ERROR", "failed to read task file", error=str(exc))
                ui_warn(
                    f"⚠️ Не удалось прочитать {request.task_path}. "
                    "Исправь/удали файл состояния или запусти с --drop для чистого старта."
                )
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="task_execute",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    started_at_ms=execute_started_ms,
                    result="continue",
                    reason="task_file_read_failed",
                )
                return TaskExecutionResult(status="continue", reason="task_file_read_failed", delay_seconds=max(request.poll, 0.2))

            same_backlog = True
            if active_backlog_raw:
                try:
                    same_backlog = Path(active_backlog_raw).resolve() == request.backlog_path.resolve()
                except Exception:
                    same_backlog = active_backlog_raw == str(request.backlog_path)

            if not same_backlog:
                log_event(
                    self.log_path,
                    "WARN",
                    "resume state ignored: backlog mismatch",
                    task_backlog=active_backlog_raw,
                    expected_backlog=str(request.backlog_path),
                )
                resume_existing = False
                resume_id = None
                persisted_restart_count = 0
                elapsed_before_start = 0.0

            if resume_existing and active_task_id and request.task_path.exists():
                from .task_source import MarkdownTaskSource

                if MarkdownTaskSource(base_backlog_path).is_task_done(active_task_id):
                    log_event(self.log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
                    ui_info(f"✅ {active_task_id} уже отмечена [x]. Удаляю {request.task_path} и продолжаю.")
                    try:
                        request.task_path.unlink()
                        delete_runtime_state_file(request.task_path, self.log_path, reason="stale_done_task_file")
                    except Exception as exc:
                        log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=active_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="continue",
                        reason="stale_done_task_file",
                    )
                    return TaskExecutionResult(status="continue", reason="stale_done_task_file")

            if resume_existing:
                task_id = active_task_id or task_id
                task_text = active_task_text or task_text
                log_event(self.log_path, "INFO", "resume existing task", task_id=task_id)
                ui_info(f"↩️ Обнаружена активная задача, запускаю resume для {task_id}.")
                if not resume_id:
                    log_event(
                        self.log_path,
                        "WARN",
                        "task file has no conversation_id — auto-dropping for fresh start",
                        task_id=task_id,
                        restart_count=persisted_restart_count,
                    )
                    ui_info(f"🗑️ Стейт {task_id} без conversation_id — авто-сброс для чистого старта.")
                    try:
                        request.task_path.unlink()
                        delete_runtime_state_file(request.task_path, self.log_path, reason="auto_drop_no_conversation")
                    except Exception:
                        pass
                    resume_existing = False
                    resume_id = None
                    # Preserve restart_count so the agent knows it's a continuation
                    elapsed_before_start = 0.0
                log_event(
                    self.log_path,
                    "INFO",
                    "resume selection",
                    conversation_id=resume_id or "",
                    resume_from_latest=False,
                    restart_count=persisted_restart_count,
                    active_seconds=elapsed_before_start,
                )

        if not resume_existing:
            write_task_file(
                request.base_workdir,
                request.task,
                request.backlog_path,
                self.log_path,
                restart_count=0,
                task_path_override=request.task_path,
            )
            if request.task_path.exists():
                try:
                    payload = json.loads(request.task_path.read_text(encoding="utf-8"))
                    if worktree_path_value:
                        payload["worktree_path"] = worktree_path_value
                    payload["branch_name"] = str(payload.get("branch_name") or "")
                    payload["status"] = "active"
                    write_json_atomic(request.task_path, payload, ensure_ascii=False, indent=2)
                except Exception as exc:
                    log_event(self.log_path, "WARN", "failed to enrich task state with worktree metadata", error=str(exc))
            start_header = f"{task_id} — {task_text}" if task_text else task_id
            send_telegram_message(f"Старт задачи\n{start_header}", self.log_path)
        if request.task_path.exists():
            try:
                session_payload = json.loads(request.task_path.read_text(encoding="utf-8"))
                save_active_session(
                    request.base_workdir,
                    {
                        "version": 1,
                        "task_id": str(session_payload.get("task_id") or task_id),
                        "session_id": str(session_payload.get("session_id") or ""),
                        "task_file": str(request.task_path),
                        "worktree_path": str(session_payload.get("worktree_path") or worktree_path_value),
                        "conversation_id": str(session_payload.get("conversation_id") or resume_id or ""),
                        "status": "active",
                    },
                )
                session_id = str(session_payload.get("session_id") or "").strip()
                if session_id:
                    save_session_manifest(request.base_workdir, session_id, session_payload)
            except Exception as exc:
                log_event(self.log_path, "WARN", "failed to persist active session snapshot", error=str(exc))

        stage_specs = list(request.stage_specs)
        if not stage_specs:
            stage_specs = [TaskStageSpec(stage_id="implementation", model=request.model, prompt_template=request.prompt_template)]
        artifact_bundle = build_stage_artifact_bundle(workdir=request.workdir, task_id=task_id)
        artifact_prompt_vars = dict(artifact_bundle.to_prompt_vars())
        enforce_stage_artifacts = bool(request.enforce_stage_artifacts) and bool(request.stage_specs)
        implementation_stage_index = _find_first_stage_index(stage_specs, "implementation")
        feedback_iteration_count = 0
        stage_index = 0

        def _complete_stage(
            *,
            current_task_id: str,
            current_task_text: str,
            current_tag: str,
            current_monitor,
            current_stage_id: str,
            current_stage_index: int,
            current_stage_is_final: bool,
            current_attempt_number: int,
            current_attempt_started_ms: int,
            completion_reason: str = "",
        ) -> tuple[Optional[TaskExecutionResult], Optional[int], bool]:
            nonlocal feedback_iteration_count
            if enforce_stage_artifacts:
                artifact_ok, artifact_reason, artifact_path = validate_stage_artifact_output(
                    stage_id=current_stage_id,
                    bundle=artifact_bundle,
                )
                if not artifact_ok:
                    failure_reason = f"stage_artifact_{current_stage_id}_{artifact_reason}"
                    log_event(
                        self.log_path,
                        "ERROR",
                        "sdlc stage artifact validation failed",
                        task_id=current_task_id,
                        stage_id=current_stage_id,
                        stage_index=current_stage_index + 1,
                        stage_total=len(stage_specs),
                        artifact_path=str(artifact_path),
                        artifact_reason=artifact_reason,
                    )
                    ui_error(
                        "❌ SDLC stage завершился без валидного артефакта: "
                        f"{current_stage_id} -> {artifact_path}"
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="agent_attempt",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=current_attempt_number,
                        started_at_ms=current_attempt_started_ms,
                        result="failed",
                        reason=failure_reason,
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason=failure_reason,
                    )
                    return TaskExecutionResult(status="failed", reason=failure_reason), None, False
            if enforce_stage_artifacts and current_stage_id in {"review", "testing"}:
                status_ok, stage_status, stage_status_reason, stage_status_path = parse_stage_artifact_status(
                    stage_id=current_stage_id,
                    bundle=artifact_bundle,
                )
                if not status_ok:
                    failure_reason = f"stage_artifact_{current_stage_id}_{stage_status_reason}"
                    log_event(
                        self.log_path,
                        "ERROR",
                        "sdlc stage status parsing failed",
                        task_id=current_task_id,
                        stage_id=current_stage_id,
                        stage_index=current_stage_index + 1,
                        stage_total=len(stage_specs),
                        artifact_path=str(stage_status_path),
                        artifact_reason=stage_status_reason,
                        artifact_status=stage_status,
                    )
                    ui_error(
                        "❌ SDLC stage артефакт не содержит валидный `status:` заголовок: "
                        f"{current_stage_id} -> {stage_status_path}"
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="agent_attempt",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=current_attempt_number,
                        started_at_ms=current_attempt_started_ms,
                        result="failed",
                        reason=failure_reason,
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason=failure_reason,
                    )
                    return TaskExecutionResult(status="failed", reason=failure_reason), None, False
            completion_data = {
                "timeline_id": timeline_id,
                "task_id": current_task_id,
                "step": "agent_attempt",
                "location": "orc_core/task_execution.py:TaskExecutionEngine.execute",
                "attempt": current_attempt_number,
                "started_at_ms": current_attempt_started_ms,
                "result": "completed",
            }
            if completion_reason:
                completion_data["reason"] = completion_reason
            timeline_step_finished(**completion_data)
            if current_stage_is_final:
                return None, None, True

            next_stage_index = current_stage_index + 1
            if enforce_stage_artifacts and current_stage_id == "review":
                status_ok, stage_status, _stage_status_reason, _stage_status_path = parse_stage_artifact_status(
                    stage_id=current_stage_id,
                    bundle=artifact_bundle,
                )
                if status_ok and stage_status == "needs_changes":
                    feedback_iteration_count += 1
                    if feedback_iteration_count > SDLC_FEEDBACK_MAX_ITERATIONS:
                        failure_reason = "sdlc_feedback_limit_exceeded"
                        log_event(
                            self.log_path,
                            "ERROR",
                            "sdlc feedback iteration limit exceeded",
                            task_id=current_task_id,
                            stage_id=current_stage_id,
                            stage_index=current_stage_index + 1,
                            stage_total=len(stage_specs),
                            feedback_iteration_count=feedback_iteration_count,
                            max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
                        )
                        ui_error("❌ SDLC feedback loop превысил лимит итераций.")
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason=failure_reason,
                        )
                        return TaskExecutionResult(status="failed", reason=failure_reason), None, False
                    if implementation_stage_index is None:
                        failure_reason = "sdlc_feedback_missing_implementation_stage"
                        log_event(
                            self.log_path,
                            "ERROR",
                            "sdlc feedback loop requested but implementation stage missing",
                            task_id=current_task_id,
                            stage_id=current_stage_id,
                            stage_index=current_stage_index + 1,
                            stage_total=len(stage_specs),
                        )
                        ui_error("❌ SDLC feedback loop не может вернуться: отсутствует stage `implementation`.")
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=current_task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason=failure_reason,
                        )
                        return TaskExecutionResult(status="failed", reason=failure_reason), None, False
                    next_stage_index = implementation_stage_index
                    log_event(
                        self.log_path,
                        "INFO",
                        "sdlc feedback loop requested by review verdict",
                        task_id=current_task_id,
                        stage_id=current_stage_id,
                        stage_index=current_stage_index + 1,
                        stage_total=len(stage_specs),
                        next_stage_id=stage_specs[next_stage_index].stage_id,
                        next_stage_index=next_stage_index + 1,
                        feedback_iteration_count=feedback_iteration_count,
                        max_feedback_iterations=SDLC_FEEDBACK_MAX_ITERATIONS,
                    )
            if enforce_stage_artifacts and current_stage_id == "testing":
                status_ok, stage_status, _stage_status_reason, _stage_status_path = parse_stage_artifact_status(
                    stage_id=current_stage_id,
                    bundle=artifact_bundle,
                )
                if status_ok and stage_status == "fail":
                    failure_reason = "testing_failed"
                    log_event(
                        self.log_path,
                        "ERROR",
                        "testing stage reported failure verdict",
                        task_id=current_task_id,
                        stage_id=current_stage_id,
                        stage_index=current_stage_index + 1,
                        stage_total=len(stage_specs),
                    )
                    ui_error("❌ Testing stage завершился с verdict `status: fail`.")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=current_task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason=failure_reason,
                    )
                    return TaskExecutionResult(status="failed", reason=failure_reason), None, False
            log_event(
                self.log_path,
                "INFO",
                "sdlc stage completed",
                task_id=current_task_id,
                stage_id=current_stage_id,
                stage_index=current_stage_index + 1,
                stage_total=len(stage_specs),
                next_stage_index=(next_stage_index + 1) if next_stage_index is not None else None,
                completion_reason=completion_reason or "monitor_completed",
            )
            return None, next_stage_index, False

        def _should_retry_after_missing_stage_artifact(
            *,
            stage_failure: TaskExecutionResult,
            monitor_result: str,
            current_stage_id: str,
            retry_budget_left: int,
        ) -> bool:
            if retry_budget_left <= 0:
                return False
            if monitor_result != "process_exited":
                return False
            if stage_failure.status != "failed":
                return False
            return stage_failure.reason.startswith(f"stage_artifact_{current_stage_id}_")

        while stage_index < len(stage_specs):
            stage_spec = stage_specs[stage_index]
            stage_id = (stage_spec.stage_id or f"stage_{stage_index + 1}").strip()
            stage_model = (stage_spec.model or request.model).strip() or request.model
            stage_is_final = stage_index == (len(stage_specs) - 1)
            if request.task_path.exists():
                update_task_stage_metadata(
                    request.task_path,
                    self.log_path,
                    stage_id=stage_id,
                    stage_index=stage_index,
                    stage_total=len(stage_specs),
                    is_final=stage_is_final,
                )
            prompt_vars = SafeDict(
                task_text=task_text,
                task_id=task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
                stage_id=stage_id,
                stage_index=stage_index + 1,
                stage_total=len(stage_specs),
                stage_is_final=stage_is_final,
                **artifact_prompt_vars,
            )
            prompt = stage_spec.prompt_template.format_map(prompt_vars)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
            tag = f"{ts}__{safe_name}__{stage_id}"
            prompt_path = _write_prompt_file(request.run_root, prompt, tag)

            stage_resume_existing = resume_existing and stage_index == 0
            stage_resume_id = resume_id if stage_resume_existing else None
            resume_prompt_text = request.nudge_text if stage_resume_existing else None
            restart_count = persisted_restart_count if stage_resume_existing else 0
            elapsed_before_start_stage = elapsed_before_start if stage_resume_existing else 0.0

            stage_next_index: Optional[int] = None
            missing_artifact_retry_budget = 1
            while True:
                attempt_number = restart_count + 1
                attempt_started_ms = timeline_step_started(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="agent_attempt",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    data={"restart_count": restart_count, "stage_id": stage_id, "stage_index": stage_index + 1},
                )
                update_task_restart_count(request.task_path, self.log_path, restart_count)
                log_event(
                    self.log_path,
                    "INFO",
                    "launching agent",
                    task_id=task_id,
                    restart_count=restart_count,
                    stage_id=stage_id,
                    stage_index=stage_index + 1,
                    stage_total=len(stage_specs),
                )
                try:
                    active_monitor = self.worker.launch(
                        workdir=request.workdir,
                        prompt_path=prompt_path,
                        model=stage_model,
                        log_path=self.log_path,
                        report_interval=request.report_interval,
                        summary_lines=request.summary_lines,
                        task_id=f"{task_id} [{stage_id}]" if stage_id else task_id,
                        progress_done=request.progress_done,
                        progress_total=request.progress_total,
                        progress_in_progress=request.progress_in_progress,
                        agent_output_log_path=effective_agent_output_log_path,
                        agent_env=effective_agent_env,
                        snapshot_publisher=request.snapshot_publisher,
                        resume_id=stage_resume_id,
                        resume_latest=False,
                        resume_prompt=resume_prompt_text if stage_resume_existing else None,
                        timeline_id=timeline_id,
                        attempt=attempt_number,
                    )
                except FileNotFoundError:
                    ui_error("❌ agent не найден. Установите Cursor CLI (agent) и попробуйте снова.")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason="agent_not_found",
                    )
                    return TaskExecutionResult(status="failed", reason="agent_not_found")

                try:
                    wait_started_ms = timeline_step_started(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="wait_for_completion",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=attempt_number,
                    )
                    try:
                        result = wait_for_completion(
                            task_path=request.task_path,
                            monitor=active_monitor,
                            poll=request.poll,
                            stall_timeout=request.stall_timeout,
                            task_ttl=request.task_ttl,
                            elapsed_before_start=elapsed_before_start_stage,
                            ignore_initial_backlog_done=enforce_stage_artifacts and stage_index > 0,
                            log_path=self.log_path,
                            nudge_after=request.nudge_after,
                            nudge_cooldown=request.nudge_cooldown,
                            nudge_text=request.nudge_text,
                            task_id=task_id,
                            task_text=task_text,
                            timeline_id=timeline_id,
                            attempt=attempt_number,
                            escape_requested=is_stop_requested,
                        )
                    except Exception:
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="wait_for_completion",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            attempt=attempt_number,
                            started_at_ms=wait_started_ms,
                            result="failed",
                            reason="exception",
                        )
                        raise
                finally:
                    active_monitor.stop()
                    _cleanup_monitor_processes(active_monitor, self.log_path, label="agent")
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="wait_for_completion",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    started_at_ms=wait_started_ms,
                    result=result,
                )

                debug_log(
                    "H8",
                    "orc_core/task_execution.py:execute:completion_state",
                    "completion state",
                    {
                        "result": result,
                        "monitor_is_none": active_monitor is None,
                        "lines": active_monitor.metrics.total_lines,
                        "commands": active_monitor.metrics.command_count,
                        "tokens_total": active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-",
                        "stage_id": stage_id,
                    },
                )

                if result == "completed":
                    stage_failure, stage_next_index, stage_completed_final = _complete_stage(
                        current_task_id=task_id,
                        current_task_text=task_text,
                        current_tag=tag,
                        current_monitor=active_monitor,
                        current_stage_id=stage_id,
                        current_stage_index=stage_index,
                        current_stage_is_final=stage_is_final,
                        current_attempt_number=attempt_number,
                        current_attempt_started_ms=attempt_started_ms,
                    )
                    if stage_failure is not None:
                        return stage_failure
                    if stage_completed_final:
                        return _finalize_completed(task_id, task_text, tag, active_monitor)
                    break
                if result == "model_unavailable":
                    log_event(
                        self.log_path,
                        "ERROR",
                        "agent model unavailable; stopping without restart",
                        task_id=task_id,
                        model=stage_model,
                    )
                    ui_error(
                        "❌ Выбранная модель недоступна для `agent`. "
                        "Проверьте `agent --list-models` и укажите доступную модель через `--model`."
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="agent_attempt",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=attempt_number,
                        started_at_ms=attempt_started_ms,
                        result="failed",
                        reason="model_unavailable",
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason="model_unavailable",
                    )
                    return TaskExecutionResult(status="failed", reason="model_unavailable")
                if result == "waiting_for_input":
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="agent_attempt",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=attempt_number,
                        started_at_ms=attempt_started_ms,
                        result="waiting_for_input",
                    )
                    restart_count += 1
                    update_task_restart_count(request.task_path, self.log_path, restart_count)
                    log_event(
                        self.log_path,
                        "INFO",
                        "waiting_for_input_budget_tick",
                        task_id=task_id,
                        restart_count=restart_count,
                        max_restarts=request.max_restarts,
                    )
                    if restart_count > request.max_restarts:
                        log_event(
                            self.log_path,
                            "ERROR",
                            "max restarts exceeded while waiting for input",
                            task_id=task_id,
                            restart_count=restart_count,
                            max_restarts=request.max_restarts,
                        )
                        ui_error("❌ Агент зациклился на запросе follow-up ввода. Лимит перезапусков исчерпан.")
                        timeline_step_finished(
                            timeline_id=timeline_id,
                            task_id=task_id,
                            step="task_execute",
                            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                            started_at_ms=execute_started_ms,
                            result="failed",
                            reason="max_restarts_exceeded",
                        )
                        return TaskExecutionResult(status="failed", reason="max_restarts_exceeded")
                    delay = max(request.nudge_cooldown, request.poll, 1.0)
                    timeline_instant(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="restart_backoff_sleep",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        attempt=attempt_number,
                        result="continue",
                        reason="waiting_for_input",
                        data={"delay_seconds": delay},
                    )
                    ui_warn(
                        f"[orc] агент запросил follow-up ввод; продолжу цикл через {delay:.1f}s "
                        "(resume сохранен, задача не потеряна)"
                    )
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="continue",
                        reason="waiting_for_input",
                    )
                    return TaskExecutionResult(status="continue", reason="waiting_for_input", delay_seconds=delay)
                try:
                    from .task_source import MarkdownTaskSource

                    base_done = MarkdownTaskSource(base_backlog_path).is_task_done(task_id)
                    runtime_done = False
                    if runtime_backlog_path != base_backlog_path:
                        runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(task_id)
                    if base_done:
                        log_event(
                            self.log_path,
                            "WARN",
                            "task marked done after non-completed monitor result",
                            task_id=task_id,
                            monitor_result=result,
                        )
                        stage_failure, stage_next_index, stage_completed_final = _complete_stage(
                            current_task_id=task_id,
                            current_task_text=task_text,
                            current_tag=tag,
                            current_monitor=active_monitor,
                            current_stage_id=stage_id,
                            current_stage_index=stage_index,
                            current_stage_is_final=stage_is_final,
                            current_attempt_number=attempt_number,
                            current_attempt_started_ms=attempt_started_ms,
                            completion_reason="base_backlog_marked_done",
                        )
                        if stage_failure is not None:
                            if _should_retry_after_missing_stage_artifact(
                                stage_failure=stage_failure,
                                monitor_result=result,
                                current_stage_id=stage_id,
                                retry_budget_left=missing_artifact_retry_budget,
                            ):
                                missing_artifact_retry_budget -= 1
                                log_event(
                                    self.log_path,
                                    "WARN",
                                    "task marked done but stage artifact missing after process exit; retrying",
                                    task_id=task_id,
                                    stage_id=stage_id,
                                    monitor_result=result,
                                    reason=stage_failure.reason,
                                    retry_budget_left=missing_artifact_retry_budget,
                                )
                            else:
                                return stage_failure
                        else:
                            if stage_completed_final and request.task_path.exists():
                                try:
                                    request.task_path.unlink()
                                    delete_runtime_state_file(request.task_path, self.log_path, reason="base_backlog_marked_done")
                                except Exception as exc:
                                    log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                            if stage_completed_final:
                                return _finalize_completed(task_id, task_text, tag, active_monitor)
                            break
                    if runtime_done:
                        if _should_defer_base_backlog_sync_to_integration(
                            integrate_to_main=request.integrate_to_main,
                            base_backlog_path=base_backlog_path,
                            runtime_backlog_path=runtime_backlog_path,
                        ):
                            log_event(
                                self.log_path,
                                "INFO",
                                "runtime backlog marked done; deferring base backlog sync until main integration",
                                task_id=task_id,
                                monitor_result=result,
                                base_backlog_path=str(base_backlog_path),
                                runtime_backlog_path=str(runtime_backlog_path),
                            )
                            debug_log(
                                "MI3",
                                "orc_core/task_execution.py:TaskExecutionEngine.execute",
                                "deferred base backlog sync because runtime backlog done will be carried by task commit",
                                {
                                    "task_id": task_id,
                                    "monitor_result": result,
                                    "base_backlog_path": str(base_backlog_path),
                                    "runtime_backlog_path": str(runtime_backlog_path),
                                },
                            )
                        else:
                            synced = _sync_done_task_from_runtime_to_base(
                                task_id=task_id,
                                base_backlog_path=base_backlog_path,
                                runtime_backlog_path=runtime_backlog_path,
                                log_path=self.log_path,
                            )
                            if not synced:
                                log_event(
                                    self.log_path,
                                    "ERROR",
                                    "runtime backlog marked done but base backlog sync failed",
                                    task_id=task_id,
                                    base_backlog_path=str(base_backlog_path),
                                    runtime_backlog_path=str(runtime_backlog_path),
                                )
                                timeline_step_finished(
                                    timeline_id=timeline_id,
                                    task_id=task_id,
                                    step="task_execute",
                                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                                    started_at_ms=execute_started_ms,
                                    result="failed",
                                    reason="runtime_backlog_sync_failed",
                                )
                                return TaskExecutionResult(status="failed", reason="runtime_backlog_sync_failed")
                            log_event(
                                self.log_path,
                                "WARN",
                                "task marked done in runtime worktree backlog after non-completed monitor result",
                                task_id=task_id,
                                monitor_result=result,
                                base_backlog_path=str(base_backlog_path),
                                runtime_backlog_path=str(runtime_backlog_path),
                            )
                        stage_failure, stage_next_index, stage_completed_final = _complete_stage(
                            current_task_id=task_id,
                            current_task_text=task_text,
                            current_tag=tag,
                            current_monitor=active_monitor,
                            current_stage_id=stage_id,
                            current_stage_index=stage_index,
                            current_stage_is_final=stage_is_final,
                            current_attempt_number=attempt_number,
                            current_attempt_started_ms=attempt_started_ms,
                            completion_reason="runtime_backlog_marked_done",
                        )
                        if stage_failure is not None:
                            if _should_retry_after_missing_stage_artifact(
                                stage_failure=stage_failure,
                                monitor_result=result,
                                current_stage_id=stage_id,
                                retry_budget_left=missing_artifact_retry_budget,
                            ):
                                missing_artifact_retry_budget -= 1
                                log_event(
                                    self.log_path,
                                    "WARN",
                                    "runtime backlog marked done but stage artifact missing after process exit; retrying",
                                    task_id=task_id,
                                    stage_id=stage_id,
                                    monitor_result=result,
                                    reason=stage_failure.reason,
                                    retry_budget_left=missing_artifact_retry_budget,
                                )
                            else:
                                return stage_failure
                        else:
                            if stage_completed_final and request.task_path.exists():
                                try:
                                    request.task_path.unlink()
                                    delete_runtime_state_file(request.task_path, self.log_path, reason="runtime_backlog_marked_done")
                                except Exception as exc:
                                    log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                            if stage_completed_final:
                                return _finalize_completed(task_id, task_text, tag, active_monitor)
                            break
                except Exception as exc:
                    log_event(
                        self.log_path,
                        "ERROR",
                        "failed to inspect backlog completion after non-completed monitor result",
                        task_id=task_id,
                        monitor_result=result,
                        error=str(exc),
                    )

                restart_count += 1
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="agent_attempt",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    started_at_ms=attempt_started_ms,
                    result="restart",
                    reason=result,
                )
                if restart_count > request.max_restarts:
                    log_event(self.log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                    debug_log(
                        "H6",
                        "orc_core/task_execution.py:execute:max_restarts",
                        "max restarts exceeded",
                        {"task_id": task_id, "restart_count": restart_count, "max_restarts": request.max_restarts},
                    )
                    ui_error("❌ Агент не завершил задачу. Проверь логи.")
                    timeline_step_finished(
                        timeline_id=timeline_id,
                        task_id=task_id,
                        step="task_execute",
                        location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                        started_at_ms=execute_started_ms,
                        result="failed",
                        reason="max_restarts_exceeded",
                    )
                    return TaskExecutionResult(status="failed", reason="max_restarts_exceeded")
                log_event(self.log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
                reason_text = RESTART_REASON_TEXT.get(result, result)
                continue_vars = SafeDict(
                    task_text=task_text,
                    task_id=task_id,
                    backlog=request.backlog_arg,
                    workspace=request.workdir,
                    stage_id=stage_id,
                    stage_index=stage_index + 1,
                    stage_total=len(stage_specs),
                    stage_is_final=stage_is_final,
                    reason=reason_text,
                    restart_count=restart_count,
                    max_restarts=request.max_restarts,
                )
                prompt = request.continue_template.format_map(continue_vars)
                prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__r{restart_count}")
                resume_prompt_text = prompt
                delay = _restart_backoff_seconds(restart_count)
                log_event(self.log_path, "INFO", "restart backoff", task_id=task_id, restart_count=restart_count, delay_seconds=delay)
                backoff_started_ms = timeline_step_started(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="restart_backoff_sleep",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    data={"delay_seconds": delay},
                )
                time.sleep(delay)
                timeline_step_finished(
                    timeline_id=timeline_id,
                    task_id=task_id,
                    step="restart_backoff_sleep",
                    location="orc_core/task_execution.py:TaskExecutionEngine.execute",
                    attempt=attempt_number,
                    started_at_ms=backoff_started_ms,
                    result="completed",
                )
            if stage_next_index is None:
                break
            stage_index = stage_next_index

        timeline_step_finished(
            timeline_id=timeline_id,
            task_id=task_id,
            step="task_execute",
            location="orc_core/task_execution.py:TaskExecutionEngine.execute",
            started_at_ms=execute_started_ms,
            result="failed",
            reason="no_final_stage_completion",
        )
        return TaskExecutionResult(status="failed", reason="no_final_stage_completion")

    async def execute_async(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        return await asyncio.to_thread(self.execute, request)
