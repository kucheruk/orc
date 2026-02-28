#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from .escape_exit import EscapeExitWatcher
from .hooks import update_task_restart_count, write_task_file
from .logging import debug_log, log_event
from .process import kill_process_tree
from .runner import launch_agent_stream_json
from .supervisor_fallback import get_resume_id_from_agent_ls, update_task_conversation_id
from .supervisor_lifecycle import wait_for_completion, wait_for_process_exit
from .task_source import Task
from .text_parse import clean_summary_lines
from .ui import ui_error, ui_info, ui_warn


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
    run_root: Path
    model: str
    commit_model: str
    prompt_template: str
    continue_template: str
    commit_template: str
    commit_phase: bool
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


@dataclass(frozen=True)
class TaskExecutionResult:
    status: str
    reason: str = ""
    delay_seconds: float = 0.0


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
            resume_id=resume_id,
            resume_latest=resume_latest,
            resume_prompt=resume_prompt,
        )


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _git_status_porcelain(workdir: str, log_path: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
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
        )
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
    ok_add, _, _, _ = _git_run(workdir, log_path, ["git", "add", "-A"], label="commit_fallback:add_all")
    if not ok_add:
        return False

    ok_quiet, _, _, rc = _git_run(workdir, log_path, ["git", "diff", "--cached", "--quiet"], label="commit_fallback:cached_quiet")
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


