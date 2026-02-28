#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .backlog import render_progress
from .hooks import (
    ensure_repo_hooks,
    ensure_repo_hooks_config,
    update_task_restart_count,
    write_task_file,
)
from .logging import ORC_LOG_NAME, ORC_ROOT, debug_log, log_event
from .notify import send_telegram_message
from .process import acquire_lock, kill_process_tree, release_lock
from .runner import launch_agent_stream_json
from .task_source import MarkdownTaskSource, Task
from .text_parse import clean_summary_lines
from .ui import ui_error, ui_info, ui_warn

TASK_FILE_NAME = "orc-task.json"
LOCK_FILE_NAME = "orc.lock"

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_PATH = BASE_DIR / "prompts" / "default.txt"
CONTINUE_PROMPT_PATH = BASE_DIR / "prompts" / "continue.txt"
COMMIT_PROMPT_PATH = BASE_DIR / "prompts" / "commit.txt"


def load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def _create_temp_backlog(workdir: str, task_text: str, log_path: Path) -> tuple[Path, str]:
    run_dir = Path(workdir) / ".orc" / "tmp"
    run_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backlog_path = run_dir / f"BACKLOG.temp.{ts}.md"
    normalized = " ".join(task_text.strip().split())
    task_id = "ORC-SMOKE-001"
    backlog_path.write_text(f"- [ ] {task_id} {normalized}\n", encoding="utf-8")
    rel_backlog = str(backlog_path.relative_to(Path(workdir)))
    log_event(log_path, "INFO", "temporary backlog created", backlog_path=str(backlog_path), task_id=task_id)
    return backlog_path, rel_backlog


def _load_task_payload(task_path: Path) -> dict:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _delete_task_file(
    task_path: Path,
    log_path: Path,
    reason: str,
    expected_task_id: Optional[str] = None,
    expected_backlog: Optional[Path] = None,
) -> bool:
    if not task_path.exists():
        return False
    payload = _load_task_payload(task_path)
    if expected_task_id and str(payload.get("task_id") or "").strip() != expected_task_id:
        log_event(
            log_path,
            "WARN",
            "skip task file remove: task_id mismatch",
            reason=reason,
            expected_task_id=expected_task_id,
            actual_task_id=str(payload.get("task_id") or ""),
        )
        return False
    if expected_backlog is not None:
        actual_backlog = str(payload.get("backlog_path") or "").strip()
        if actual_backlog and Path(actual_backlog) != expected_backlog:
            log_event(
                log_path,
                "WARN",
                "skip task file remove: backlog mismatch",
                reason=reason,
                expected_backlog=str(expected_backlog),
                actual_backlog=actual_backlog,
            )
            return False
    try:
        task_path.unlink()
        log_event(log_path, "WARN", "task file removed", reason=reason, task_path=str(task_path))
        return True
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to remove task file", reason=reason, error=str(exc), task_path=str(task_path))
        return False


def _cleanup_stale_task_file(task_path: Path, log_path: Path, allowed_backlog: Optional[Path] = None) -> bool:
    """
    Remove broken or stale task state that can block orchestrator startup/resume.
    """
    if not task_path.exists():
        return False
    payload = _load_task_payload(task_path)
    if not payload:
        return _delete_task_file(task_path, log_path, reason="invalid_task_json")
    backlog_path_raw = str(payload.get("backlog_path") or "").strip()
    if not backlog_path_raw:
        return _delete_task_file(task_path, log_path, reason="missing_backlog_path")
    backlog_path = Path(backlog_path_raw)
    if not backlog_path.exists():
        return _delete_task_file(task_path, log_path, reason="backlog_missing")
    if allowed_backlog is not None and backlog_path.resolve() != allowed_backlog.resolve():
        log_event(
            log_path,
            "WARN",
            "task file references another backlog; keeping state",
            task_backlog=str(backlog_path),
            allowed_backlog=str(allowed_backlog),
        )
    return False


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


def _update_task_conversation_id(task_path: Path, log_path: Path, conversation_id: str) -> None:
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to read task file for conversation_id update", error=str(exc))
        return
    if payload.get("conversation_id") == conversation_id:
        return
    payload["conversation_id"] = conversation_id
    try:
        task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log_event(log_path, "INFO", "stored conversation_id from agent ls", conversation_id=conversation_id)
    except Exception as exc:
        log_event(log_path, "ERROR", "failed to update conversation_id", error=str(exc))


