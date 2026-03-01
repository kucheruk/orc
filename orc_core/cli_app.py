#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .agent_preflight import AgentNotInstalledError, ensure_agent_installed
from .backlog_orchestrator import BacklogOrchestrator
from .backlog_status import inspect_backlog
from .logging import ORC_LOG_NAME, ORC_ROOT, emit_crash_stdout_payload, init_debug_logging, log_event, set_log_context
from .model_selector import (
    DEFAULT_MODEL,
    ModelListLoader,
    ModelSelectionError,
    load_last_selected_model,
    save_last_selected_model,
    start_model_list_loading,
)
from .notify import send_telegram_message
from .process import acquire_lock, release_lock
from .resume_state import resumable_task_id
from .start_menu import show_start_menu
from .supervisor import (
    COMMIT_PROMPT_PATH,
    CONTINUE_PROMPT_PATH,
    DEFAULT_PROMPT_PATH,
    _cleanup_stale_task_file,
    _create_temp_backlog,
    _delete_task_file,
    _load_task_payload,
    load_prompt,
)
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine
from .tui_app import OrcApp
from .ui import ui_error, ui_info, ui_warn

TASK_FILE_NAME = "orc-task.json"
LOCK_FILE_NAME = "orc.lock"


def _build_agent_output_log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(tempfile.gettempdir()) / f"orc-agent-output-{stamp}.log"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="BACKLOG.md")
    ap.add_argument("--task", default="", help="Run a one-off task by creating a temporary backlog")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--model", default="")
    ap.add_argument("--prompt-template", default="", help="Path to a custom prompt template file")
    ap.add_argument("--continue-template", default="", help="Path to a custom continue prompt file")
    ap.add_argument("--commit-template", default="", help="Path to a custom commit prompt template file")
    ap.add_argument("--commit-model", default="", help="Optional model override for commit phase")
    ap.add_argument(
        "--commit-phase",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run a separate commit phase after each completed task (default: true)",
    )
    ap.add_argument("--commit-stall-timeout", type=float, default=300.0, help="Commit stall timeout seconds")
    ap.add_argument("--commit-ttl", type=float, default=1800.0, help="Max seconds for commit phase")
    ap.add_argument(
        "--allow-fallback-commits",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Allow fallback autocommit when commit phase leaves tracked changes (default: false)",
    )
    ap.add_argument("--poll", type=float, default=1.0, help="Poll interval for task completion")
    ap.add_argument("--stall-timeout", type=float, default=600.0, help="Seconds without output before stall")
    ap.add_argument("--task-ttl", type=float, default=6 * 3600, help="Max seconds per task before abort")
    ap.add_argument("--max-restarts", type=int, default=2, help="Max restarts for a task")
    ap.add_argument("--report-interval", type=float, default=2.0, help="Seconds between stats reports")
    ap.add_argument("--summary-lines", type=int, default=25, help="Lines in Telegram summary")
    ap.add_argument("--nudge-after", type=int, default=10, help="Send continue after N identical stats")
    ap.add_argument("--nudge-cooldown", type=float, default=300.0, help="Seconds between auto-nudges")
    ap.add_argument("--nudge-text", default="continue", help="Text to send before Enter")
    ap.add_argument("--telegram-test", nargs="?", const="orc telegram test", default=None, help="Test Telegram and exit")
    ap.add_argument("--reinit-hooks", action="store_true", help="Recreate hooks on startup")
    ap.add_argument("--drop", action="store_true", help="Drop active task state and restart from scratch")
    ap.add_argument("--mode", choices=["backlog", "single", "prompt"], default="", help="Execution mode")
    ap.add_argument("--task-id", default="", help="Run exactly one backlog task by ID")
    ap.add_argument("--prompt", default="", help="Run one arbitrary prompt without requiring backlog")
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to the system temp directory (/.../orc)",
    )
    ap.add_argument(
        "--agent-output-log",
        action="store_true",
        help="Write complete agent stdout/stderr to the system temp directory (/.../orc-agent-output-<timestamp>.log)",
    )
    return ap


def _should_use_interactive_flow(args) -> bool:
    return not bool(args.mode or args.task_id.strip() or args.prompt.strip() or args.task.strip())


def _resolve_mode(
    args,
    backlog_path: Path,
    *,
    models: Optional[list[str]] = None,
    default_model: str = DEFAULT_MODEL,
    task_path: Optional[Path] = None,
    status_line: str = "",
) -> None:
    explicit_new_flow = bool(args.mode or args.task_id.strip() or args.prompt.strip())
    if explicit_new_flow:
        if not args.mode:
            args.mode = "prompt" if args.prompt.strip() else "single"
        return
    if args.task.strip():
        args.mode = "prompt"
        args.prompt = args.task.strip()
        return
    status = inspect_backlog(backlog_path)
    if not models:
        raise ModelSelectionError("Невозможно открыть стартовый экран: список моделей пуст.")
    resume_task_id = _resumable_task_id(task_path, backlog_path) if task_path is not None else ""
    choice = show_start_menu(
        status,
        models=models,
        default_model=default_model,
        resume_task_id=resume_task_id,
        status_line=status_line,
    )
    args.mode = "backlog" if choice.mode == "resume" else choice.mode
    args.debug = bool(args.debug or choice.debug_enabled)
    args.model = choice.model
    if choice.task_id:
        args.task_id = choice.task_id
    if choice.prompt_text:
        args.prompt = choice.prompt_text


