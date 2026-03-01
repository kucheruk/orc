#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import subprocess
from pathlib import Path
from typing import Callable, Optional

from .backlog_orchestrator import BacklogOrchestrator
from .hooks import (
    ensure_repo_hooks,
    ensure_repo_hooks_config,
)
from .logging import ORC_LOG_NAME, ORC_ROOT, debug_log, log_event
from .notify import send_telegram_message
from .process import acquire_lock, kill_process_tree, release_lock
from .runner import launch_agent_stream_json
from .task_state import (
    cleanup_stale_task_file as _cleanup_stale_task_file,
    create_temp_backlog as _create_temp_backlog,
    delete_task_file as _delete_task_file,
    load_task_payload as _load_task_payload,
)
from .supervisor_lifecycle import (
    wait_for_completion as lifecycle_wait_for_completion,
    wait_for_process_exit as lifecycle_wait_for_process_exit,
)
from .task_execution import TaskExecutionEngine
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


class SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _write_prompt_file(run_root: Path, prompt: str, tag: str) -> Path:
    prompt_dir = run_root / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{tag}.txt"
    prompt_path.write_text(prompt, encoding="utf-8")
    return prompt_path


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
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> str:
    return lifecycle_wait_for_completion(
        task_path=task_path,
        monitor=monitor,
        poll=poll,
        stall_timeout=stall_timeout,
        task_ttl=task_ttl,
        log_path=log_path,
        nudge_after=nudge_after,
        nudge_cooldown=nudge_cooldown,
        nudge_text=nudge_text,
        task_id=task_id,
        task_text=task_text,
        escape_requested=escape_requested,
        confirm_exit=confirm_exit,
    )


def wait_for_process_exit(
    monitor,
    poll: float,
    stall_timeout: float,
    task_ttl: float,
    log_path: Path,
    label: str,
    stop_on_followup_prompt: bool = False,
    escape_requested: Optional[Callable[[], bool]] = None,
    confirm_exit: Optional[Callable[[], bool]] = None,
) -> str:
    return lifecycle_wait_for_process_exit(
        monitor=monitor,
        poll=poll,
        stall_timeout=stall_timeout,
        task_ttl=task_ttl,
        log_path=log_path,
        label=label,
        stop_on_followup_prompt=stop_on_followup_prompt,
        escape_requested=escape_requested,
        confirm_exit=confirm_exit,
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
        engine = TaskExecutionEngine(log_path=orc_log_path)
        orchestrator = BacklogOrchestrator(
            workdir=workdir,
            backlog_path=backlog_path,
            args=args,
            task_path=task_path,
            run_root=run_root,
            log_path=orc_log_path,
            prompt_template=template,
            continue_template=continue_prompt,
            commit_template=commit_template,
            engine=engine,
        )
        return orchestrator.run()
    except KeyboardInterrupt:
        log_event(orc_log_path, "WARN", "keyboard interrupt")
        ui_warn("⏹️ Прервано. Состояние сохранено.")
        return 130
    finally:
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