def _parse_agent_ls_output(output: str) -> Optional[str]:
    uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
    generic_re = re.compile(r"\b[A-Za-z0-9_-]{8,}\b")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        lower = line.lower()
        if lower.startswith(("id", "title", "name")):
            continue
        uuid_match = uuid_re.search(line)
        if uuid_match:
            return uuid_match.group(0)
        for token in generic_re.findall(line):
            token_lower = token.lower()
            if token_lower in {"id", "title", "name", "today", "yesterday"}:
                continue
            if ":" in token and all(part.isdigit() for part in token.split(":") if part):
                continue
            if not any(ch.isdigit() for ch in token):
                continue
            return token
    return None


def _get_resume_id_from_agent_ls(workdir: str, log_path: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["agent", "ls"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "agent ls failed", error=str(exc))
        return None
    if result.returncode != 0:
        log_event(
            log_path,
            "ERROR",
            "agent ls returned non-zero",
            returncode=result.returncode,
            stderr=result.stderr[:500],
        )
        return None
    resume_id = _parse_agent_ls_output(result.stdout)
    if resume_id:
        log_event(log_path, "INFO", "agent ls resume id", conversation_id=resume_id)
    else:
        log_event(log_path, "WARN", "agent ls returned no resume id")
    return resume_id


def _invoke_stop_hook_fallback(workdir: str, task_path: Path, log_path: Path) -> bool:
    stop_hook = Path(workdir) / ".cursor" / "hooks" / "orc_stop.py"
    if not stop_hook.exists():
        log_event(log_path, "WARN", "fallback stop skipped: hook missing", hook=str(stop_hook))
        return False
    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "fallback stop: failed to read task file", error=str(exc))
        return False
    stdin_payload = {
        "status": "completed",
        "loop_count": 0,
        "conversation_id": payload.get("conversation_id") or "",
    }
    try:
        result = subprocess.run(
            ["python3", str(stop_hook)],
            cwd=workdir,
            input=json.dumps(stdin_payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception as exc:
        log_event(log_path, "ERROR", "fallback stop: hook invocation failed", error=str(exc))
        return False
    log_event(
        log_path,
        "WARN" if result.returncode != 0 else "INFO",
        "fallback stop invoked",
        returncode=result.returncode,
        stdout=(result.stdout or "")[:500],
        stderr=(result.stderr or "")[:500],
    )
    return result.returncode == 0


def wait_for_completion(
    task_path: Path,
    monitor,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    nudge_after: int,
    nudge_cooldown: float,
    nudge_text: str,
    task_id: str,
    task_text: str,
) -> str:
    start_time = time.time()
    last_stats_key: Optional[Tuple[int, int, int, int]] = None
    same_count = 0
    last_tokens_value: Optional[int] = None
    last_tokens_time = time.time()
    last_stuck_notice_time = 0.0
    followup_seen_at: Optional[float] = None
    fallback_invoked = False
    fallback_last_attempt = 0.0
    #region agent log
    debug_log(
        "H3",
        "orc_core/supervisor.py:wait_for_completion:start",
        "wait loop start",
        {
            "task_path": str(task_path),
            "exists": task_path.exists(),
            "stall_timeout": stall_timeout,
            "task_ttl": task_ttl,
            "poll": poll,
        },
    )
    #endregion
    while True:
        if not task_path.exists():
            log_event(log_path, "INFO", "task file removed; completion observed")
            #region agent log
            debug_log(
                "H3",
                "orc_core/supervisor.py:wait_for_completion:done",
                "task file removed",
                {"task_path": str(task_path)},
            )
            #endregion
            return "completed"
        monitor.maybe_report()
        stats_key = (
            monitor.metrics.total_lines,
            monitor.metrics.command_count,
            monitor.metrics.total_output_chars,
            int(monitor.metrics.tokens_total or 0),
        )
        tokens_value = monitor.metrics.tokens_total
        if tokens_value is not None:
            if last_tokens_value is None or tokens_value != last_tokens_value:
                last_tokens_value = tokens_value
                last_tokens_time = time.time()
            else:
                since_tokens = time.time() - last_tokens_time
                if since_tokens >= 300 and (time.time() - last_stuck_notice_time) >= 300:
                    last_stuck_notice_time = time.time()
                    stuck_msg = f"{task_id} — agent stuck (tokens unchanged 5m)"
                    if task_text:
                        stuck_msg = f"{task_id} — {task_text}\nagent stuck (tokens unchanged 5m)"
                    send_telegram_message(stuck_msg, log_path)
        if stats_key == last_stats_key:
            same_count += 1
        else:
            same_count = 0
            last_stats_key = stats_key
        if monitor.ui_followup_prompt:
            if followup_seen_at is None:
                followup_seen_at = time.time()
            # Cursor can stay on "Add a follow-up" despite task completion.
            # If backlog already has [x], invoke stop-hook fallback to clear stale task file.
            if not fallback_invoked and (time.time() - followup_seen_at) >= 20.0:
                try:
                    payload = json.loads(task_path.read_text(encoding="utf-8"))
                except Exception as exc:
                    log_event(log_path, "ERROR", "fallback stop: failed to parse task json", error=str(exc))
                    payload = {}
                backlog_path = payload.get("backlog_path")
                current_task_id = payload.get("task_id")
                if backlog_path and current_task_id and MarkdownTaskSource(Path(backlog_path)).is_task_done(str(current_task_id)):
                    log_event(
                        log_path,
                        "WARN",
                        "follow-up prompt stuck with done task; invoking fallback stop",
                        task_id=current_task_id,
                    )
                    fallback_invoked = _invoke_stop_hook_fallback(monitor.workdir, task_path, log_path)
                else:
                    log_event(
                        log_path,
                        "INFO",
                        "follow-up prompt visible but task not marked done yet",
                        task_id=current_task_id,
                    )
        else:
            followup_seen_at = None
        # Auto-continue removed (was unreliable and noisy).
        if getattr(monitor, "result_status", None) == "success":
            if not task_path.exists():
                return "completed"
            if getattr(monitor, "result_seen_at", None) and (time.time() - monitor.result_seen_at) >= 10.0:
                if not fallback_invoked or (time.time() - fallback_last_attempt) >= 5.0:
                    log_event(log_path, "WARN", "result success observed; invoking stop-hook fallback")
                    fallback_last_attempt = time.time()
                    fallback_invoked = _invoke_stop_hook_fallback(monitor.workdir, task_path, log_path)
                if not task_path.exists():
                    return "completed"
                # Hard safety-net: if backlog is already done (or missing), clear stale task file.
                payload = _load_task_payload(task_path)
                backlog_path_raw = str(payload.get("backlog_path") or "").strip()
                current_task_id = str(payload.get("task_id") or "").strip()
                if backlog_path_raw and current_task_id:
                    backlog_path = Path(backlog_path_raw)
                    if not backlog_path.exists():
                        _delete_task_file(
                            task_path,
                            log_path,
                            reason="result_success_backlog_missing",
                            expected_task_id=current_task_id,
                        )
                        return "completed"
                    if MarkdownTaskSource(backlog_path).is_task_done(current_task_id):
                        _delete_task_file(
                            task_path,
                            log_path,
                            reason="result_success_backlog_already_done",
                            expected_task_id=current_task_id,
                            expected_backlog=backlog_path,
                        )
                        return "completed"

        if monitor.proc.poll() is not None:
            log_event(log_path, "ERROR", "agent process exited while task still active", returncode=monitor.proc.returncode)
            #region agent log
            debug_log(
                "H4",
                "orc_core/supervisor.py:wait_for_completion:exit",
                "agent process exited early",
                {
                    "returncode": monitor.proc.returncode,
                    "task_exists": task_path.exists(),
                    "stderr_count": monitor.stderr_count,
                    "last_stderr_line": monitor.last_stderr_line,
                },
            )
            #endregion
            return "process_exited"
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", stall_seconds=stall_timeout)
            #region agent log
            debug_log(
                "H5",
                "orc_core/supervisor.py:wait_for_completion:stall",
                "stall detected",
                {
                    "stall_seconds": stall_timeout,
                    "since_last_output": time.time() - monitor.last_output_time,
                    "lines": monitor.metrics.total_lines,
                    "task_exists": task_path.exists(),
                },
            )
            #endregion
            return "stalled"
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "task ttl exceeded", task_ttl=task_ttl)
            #region agent log
            debug_log(
                "H6",
                "orc_core/supervisor.py:wait_for_completion:ttl",
                "task ttl exceeded",
                {"task_ttl": task_ttl, "elapsed": time.time() - start_time},
            )
            #endregion
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))
    return "completed"