def _resolve_model(args, workdir: str, *, interactive_requested: bool, model_loader: Optional[ModelListLoader]) -> None:
    if not interactive_requested:
        if str(args.model).strip():
            return
        args.model = DEFAULT_MODEL
        return
    if str(args.model).strip():
        save_last_selected_model(workdir, args.model)
        return
    raise ModelSelectionError("Интерактивный запуск требует выбранной модели со стартового экрана.")


def _resumable_task_id(task_path: Path, backlog_path: Path) -> str:
    return resumable_task_id(task_path, backlog_path)


def _resolve_backlog(args, workdir: str, log_path: Path) -> tuple[Path, Optional[Path]]:
    temp_backlog_path: Optional[Path] = None
    backlog_path = Path(workdir) / args.backlog
    if args.mode == "prompt":
        prompt_text = args.prompt.strip()
        if not prompt_text:
            raise ValueError("Prompt mode requires non-empty --prompt")
        backlog_path, rel_backlog = _create_temp_backlog(workdir, prompt_text, log_path)
        temp_backlog_path = backlog_path
        args.backlog = rel_backlog
        args.task = prompt_text
        args.task_id = ""
        ui_info(f"[orc] prompt mode: temporary backlog {backlog_path}")
    return backlog_path, temp_backlog_path


def _validate_inputs(args, backlog_path: Path) -> bool:
    if args.mode in {"backlog", "single"} and not backlog_path.exists():
        ui_error(f"Backlog not found: {backlog_path}")
        return False
    if args.mode == "single" and not args.task_id.strip():
        ui_error("Single mode requires --task-id (or choose task in interactive menu)")
        return False
    return True


def _failure_message(reason: str) -> str:
    normalized = str(reason or "").strip()
    if normalized == "missing_conversation_id":
        return (
            "Resume state повреждён: в `.cursor/orc-task.json` отсутствует `conversation_id`."
            " Запустите с `--drop` для чистого старта или удалите файл состояния вручную."
        )
    if normalized:
        return f"ORC завершился с ошибкой: {normalized}"
    return "ORC завершился с ошибкой без детали причины. Проверьте `.orc/orc.log`."