def _run_commit_phase(
    worker: TaskWorker,
    request: TaskExecutionRequest,
    prompt_vars: SafeDict,
    task_id: str,
    tag: str,
    log_path: Path,
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

    monitor = worker.launch(
        workdir=request.workdir,
        prompt_path=prompt_path,
        model=request.commit_model,
        log_path=log_path,
        report_interval=15.0,
        summary_lines=25,
        task_id=f"{task_id}::commit",
    )
    try:
        with EscapeExitWatcher() as escape_watcher:
            result = wait_for_process_exit(
                monitor=monitor,
                poll=request.poll,
                stall_timeout=request.commit_stall_timeout,
                task_ttl=request.commit_ttl,
                log_path=log_path,
                label="commit_phase",
                stop_on_followup_prompt=True,
                escape_requested=escape_watcher.poll_escape,
                confirm_exit=escape_watcher.confirm_exit,
            )
    finally:
        monitor.stop()
        kill_process_tree(monitor.init_pid or monitor.proc.pid, log_path, label="commit-phase")

    if result not in {"completed", "followup_stuck"}:
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

        task_text = str(prompt_vars.get("task_text") or "").strip()
        if tracked:
            ui_warn("[orc] commit phase: finished but repo still dirty; attempting fallback commit")
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

    log_event(log_path, "INFO", "commit phase completed", task_id=task_id)
    ui_info("[orc] commit phase: completed")
    return True


class TaskExecutionEngine:
    def __init__(self, *, worker: Optional[TaskWorker] = None, log_path: Path) -> None:
        self.worker = worker or AgentTaskWorker()
        self.log_path = log_path

    def execute(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        task_id = request.task.task_id
        task_text = request.task.text
        resume_existing = request.task_path.exists()
        resume_id: Optional[str] = None

        debug_log(
            "H2",
            "orc_core/task_execution.py:execute:task_state",
            "task file state",
            {"task_path": str(request.task_path), "exists": resume_existing},
        )

        if resume_existing:
            try:
                active = json.loads(request.task_path.read_text(encoding="utf-8"))
                active_task_id = active.get("task_id")
                active_task_text = active.get("task_text")
                resume_id = (active.get("conversation_id") or "").strip() or None
            except Exception as exc:
                log_event(self.log_path, "ERROR", "failed to read task file", error=str(exc))
                ui_warn(f"⚠️ Не удалось прочитать {request.task_path}. Удали файл и запусти заново.")
                return TaskExecutionResult(status="continue", reason="task_file_read_failed", delay_seconds=max(request.poll, 0.2))

            if active_task_id and request.task_path.exists():
                from .task_source import MarkdownTaskSource

                if MarkdownTaskSource(request.backlog_path).is_task_done(active_task_id):
                    log_event(self.log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
                    ui_info(f"✅ {active_task_id} уже отмечена [x]. Удаляю {request.task_path} и продолжаю.")
                    try:
                        request.task_path.unlink()
                    except Exception as exc:
                        log_event(self.log_path, "ERROR", "failed to delete task file", error=str(exc))
                    return TaskExecutionResult(status="continue", reason="stale_done_task_file")

            task_id = active_task_id or task_id
            task_text = active_task_text or task_text
            log_event(self.log_path, "INFO", "resume existing task", task_id=task_id)
            ui_info(f"↩️ Обнаружена активная задача, запускаю resume для {task_id}.")
            if not resume_id:
                resume_id = get_resume_id_from_agent_ls(request.workdir, self.log_path)
                if resume_id:
                    update_task_conversation_id(request.task_path, self.log_path, resume_id)
                else:
                    ui_warn("⚠️ Resume ID не найден, сбрасываю state и запускаю задачу заново.")
                    try:
                        request.task_path.unlink()
                        resume_existing = False
                        log_event(
                            self.log_path,
                            "WARN",
                            "resume state reset: missing conversation_id",
                            task_id=task_id,
                            task_path=str(request.task_path),
                        )
                    except Exception as exc:
                        log_event(self.log_path, "ERROR", "failed to reset resume state", error=str(exc))
            log_event(
                self.log_path,
                "INFO",
                "resume selection",
                conversation_id=resume_id or "",
                resume_from_latest=False,
            )

        if not resume_existing:
            write_task_file(request.workdir, request.task, request.backlog_path, self.log_path, restart_count=0)

        prompt_vars = SafeDict(task_text=task_text, task_id=task_id, backlog=request.backlog_arg, workspace=request.workdir)
        prompt = request.prompt_template.format_map(prompt_vars)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
        tag = f"{ts}__{safe_name}"
        prompt_path = _write_prompt_file(request.run_root, prompt, tag)

        restart_count = 0
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
                    resume_id=resume_id if resume_existing else None,
                    resume_latest=False,
                    resume_prompt=request.nudge_text if resume_existing else None,
                )
            except FileNotFoundError:
                ui_error("❌ agent не найден. Установите Cursor CLI (agent) и попробуйте снова.")
                return TaskExecutionResult(status="failed", reason="agent_not_found")

            with EscapeExitWatcher() as escape_watcher:
                result = wait_for_completion(
                    task_path=request.task_path,
                    monitor=active_monitor,
                    poll=request.poll,
                    stall_timeout=request.stall_timeout,
                    task_ttl=request.task_ttl,
                    log_path=self.log_path,
                    nudge_after=request.nudge_after,
                    nudge_cooldown=request.nudge_cooldown,
                    nudge_text=request.nudge_text,
                    task_id=task_id,
                    task_text=task_text,
                    escape_requested=escape_watcher.poll_escape,
                    confirm_exit=escape_watcher.confirm_exit,
                )
            active_monitor.stop()
            kill_process_tree(active_monitor.init_pid or active_monitor.proc.pid, self.log_path, label="agent")

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
                log_event(self.log_path, "INFO", "task completed", task_id=task_id)
                raw_summary_text = active_monitor.get_summary_text()
                raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
                cleaned_lines = clean_summary_lines(raw_lines)
                summary_text = "\n".join(cleaned_lines[-request.summary_lines :])
                tokens = active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-"
                files_edited = active_monitor.metrics.files_edited if active_monitor.metrics.files_edited is not None else "-"
                ui_info(
                    f"[orc] completed stats tokens={tokens} lines={active_monitor.metrics.total_lines} "
                    f"commands={active_monitor.metrics.command_count} files_edited={files_edited}"
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
                if not summary_text.strip():
                    log_event(self.log_path, "WARN", "telegram summary empty", task_id=task_id)
                if request.commit_phase and not _run_commit_phase(self.worker, request, prompt_vars, task_id, tag, self.log_path):
                    ui_error("❌ Commit phase failed. Stop to avoid accumulating uncommitted changes.")
                    return TaskExecutionResult(status="failed", reason="commit_phase_failed")
                return TaskExecutionResult(status="completed")

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
            prompt = request.continue_template.format_map(prompt_vars)
            prompt_path = _write_prompt_file(request.run_root, prompt, f"{tag}__r{restart_count}")