def wait_for_process_exit(
    monitor,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    label: str,
    stop_on_followup_prompt: bool = False,
) -> str:
    """
    Wait for the agent process to exit (used for non-task phases, e.g. commit).
    """
    start_time = time.time()
    followup_seen_at: Optional[float] = None
    followup_enter_sent = False
    followup_ctrlc_sent = False
    #region agent log
    debug_log(
        "H3",
        "orc_core/supervisor.py:wait_for_process_exit:start",
        "wait process exit loop start",
        {
            "stall_timeout": stall_timeout,
            "task_ttl": task_ttl,
            "poll": poll,
            "label": label,
            "stop_on_followup_prompt": stop_on_followup_prompt,
        },
    )
    #endregion
    while True:
        monitor.maybe_report()
        if stop_on_followup_prompt and getattr(monitor, "ui_followup_prompt", False):
            if followup_seen_at is None:
                followup_seen_at = time.time()
                log_event(log_path, "WARN", "follow-up prompt visible during phase", label=label)
            seen_for = time.time() - followup_seen_at
            # In Cursor this screen can be "sticky" even after work is complete. Nudge it.
            if seen_for >= 10.0 and not followup_enter_sent:
                followup_enter_sent = True
                monitor.send_keys(["Enter"], label=f"{label}:followup:enter")
            if seen_for >= 20.0 and not followup_ctrlc_sent:
                followup_ctrlc_sent = True
                monitor.send_keys(["C-C"], label=f"{label}:followup:ctrlc")
            if seen_for >= 40.0:
                log_event(log_path, "WARN", "follow-up prompt stuck; forcing phase end", label=label)
                return "followup_stuck"
        else:
            followup_seen_at = None
        if monitor.proc.poll() is not None:
            log_event(
                log_path,
                "INFO" if monitor.proc.returncode == 0 else "ERROR",
                "phase process exited",
                label=label,
                returncode=monitor.proc.returncode,
            )
            return "completed" if monitor.proc.returncode == 0 else "process_exited"
        if time.time() - monitor.last_output_time > stall_timeout:
            log_event(log_path, "ERROR", "stall detected", label=label, stall_seconds=stall_timeout)
            return "stalled"
        if time.time() - start_time > task_ttl:
            log_event(log_path, "ERROR", "phase ttl exceeded", label=label, task_ttl=task_ttl)
            return "ttl_exceeded"
        time.sleep(max(poll, 0.2))


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
    """
    Best-effort fallback when commit phase leaves tracked changes behind.
    The goal is to be resilient and avoid stopping the whole backlog run.
    """
    ok_add, _, _, _ = _git_run(workdir, log_path, ["git", "add", "-A"], label="commit_fallback:add_all")
    if not ok_add:
        return False

    # Nothing staged -> nothing to commit.
    ok_quiet, _, _, rc = _git_run(workdir, log_path, ["git", "diff", "--cached", "--quiet"], label="commit_fallback:cached_quiet")
    if ok_quiet:
        return True
    # Return code 1 means "diff exists" (i.e., something staged). Other codes are errors.
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
    workdir: str,
    run_root: Path,
    prompt_template: str,
    prompt_vars: SafeDict,
    model: str,
    log_path: Path,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    task_id: str,
    tag: str,
) -> bool:
    ok, porcelain = _git_status_porcelain(workdir, log_path)
    if ok and not porcelain.strip():
        log_event(log_path, "INFO", "commit phase skipped: clean tree", task_id=task_id)
        ui_info("[orc] commit phase: skip (clean tree)")
        return True

    prompt = prompt_template.format_map(prompt_vars)
    prompt_path = _write_prompt_file(run_root, prompt, f"{tag}__commit")
    log_event(log_path, "INFO", "commit phase starting", task_id=task_id, prompt_path=str(prompt_path), model=model)
    ui_info("[orc] commit phase: starting")

    monitor = launch_agent_stream_json(
        workdir,
        prompt_path,
        model,
        log_path,
        report_interval=15.0,
        summary_lines=25,
        task_id=f"{task_id}::commit",
    )
    try:
        result = wait_for_process_exit(
            monitor=monitor,
            poll=poll,
            stall_timeout=stall_timeout,
            task_ttl=task_ttl,
            log_path=log_path,
            label="commit_phase",
            stop_on_followup_prompt=True,
        )
    finally:
        monitor.stop()
        kill_process_tree(monitor.init_pid or monitor.proc.pid, log_path, label="commit-phase")

    if result not in {"completed", "followup_stuck"}:
        log_event(log_path, "ERROR", "commit phase failed", task_id=task_id, result=result)
        ui_error(f"[orc] commit phase: failed ({result})")
        return False

    ok2, porcelain2 = _git_status_porcelain(workdir, log_path)
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
        # If only untracked files remain, don't block the whole run.
        if not tracked and untracked:
            ui_warn("[orc] commit phase: warning (repo has untracked files)")
            return True

        # If tracked changes remain, try a best-effort fallback autocommit.
        task_text = str(prompt_vars.get("task_text") or "").strip()
        if tracked:
            ui_warn("[orc] commit phase: finished but repo still dirty; attempting fallback commit")
            if not _attempt_autocommit_fallback(workdir, log_path, task_id=task_id, task_text=task_text):
                ui_error("[orc] commit phase: fallback commit failed")
                return False

        ok3, porcelain3 = _git_status_porcelain(workdir, log_path)
        if ok3 and porcelain3.strip():
            tracked3, untracked3 = _parse_git_porcelain(porcelain3)
            # Allow untracked-only leftovers; fail if tracked changes remain.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="BACKLOG.md")
    ap.add_argument("--task", default="", help="Run a one-off task by creating a temporary backlog")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--model", default="gpt-5.2-codex")
    ap.add_argument("--prompt-template", default="", help="Path to a custom prompt template file")
    ap.add_argument("--continue-template", default="", help="Path to a custom continue prompt file")
    ap.add_argument(
        "--commit-template",
        default="",
        help="Path to a custom commit prompt template file (runs after each completed task)",
    )
    ap.add_argument("--commit-model", default="", help="Optional model override for commit phase")
    ap.add_argument(
        "--commit-phase",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run a separate commit phase after each completed task (default: true)",
    )
    ap.add_argument("--commit-stall-timeout", type=float, default=300.0, help="Seconds without output before commit stall")
    ap.add_argument("--commit-ttl", type=float, default=1800.0, help="Max seconds for commit phase before abort")
    ap.add_argument("--poll", type=float, default=1.0, help="Poll interval for task completion")
    ap.add_argument("--stall-timeout", type=float, default=600.0, help="Seconds without output before stall")
    ap.add_argument("--task-ttl", type=float, default=6 * 3600, help="Max seconds per task before abort")
    ap.add_argument("--max-restarts", type=int, default=2, help="Max restarts for a task")
    ap.add_argument("--report-interval", type=float, default=2.0, help="Seconds between stats reports")
    ap.add_argument("--summary-lines", type=int, default=25, help="Lines to send to Telegram after completion")
    ap.add_argument("--nudge-after", type=int, default=10, help="Send continue after N identical stats")
    ap.add_argument("--nudge-cooldown", type=float, default=300.0, help="Seconds between auto-nudges")
    ap.add_argument("--nudge-text", default="continue", help="Text to send before Enter")
    ap.add_argument("--telegram-test", nargs="?", const="orc telegram test", default=None, help="Send a test Telegram message and exit")
    ap.add_argument("--reinit-hooks", action="store_true", help="Recreate hooks on startup")
    ap.add_argument(
        "--drop",
        action="store_true",
        help="Drop active task state (.cursor/orc-task.json) and restart task from scratch (no resume)",
    )
    args = ap.parse_args()

    workdir = str(Path(args.workspace).resolve())
    orc_log_path = ORC_ROOT / ".orc" / ORC_LOG_NAME
    lock_path = Path(workdir) / ".orc" / LOCK_FILE_NAME
    temp_backlog_path: Optional[Path] = None

    if args.telegram_test is not None:
        send_telegram_message(args.telegram_test, orc_log_path)
        return 0

    if args.task.strip():
        backlog_path, rel_backlog = _create_temp_backlog(workdir, args.task, orc_log_path)
        temp_backlog_path = backlog_path
        args.backlog = rel_backlog
        ui_info(f"[orc] test mode: using temporary backlog {backlog_path}")
    else:
        backlog_path = Path(workdir) / args.backlog

    if args.reinit_hooks:
        before_path, stop_path = ensure_repo_hooks(workdir)
        hooks_path = ensure_repo_hooks_config(workdir, before_path, stop_path, orc_log_path)
        log_event(orc_log_path, "WARN", "hooks reinitialized", hooks_config=str(hooks_path))

    if not backlog_path.exists():
        ui_error(f"Backlog not found: {backlog_path}")
        return 2

    task_path = Path(workdir) / ".cursor" / TASK_FILE_NAME
    _cleanup_stale_task_file(task_path, orc_log_path, allowed_backlog=backlog_path)

    acquire_lock(lock_path, orc_log_path)
    active_monitor = None
    try:
        try:
            template = load_prompt(Path(args.prompt_template)) if args.prompt_template else load_prompt(DEFAULT_PROMPT_PATH)
            continue_prompt = load_prompt(Path(args.continue_template)) if args.continue_template else load_prompt(CONTINUE_PROMPT_PATH)
            commit_template = ""
            if args.commit_phase:
                commit_template = (
                    load_prompt(Path(args.commit_template)) if args.commit_template else load_prompt(COMMIT_PROMPT_PATH)
                )
        except FileNotFoundError as exc:
            log_event(orc_log_path, "ERROR", "prompt file missing", error=str(exc))
            return 2

        run_root = Path(workdir) / ".orc" / "backlog-run"
        drop_pending = bool(args.drop)
        drop_override: Optional[Tuple[str, str]] = None
        while True:
            task_source = MarkdownTaskSource(backlog_path)
            tasks = task_source.list_tasks()
            total = len(tasks)
            done = sum(1 for t in tasks if t.done)
            open_task = task_source.get_first_open_task()

            # One-shot drop: if there is an active task file, delete it and restart the task from scratch.
            # This is intentionally done before resume selection to avoid continuing an already-started task.
            if drop_pending and task_path.exists():
                drop_pending = False
                started_flag = False
                try:
                    active = json.loads(task_path.read_text(encoding="utf-8"))
                    active_task_id = (active.get("task_id") or "").strip()
                    active_task_text = (active.get("task_text") or "").strip()
                    conversation_id = str(active.get("conversation_id") or "").strip()
                    started_flag = bool(active.get("start_notified") or conversation_id)
                    if active_task_id:
                        drop_override = (active_task_id, active_task_text or active_task_id)
                except Exception as exc:
                    log_event(orc_log_path, "ERROR", "drop: failed to read task file (still deleting)", error=str(exc))
                try:
                    task_path.unlink()
                    log_event(
                        orc_log_path,
                        "WARN",
                        "drop: active task state deleted",
                        task_path=str(task_path),
                        started=started_flag,
                    )
                    if started_flag:
                        ui_warn("🧹 --drop: активная задача была начата; сбрасываю состояние и запускаю с нуля.")
                    else:
                        ui_warn("🧹 --drop: сбрасываю состояние активной задачи и запускаю с нуля.")
                except Exception as exc:
                    log_event(orc_log_path, "ERROR", "drop: failed to delete task file", error=str(exc))
                    ui_error(f"❌ --drop: не удалось удалить {task_path}: {exc}")
                    return 2
                if drop_override:
                    dropped_task_id, _ = drop_override
                    if dropped_task_id:
                        # Only restart "the same task" if it still exists in BACKLOG.md.
                        # If it was removed from backlog, proceed with the next open task (or exit).
                        dropped_task = next((t for t in tasks if t.task_id == dropped_task_id), None)
                        if dropped_task and not dropped_task.done:
                            open_task = dropped_task
                        else:
                            drop_override = None

            if not open_task:
                log_event(orc_log_path, "INFO", "backlog complete")
                ui_info("✅ BACKLOG.md: невыполненных пунктов не осталось. Выход.")
                return 0

            task_id = open_task.task_id
            task_text = open_task.text

            resume_existing = task_path.exists()
            resume_id: Optional[str] = None
            #region agent log
            debug_log(
                "H2",
                "orc_core/supervisor.py:main:task_state",
                "task file state",
                {"task_path": str(task_path), "exists": resume_existing},
            )
            #endregion
            if resume_existing:
                try:
                    active = json.loads(task_path.read_text(encoding="utf-8"))
                    active_task_id = active.get("task_id")
                    active_task_text = active.get("task_text")
                    resume_id = (active.get("conversation_id") or "").strip() or None
                    #region agent log
                    debug_log(
                        "H2",
                        "orc_core/supervisor.py:main:resume_existing",
                        "resume task loaded",
                        {"active_task_id": active_task_id, "task_text_len": len(active_task_text) if active_task_text else 0},
                    )
                    #endregion
                except Exception as exc:
                    log_event(orc_log_path, "ERROR", "failed to read task file", error=str(exc))
                    ui_warn(f"⚠️ Не удалось прочитать {task_path}. Удали файл и запусти заново.")
                    time.sleep(max(args.poll, 0.2))
                    continue
                if active_task_id and task_source.is_task_done(active_task_id):
                    log_event(orc_log_path, "INFO", "task already marked done; removing task file", task_id=active_task_id)
                    ui_info(f"✅ {active_task_id} уже отмечена [x]. Удаляю {task_path} и продолжаю.")
                    try:
                        task_path.unlink()
                    except Exception as exc:
                        log_event(orc_log_path, "ERROR", "failed to delete task file", error=str(exc))
                    continue
                # Файл актуален — используем его данные для resume
                task_id = active_task_id or task_id
                task_text = active_task_text or task_text
                log_event(orc_log_path, "INFO", "resume existing task", task_id=task_id)
                ui_info(f"↩️ Обнаружена активная задача, запускаю resume для {task_id}.")
                if not resume_id:
                    resume_id = _get_resume_id_from_agent_ls(workdir, orc_log_path)
                    if resume_id:
                        _update_task_conversation_id(task_path, orc_log_path, resume_id)
                log_event(
                    orc_log_path,
                    "INFO",
                    "resume selection",
                    conversation_id=resume_id or "",
                    resume_from_latest=resume_id is None,
                )

            short = (task_text[:120] + "…") if len(task_text) > 120 else task_text
            ui_info(f"▶️ Текущая задача: {task_id} — {short}")

            before_path, stop_path = ensure_repo_hooks(workdir)
            hooks_path = ensure_repo_hooks_config(workdir, before_path, stop_path, orc_log_path)
            log_event(orc_log_path, "INFO", "hooks ready", hooks_config=str(hooks_path))

            if not resume_existing:
                write_task_file(workdir, open_task, backlog_path, orc_log_path, restart_count=0)

            prompt_vars = SafeDict(task_text=task_text, task_id=task_id, backlog=args.backlog, workspace=workdir)
            prompt = template.format_map(prompt_vars)

            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", task_text)[:60]
            tag = f"{ts}__{safe_name}"
            prompt_path = _write_prompt_file(run_root, prompt, tag)

            restart_count = 0
            while True:
                update_task_restart_count(task_path, orc_log_path, restart_count)
                log_event(orc_log_path, "INFO", "launching agent", task_id=task_id, restart_count=restart_count)
                try:
                    active_monitor = launch_agent_stream_json(
                        workdir,
                        prompt_path,
                        args.model,
                        orc_log_path,
                        report_interval=args.report_interval,
                        summary_lines=args.summary_lines,
                        task_id=task_id,
                        progress_done=done,
                        progress_total=total,
                        resume_id=resume_id if resume_existing else None,
                        resume_latest=resume_existing and resume_id is None,
                        resume_prompt=args.nudge_text if resume_existing else None,
                    )
                except FileNotFoundError:
                    ui_error("❌ agent не найден. Установите Cursor CLI (agent) и попробуйте снова.")
                    return 2
                result = wait_for_completion(
                    task_path=task_path,
                    monitor=active_monitor,
                    poll=args.poll,
                    stall_timeout=args.stall_timeout,
                    task_ttl=args.task_ttl,
                    log_path=orc_log_path,
                    nudge_after=args.nudge_after,
                    nudge_cooldown=args.nudge_cooldown,
                    nudge_text=args.nudge_text,
                    task_id=task_id,
                    task_text=task_text,
                )
                active_monitor.stop()
                kill_process_tree(active_monitor.init_pid or active_monitor.proc.pid, orc_log_path, label="agent")
                #region agent log
                debug_log(
                    "H8",
                    "orc_core/supervisor.py:main:completion_state",
                    "completion state",
                    {
                        "result": result,
                        "monitor_is_none": active_monitor is None,
                        "lines": active_monitor.metrics.total_lines,
                        "commands": active_monitor.metrics.command_count,
                        "tokens_total": active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-",
                    },
                )
                #endregion
                if result == "completed":
                    log_event(orc_log_path, "INFO", "task completed", task_id=task_id)
                    raw_summary_text = active_monitor.get_summary_text()
                    raw_lines = raw_summary_text.splitlines() if raw_summary_text else []
                    cleaned_lines = clean_summary_lines(raw_lines)
                    summary_text = "\n".join(cleaned_lines[-args.summary_lines :])
                    tokens = active_monitor.metrics.tokens_total if active_monitor.metrics.tokens_total is not None else "-"
                    files_edited = active_monitor.metrics.files_edited if active_monitor.metrics.files_edited is not None else "-"
                    ui_info(
                        f"[orc] completed stats tokens={tokens} lines={active_monitor.metrics.total_lines} "
                        f"commands={active_monitor.metrics.command_count} files_edited={files_edited}"
                    )
                    #region agent log
                    debug_log(
                        "H8",
                        "orc_core/supervisor.py:main:summary",
                        "summary prepared",
                        {
                            "summary_len": len(summary_text),
                            "summary_lines": summary_text.count("\n") + 1 if summary_text else 0,
                        },
                    )
                    #endregion
                    # Telegram notifications are handled by hooks.
                    if not summary_text.strip():
                        log_event(orc_log_path, "WARN", "telegram summary empty", task_id=task_id)
                    active_monitor = None
                    if args.commit_phase:
                        commit_model = (args.commit_model or "").strip() or args.model
                        if not _run_commit_phase(
                            workdir=workdir,
                            run_root=run_root,
                            prompt_template=commit_template,
                            prompt_vars=prompt_vars,
                            model=commit_model,
                            log_path=orc_log_path,
                            poll=args.poll,
                            stall_timeout=args.commit_stall_timeout,
                            task_ttl=args.commit_ttl,
                            task_id=task_id,
                            tag=tag,
                        ):
                            ui_error("❌ Commit phase failed. Stop to avoid accumulating uncommitted changes.")
                            return 1
                    break
                active_monitor = None
                restart_count += 1
                if restart_count > args.max_restarts:
                    log_event(orc_log_path, "ERROR", "max restarts exceeded", task_id=task_id)
                    #region agent log
                    debug_log(
                        "H6",
                        "orc_core/supervisor.py:main:max_restarts",
                        "max restarts exceeded",
                        {"task_id": task_id, "restart_count": restart_count, "max_restarts": args.max_restarts},
                    )
                    #endregion
                    ui_error("❌ Агент не завершил задачу. Проверь логи.")
                    return 1
                log_event(orc_log_path, "WARN", "restarting task", task_id=task_id, restart_count=restart_count, reason=result)
                prompt = continue_prompt.format_map(prompt_vars)
                prompt_path = _write_prompt_file(run_root, prompt, f"{tag}__r{restart_count}")
            ui_info("[orc] pause 5s before next task (Ctrl+C to stop)")
            time.sleep(5)
    except KeyboardInterrupt:
        log_event(orc_log_path, "WARN", "keyboard interrupt")
        ui_warn("⏹️ Прервано. Состояние сохранено.")
        return 130
    finally:
        if active_monitor is not None:
            active_monitor.stop()
            kill_process_tree(active_monitor.init_pid or active_monitor.proc.pid, orc_log_path, label="agent-finalize")
        release_lock(lock_path, orc_log_path)
        # Final safety-net for one-off runs: never leave stale task state behind.
        if temp_backlog_path is not None and task_path.exists():
            payload = _load_task_payload(task_path)
            task_backlog = str(payload.get("backlog_path") or "").strip()
            if not task_backlog or Path(task_backlog) == temp_backlog_path or not Path(task_backlog).exists():
                _delete_task_file(task_path, orc_log_path, reason="one_off_final_cleanup")
        if temp_backlog_path is not None and temp_backlog_path.exists():
            try:
                temp_backlog_path.unlink()
                log_event(orc_log_path, "INFO", "temporary backlog removed", backlog_path=str(temp_backlog_path))
            except Exception as exc:
                log_event(orc_log_path, "WARN", "failed to remove temporary backlog", error=str(exc), backlog_path=str(temp_backlog_path))


if __name__ == "__main__":
    raise SystemExit(main())
