#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import asyncio
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol

from .hooks import update_task_restart_count, write_task_file
from .logging import debug_log, log_event
from .notify import send_telegram_message
from .process import (
    ORPHAN_SWEEP_COMMAND_MARKERS,
    build_process_tree,
    is_pid_alive,
    kill_orphan_project_processes,
    kill_process_tree,
)
from .process_groups import terminate_process_group
from .quit_signal import is_stop_requested
from .runner import launch_agent_stream_json
from .stream_monitor_state import MonitorSnapshot
from .supervisor_lifecycle import wait_for_completion, wait_for_process_exit
from .task_source import Task
from .text_parse import clean_summary_lines
from .ui import ui_error, ui_info, ui_warn
from .worktree_flow import get_head_commit, integrate_commit_into_main

GIT_COMMAND_TIMEOUT_SECONDS = 20.0


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


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
        agent_output_log_path: Optional[str] = None,
        agent_env: Optional[Mapping[str, str]] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        resume_id: Optional[str] = None,
        resume_latest: bool = False,
        resume_prompt: Optional[str] = None,
    ):
        ...


class AgentTaskWorker:
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
        agent_output_log_path: Optional[str] = None,
        agent_env: Optional[Mapping[str, str]] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
        resume_id: Optional[str] = None,
        resume_latest: bool = False,
        resume_prompt: Optional[str] = None,
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
            agent_output_log_path=agent_output_log_path,
            agent_env=agent_env,
            snapshot_publisher=snapshot_publisher,
            resume_id=resume_id,
            resume_latest=resume_latest,
            resume_prompt=resume_prompt,
        )


RESTART_REASON_TEXT = {
    "stalled": "Ты перестал выдавать результат (завис). Переоцени свой подход.",
    "ttl_exceeded": "Ты превысил лимит времени. Сделай коммит текущего прогресса или выбери более простой путь.",
    "process_exited": "Твой процесс неожиданно завершился (возможно, ошибка синтаксиса в bash).",
}


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


def _build_completion_message(*, task_id: str, workdir: str, summary_text: str, log_path: Path) -> str:
    header = f"✅ Задача завершена: {task_id}"
    task_report = _read_task_report_text(workdir, task_id, log_path)
    if task_report:
        return f"{header}\n\n{task_report}"
    normalized_summary = _normalize_fragmented_summary_text(summary_text)
    if normalized_summary:
        return f"{header}\n\n{normalized_summary}"
    return f"{header}\n\n(Отчёт отсутствует: пустой tasks/{task_id}.md и пустой summary.)"


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


def _has_commits_ahead_of_branch(workdir: str, branch: str, log_path: Path) -> bool:
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


def _run_commit_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
) -> bool:
    ok, porcelain = _git_status_porcelain(request.workdir, log_path)
    if ok and not porcelain.strip():
        log_event(log_path, "INFO", "commit phase skipped: clean tree", task_id=task_id)
        ui_info("[orc] commit phase: skip (clean tree)")
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
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "commit phase launch failed", task_id=task_id, error=str(exc))
        ui_error(f"[orc] commit phase: launch failed ({type(exc).__name__})")
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
            escape_requested=is_stop_requested,
        )
    finally:
        monitor.stop()
        _cleanup_monitor_processes(monitor, log_path, label="commit-phase")

    if result != "completed":
        log_event(log_path, "ERROR", "commit phase failed", task_id=task_id, result=result)
        ui_error(f"[orc] commit phase: failed ({result})")
        return False

    ok2, porcelain2 = _git_status_porcelain(request.workdir, log_path)
    if ok2 and porcelain2.strip():
        tracked, untracked = _parse_git_porcelain(porcelain2)
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
            return True

        if tracked:
            task_text = str(prompt_vars.get("task_text") or "").strip()
            if request.allow_fallback_commits:
                ui_warn("[orc] commit phase: tracked changes remain; attempting fallback commit")
                if not _attempt_autocommit_fallback(request.workdir, log_path, task_id=task_id, task_text=task_text):
                    ui_error("[orc] commit phase: fallback commit failed")
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
                        return False
                    ui_warn("[orc] commit phase: completed (untracked leftovers remain)")
                    return True
                log_event(log_path, "INFO", "commit phase completed after fallback", task_id=task_id)
                ui_info("[orc] commit phase: completed")
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
            return False
        ui_warn("[orc] commit phase: completed (untracked leftovers remain)")
        return True

    log_event(log_path, "INFO", "commit phase completed", task_id=task_id)
    ui_info("[orc] commit phase: completed")
    return True


def _run_merge_expert_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
    agent_output_log_path: Optional[str],
) -> bool:
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
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "merge expert phase launch failed", task_id=task_id, error=str(exc))
        ui_error(f"[orc] merge expert phase: launch failed ({type(exc).__name__})")
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
            escape_requested=is_stop_requested,
        )
    finally:
        monitor.stop()
        _cleanup_monitor_processes(monitor, log_path, label="merge-expert-phase")

    if result != "completed":
        log_event(log_path, "ERROR", "merge expert phase failed", task_id=task_id, result=result)
        ui_error(f"[orc] merge expert phase: failed ({result})")
        return False
    log_event(log_path, "INFO", "merge expert phase completed", task_id=task_id)
    ui_info("[orc] merge expert phase: completed")
    return True