def main() -> int:
    args = build_parser().parse_args()
    workdir = str(Path(args.workspace).resolve())
    set_log_context(workdir=workdir)
    lock_path = Path(workdir) / ".orc" / LOCK_FILE_NAME
    log_path = ORC_ROOT / ".orc" / ORC_LOG_NAME
    task_path = Path(workdir) / ".cursor" / TASK_FILE_NAME
    temp_backlog_path: Optional[Path] = None
    lock_acquired = False

    try:
        if args.telegram_test is not None:
            send_telegram_message(args.telegram_test, log_path)
            return 0

        try:
            ensure_agent_installed()
        except AgentNotInstalledError as exc:
            ui_error(str(exc))
            return 2

        interactive_requested = _should_use_interactive_flow(args)
        model_loader = start_model_list_loading() if interactive_requested else None

        last_model = str(args.model).strip() or load_last_selected_model(workdir) or DEFAULT_MODEL
        models = model_loader.result(timeout=30.0) if model_loader is not None else [DEFAULT_MODEL]
        status_line = ""
        while True:
            initial_backlog_path = Path(workdir) / args.backlog
            if interactive_requested:
                _resolve_mode(
                    args,
                    initial_backlog_path,
                    models=models,
                    default_model=last_model,
                    task_path=task_path,
                    status_line=status_line,
                )
                status_line = ""
            else:
                _resolve_mode(args, initial_backlog_path)
            last_model = str(args.model).strip() or last_model
            try:
                _resolve_model(args, workdir, interactive_requested=interactive_requested, model_loader=model_loader)
            except ModelSelectionError as exc:
                ui_error(f"❌ {exc}")
                return 2
            debug_log_path = init_debug_logging(enabled=bool(args.debug), workdir=workdir)
            if debug_log_path is not None:
                ui_info(f"[orc] debug log: {debug_log_path}")
                log_event(log_path, "INFO", "debug logging enabled", debug_log_path=str(debug_log_path))
            args.agent_output_log_path = ""
            if bool(args.agent_output_log):
                transcript_path = _build_agent_output_log_path()
                args.agent_output_log_path = str(transcript_path)
                ui_info(f"[orc] agent output log: {transcript_path}")
                log_event(log_path, "INFO", "agent output logging enabled", agent_output_log_path=str(transcript_path))
            backlog_path, temp_backlog_path = _resolve_backlog(args, workdir, log_path)
            if not _validate_inputs(args, backlog_path):
                return 2

            _cleanup_stale_task_file(task_path, log_path, allowed_backlog=backlog_path)
            acquire_lock(lock_path, log_path)
            lock_acquired = True
            try:
                try:
                    template = load_prompt(Path(args.prompt_template)) if args.prompt_template else load_prompt(DEFAULT_PROMPT_PATH)
                    continue_template = load_prompt(Path(args.continue_template)) if args.continue_template else load_prompt(CONTINUE_PROMPT_PATH)
                    commit_template = ""
                    if args.commit_phase:
                        commit_template = load_prompt(Path(args.commit_template)) if args.commit_template else load_prompt(COMMIT_PROMPT_PATH)
                except FileNotFoundError as exc:
                    log_event(log_path, "ERROR", "prompt file missing", error=str(exc))
                    ui_error(str(exc))
                    return 2

                run_root = Path(workdir) / ".orc" / "backlog-run"
                engine = TaskExecutionEngine(log_path=log_path)
                orchestrator = BacklogOrchestrator(
                    workdir=workdir,
                    backlog_path=backlog_path,
                    args=args,
                    task_path=task_path,
                    run_root=run_root,
                    log_path=log_path,
                    prompt_template=template,
                    continue_template=continue_template,
                    commit_template=commit_template,
                    engine=engine,
                )

                def _run_orchestrator(snapshot_publisher: Callable[[MonitorSnapshot], None]) -> int:
                    orchestrator.snapshot_publisher = snapshot_publisher
                    return asyncio.run(orchestrator.run_async())

                app = OrcApp(_run_orchestrator)
                result = app.run(mouse=False)
                exit_code = int(result if result is not None else 1)
                if app.last_error:
                    crash_payload = emit_crash_stdout_payload(
                        entrypoint="orc_core.cli_app:main",
                        phase="orchestrator.run_async",
                        exception_type="OrchestratorUnhandledException",
                        error="orchestrator crashed",
                        traceback_text=app.last_error,
                        workspace=workdir,
                    )
                    log_event(log_path, "ERROR", "orchestrator crashed", **crash_payload)
                    ui_error("❌ ORC завершился из-за необработанной ошибки. Traceback:")
                    print(app.last_error, file=sys.stderr, flush=True)
                elif exit_code != 0:
                    ui_error(f"❌ {_failure_message(orchestrator.last_failure_reason)}")
                if interactive_requested and exit_code == 0 and str(args.mode).strip() == "single":
                    completed_task_id = str(args.task_id).strip()
                    status_line = f"Задача {completed_task_id} завершена успешно" if completed_task_id else "Задача завершена успешно"
                    args.mode = ""
                    args.task_id = ""
                    args.prompt = ""
                    args.task = ""
                    continue
                return exit_code
            except KeyboardInterrupt:
                log_event(log_path, "WARN", "keyboard interrupt")
                ui_warn("⏹️ Прервано. Состояние сохранено.")
                return 130
            finally:
                if lock_acquired:
                    release_lock(lock_path, log_path)
                lock_acquired = False
                if temp_backlog_path is not None and task_path.exists():
                    payload = _load_task_payload(task_path)
                    task_backlog = str(payload.get("backlog_path") or "").strip()
                    if not task_backlog or Path(task_backlog) == temp_backlog_path or not Path(task_backlog).exists():
                        _delete_task_file(task_path, log_path, reason="one_off_final_cleanup")
                if temp_backlog_path is not None and temp_backlog_path.exists():
                    try:
                        temp_backlog_path.unlink()
                        log_event(log_path, "INFO", "temporary backlog removed", backlog_path=str(temp_backlog_path))
                    except Exception as exc:
                        log_event(log_path, "WARN", "failed to remove temporary backlog", error=str(exc), backlog_path=str(temp_backlog_path))
    except KeyboardInterrupt:
        log_event(log_path, "WARN", "keyboard interrupt")
        ui_warn("⏹️ Прервано. Состояние сохранено.")
        return 130
    except Exception as exc:
        traceback_text = traceback.format_exc()
        crash_payload = emit_crash_stdout_payload(
            entrypoint="orc_core.cli_app:main",
            phase="main",
            exception_type=type(exc).__name__,
            error=str(exc),
            traceback_text=traceback_text,
            workspace=workdir,
        )
        log_event(log_path, "ERROR", "cli main crashed", **crash_payload)
        ui_error("❌ ORC завершился из-за необработанной ошибки.")
        print(traceback_text, file=sys.stderr, flush=True)
        return 1