class TaskExecutionEngine:
    def __init__(self, *, worker: Optional[TaskWorker] = None, log_path: Path) -> None:
        self.worker = worker or AgentTaskWorker()
        self.log_path = log_path

    def execute(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        task_id = request.task.task_id
        task_text = request.task.text
        base_backlog_path = request.backlog_path
        runtime_backlog_path = _resolve_runtime_backlog_path(request)
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
        resume_existing = request.task_path.exists()
        resume_id: Optional[str] = None

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
            debug_log(
                "H8",
                "orc_core/task_execution.py:execute:summary",
                "summary prepared",
                {
                    "summary_len": len(summary_text),
                    "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
                },
            )
            completion_message = _build_completion_message(
                task_id=current_task_id,
                workdir=request.workdir,
                summary_text=summary_text,
                log_path=self.log_path,
            )
            send_telegram_message(completion_message, self.log_path)
            prompt_vars = SafeDict(
                task_text=current_task_text,
                task_id=current_task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
            )
            if request.commit_phase and not _run_commit_phase(
                self.worker,
                request,
                prompt_vars,
                current_task_id,
                current_tag,
                self.log_path,
                effective_agent_output_log_path,
            ):
                ui_error("❌ Commit phase failed. Stop to avoid accumulating uncommitted changes.")
                return TaskExecutionResult(status="failed", reason="commit_phase_failed")
            if request.commit_phase:
                commit_completed = True

            if request.integrate_to_main:
                if not _has_commits_ahead_of_branch(request.workdir, request.main_branch, self.log_path):
                    log_event(
                        self.log_path,
                        "INFO",
                        "main integration skipped: no task commit ahead of main",
                        task_id=current_task_id,
                        branch=request.main_branch,
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
                    if not _run_merge_expert_phase(
                        self.worker,
                        request,
                        merge_prompt_vars,
                        current_task_id,
                        current_tag,
                        self.log_path,
                        effective_agent_output_log_path,
                    ):
                        return TaskExecutionResult(status="failed", reason="merge_expert_phase_failed")
                    integration = integrate_commit_into_main(
                        base_workdir=request.base_workdir,
                        commit_sha=commit_sha,
                        task_id=current_task_id,
                        log_path=self.log_path,
                        main_branch=request.main_branch,
                    )
                if not integration.ok:
                    log_event(
                        self.log_path,
                        "ERROR",
                        "failed to integrate task commit into main",
                        task_id=current_task_id,
                        commit_sha=commit_sha,
                        error=integration.error[:500],
                    )
                    ui_error(f"❌ Не удалось перенести commit в {request.main_branch}: {integration.error}")
                    return TaskExecutionResult(status="failed", reason="main_integration_failed")
            try:
                from .task_source import MarkdownTaskSource

                base_done = MarkdownTaskSource(base_backlog_path).is_task_done(current_task_id)
                runtime_done = False
                if runtime_backlog_path != base_backlog_path:
                    runtime_done = MarkdownTaskSource(runtime_backlog_path).is_task_done(current_task_id)
                if runtime_done and not base_done:
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
                raw_active_seconds = active.get("active_seconds", 0.0)
                try:
                    persisted_restart_count = max(int(raw_restart_count), 0)
                except (TypeError, ValueError):
                    persisted_restart_count = 0
                try:
                    elapsed_before_start = max(float(raw_active_seconds), 0.0)
                except (TypeError, ValueError):
                    elapsed_before_start = 0.0
            except Exception as exc:
                log_event(self.log_path, "ERROR", "failed to read task file", error=str(exc))
                ui_warn(
                    f"⚠️ Не удалось прочитать {request.task_path}. "
                    "Исправь/удали файл состояния или запусти с --drop для чистого старта."
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
                    except Exception as exc:
                        log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                    return TaskExecutionResult(status="continue", reason="stale_done_task_file")

            if resume_existing:
                task_id = active_task_id or task_id
                task_text = active_task_text or task_text
                log_event(self.log_path, "INFO", "resume existing task", task_id=task_id)
                ui_info(f"↩️ Обнаружена активная задача, запускаю resume для {task_id}.")
                if not resume_id:
                    missing_kind = "missing_key" if "conversation_id" not in active else "blank_value"
                    log_event(
                        self.log_path,
                        "ERROR",
                        "resume state invalid: conversation_id unavailable",
                        task_id=task_id,
                        missing_kind=missing_kind,
                        has_conversation_id_key=("conversation_id" in active),
                        raw_conversation_id_repr=repr(raw_conversation_id)[:120],
                    )
                    ui_error(
                        "❌ Resume state поврежден: отсутствует conversation_id в task file. "
                        "Запусти с --drop для намеренного перезапуска без resume."
                    )
                    return TaskExecutionResult(status="failed", reason="missing_conversation_id")
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
            write_task_file(request.base_workdir, request.task, request.backlog_path, self.log_path, restart_count=0)
            start_header = f"{task_id} — {task_text}" if task_text else task_id
            send_telegram_message(f"Старт задачи\n{start_header}", self.log_path)

        prompt_vars = SafeDict(task_text=task_text, task_id=task_id, backlog=request.backlog_arg, workspace=request.workdir)
        prompt = request.prompt_template.format_map(prompt_vars)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
        tag = f"{ts}__{safe_name}"
        prompt_path = _write_prompt_file(request.run_root, prompt, tag)
        resume_prompt_text = request.nudge_text if resume_existing else None

        restart_count = persisted_restart_count if resume_existing else 0
        while True:
            update_task_restart_count(request.task_path, self.log_path, restart_count)
            log_event(self.log_path, "INFO", "launching agent", task_id=task_id, restart_count=restart_count)
            try:
                active_monitor = self.worker.launch(
                    workdir=request.workdir,
                    prompt_path=prompt_path,
                    model=request.model,
                    log_path=self.log_path,
                    report_interval=request.report_interval,
                    summary_lines=request.summary_lines,
                    task_id=task_id,
                    progress_done=request.progress_done,
                    progress_total=request.progress_total,
                    agent_output_log_path=effective_agent_output_log_path,
                    agent_env=request.agent_env,
                    snapshot_publisher=request.snapshot_publisher,
                    resume_id=resume_id if resume_existing else None,
                    resume_latest=False,
                    resume_prompt=resume_prompt_text if resume_existing else None,
                )
            except FileNotFoundError:
                ui_error("❌ agent не найден. Установите Cursor CLI (agent) и попробуйте снова.")
                return TaskExecutionResult(status="failed", reason="agent_not_found")

            try:
                result = wait_for_completion(
                    task_path=request.task_path,
                    monitor=active_monitor,
                    poll=request.poll,
                    stall_timeout=request.stall_timeout,
                    task_ttl=request.task_ttl,
                    elapsed_before_start=elapsed_before_start,
                    log_path=self.log_path,
                    nudge_after=request.nudge_after,
                    nudge_cooldown=request.nudge_cooldown,
                    nudge_text=request.nudge_text,
                    task_id=task_id,
                    task_text=task_text,
                    escape_requested=is_stop_requested,
                )
            finally:
                active_monitor.stop()
                _cleanup_monitor_processes(active_monitor, self.log_path, label="agent")

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
                },
            )

            if result == "completed":
                return _finalize_completed(task_id, task_text, tag, active_monitor)
            if result == "waiting_for_input":
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
                    return TaskExecutionResult(status="failed", reason="max_restarts_exceeded")
                delay = max(request.nudge_cooldown, request.poll, 1.0)
                ui_warn(
                    f"[orc] агент запросил follow-up ввод; продолжу цикл через {delay:.1f}s "
                    "(resume сохранен, задача не потеряна)"
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
                        "task marked done after non-completed monitor result; treating as completed",
                        task_id=task_id,
                        monitor_result=result,
                    )
                    if request.task_path.exists():
                        try:
                            request.task_path.unlink()
                        except Exception as exc:
                            log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                    return _finalize_completed(task_id, task_text, tag, active_monitor)
                if runtime_done:
                    log_event(
                        self.log_path,
                        "WARN",
                        "task marked done in runtime worktree backlog after non-completed monitor result; treating as completed",
                        task_id=task_id,
                        monitor_result=result,
                        base_backlog_path=str(base_backlog_path),
                        runtime_backlog_path=str(runtime_backlog_path),
                    )
                    if request.task_path.exists():
                        try:
                            request.task_path.unlink()
                        except Exception as exc:
                            log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                    return _finalize_completed(task_id, task_text, tag, active_monitor)
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
            if restart_count > request.max_restarts:
                log_event(self.log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                debug_log(
                    "H6",
                    "orc_core/task_execution.py:execute:max_restarts",
                    "max restarts exceeded",
                    {"task_id": task_id, "restart_count": restart_count, "max_restarts": request.max_restarts},
                )
                ui_error("❌ Агент не завершил задачу. Проверь логи.")
                return TaskExecutionResult(status="failed", reason="max_restarts_exceeded")
            log_event(self.log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
            reason_text = RESTART_REASON_TEXT.get(result, result)
            continue_vars = SafeDict(
                task_text=task_text,
                task_id=task_id,
                backlog=request.backlog_arg,
                workspace=request.workdir,
                reason=reason_text,
                restart_count=restart_count,
                max_restarts=request.max_restarts,
            )
            prompt = request.continue_template.format_map(continue_vars)
            prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__r{restart_count}")
            resume_prompt_text = prompt
            delay = _restart_backoff_seconds(restart_count)
            log_event(self.log_path, "INFO", "restart backoff", task_id=task_id, restart_count=restart_count, delay_seconds=delay)
            time.sleep(delay)

    async def execute_async(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        return await asyncio.to_thread(self.execute, request)
