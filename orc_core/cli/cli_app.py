#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import atexit
import asyncio
import os
import signal
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from ..errors.exceptions import AgentNotInstalledError
from .agent_preflight import ensure_agent_installed
from ..backends.backend import SUPPORTED_BACKENDS, get_backend
from ..errors.failure_reasons import format_known_failure_message
from ..git.gitignore_guard import validate_workspace_gitignore
from ..log import log_event, set_log_context
from ..infra.io.logging import ORC_LOG_NAME
from ..infra.io.debug_log import init_debug_logging
from ..errors.crash_handler import emit_crash_stdout_payload, install_crash_handlers
from .model_selector import (
    DEFAULT_MODEL,
    ModelSelectionError,
    load_last_selected_model,
    save_last_selected_model,
)
from ..notifications.notify import send_telegram_message
from ..infra.process.process import acquire_lock, release_lock
from ..role_config import (
    ROLE_CODER,
    ROLE_HANDOFF,
    ROLE_MERGE_EXPERT,
    RoleProfileRegistry,
)
from ..tasks.ports import MonitorSnapshot
from ..tasks.execution.engine import TaskExecutionEngine
from .tui_app import OrcApp
from .ui import ui_error, ui_info, ui_warn
from ..git.worktree_flow import detect_base_branch
from ..infra.io.state_paths import app_log_path, lock_path as state_lock_path


def build_parser() -> argparse.ArgumentParser:
    from ..config import OrcConfig
    _d = OrcConfig()  # SSOT defaults
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--model", default="")
    ap.add_argument("--commit-model", default="", help="Optional model override for commit phase")
    ap.add_argument(
        "--commit-phase",
        action=argparse.BooleanOptionalAction,
        default=_d.commit_phase,
        help="Run a separate commit phase after each completed task (default: true)",
    )
    ap.add_argument("--commit-stall-timeout", type=float, default=_d.commit_stall_timeout, help="Commit stall timeout seconds")
    ap.add_argument("--commit-ttl", type=float, default=_d.commit_ttl, help="Max seconds for commit phase")
    ap.add_argument("--poll", type=float, default=_d.poll, help="Poll interval for task completion")
    ap.add_argument("--stall-timeout", type=float, default=_d.stall_timeout, help="Seconds without output before stall")
    ap.add_argument("--task-ttl", type=float, default=6 * 3600, help="Max seconds per task before abort")
    ap.add_argument("--max-restarts", type=int, default=_d.max_restarts, help="Max restarts for a task")
    ap.add_argument("--report-interval", type=float, default=_d.report_interval, help="Seconds between stats reports")
    ap.add_argument("--summary-lines", type=int, default=_d.summary_lines, help="Lines in Telegram summary")
    ap.add_argument("--nudge-after", type=int, default=_d.nudge_after, help="Send continue after N identical stats")
    ap.add_argument("--nudge-cooldown", type=float, default=_d.nudge_cooldown, help="Seconds between auto-nudges")
    ap.add_argument("--nudge-text", default=_d.nudge_text, help="Text to send before Enter")
    ap.add_argument("--telegram-test", nargs="?", const="orc telegram test", default=None, help="Test Telegram and exit")
    ap.add_argument("--reinit-hooks", action="store_true", help="Recreate hooks on startup")
    ap.add_argument("--hooks", action="store_true", help="Install agent hooks (default: off)")
    ap.add_argument("--max-sessions", type=int, default=0, help="Max parallel agent sessions (2-4, default: 4)")
    ap.add_argument("--init-kanban", action="store_true", help="Initialize kanban board folder structure and exit")
    ap.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging to the system temp directory",
    )
    ap.add_argument(
        "--agent-output-log",
        action="store_true",
        help="Write complete agent stdout/stderr to a log file",
    )
    ap.add_argument(
        "--backend",
        choices=list(SUPPORTED_BACKENDS),
        default="cursor",
        help="Agent backend to use (default: cursor)",
    )
    return ap


def _build_agent_output_log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    import tempfile
    return Path(tempfile.gettempdir()) / f"orc-agent-output-{stamp}.log"


def _failure_message(reason: str) -> str:
    normalized = str(reason or "").strip()
    if normalized == "model_unavailable":
        return (
            "Выбранная модель недоступна для локального `agent`."
            " Проверьте `agent --list-models` и запустите с доступной моделью через `--model`."
        )
    known_message = format_known_failure_message(normalized)
    if known_message:
        return known_message
    if normalized:
        return f"ORC завершился с ошибкой: {normalized}"
    return "ORC завершился с ошибкой без детали причины. Проверьте лог ORC."


def _atexit_kill_group() -> None:
    """Kill our entire process group on exit so no children survive."""
    # Ignore signals to prevent recursive handler invocation
    for sig_name in ("SIGTERM", "SIGHUP", "SIGQUIT", "SIGABRT", "SIGINT"):
        sig = getattr(signal, sig_name, None)
        if sig:
            try:
                signal.signal(sig, signal.SIG_IGN)
            except Exception:
                pass
    from ..infra.process.process_groups import kill_own_process_group
    kill_own_process_group()


def _resolve_model(args, workdir: str, role_registry: RoleProfileRegistry) -> str:
    """Resolve the effective model from CLI args, role config, or saved preference."""
    if str(args.model).strip():
        return args.model
    coder_config = role_registry.resolve_role(workdir, ROLE_CODER)
    return coder_config.model or load_last_selected_model(workdir) or DEFAULT_MODEL


def _resolve_templates(args, workdir: str, role_registry: RoleProfileRegistry) -> tuple[str, str, str, str]:
    """Resolve commit/merge templates. Returns (commit_model, commit_template, merge_model, merge_template)."""
    commit_template = ""
    merge_expert_template = ""
    merge_expert_model = ""
    commit_model = str(args.commit_model).strip()
    if args.commit_phase:
        handoff_config = role_registry.resolve_role(workdir, ROLE_HANDOFF, cli_model=commit_model)
        commit_model = handoff_config.model
        commit_template = handoff_config.prompt
    merge_expert_config = role_registry.resolve_role(workdir, ROLE_MERGE_EXPERT)
    merge_expert_model = merge_expert_config.model
    merge_expert_template = merge_expert_config.prompt
    return commit_model, commit_template, merge_expert_model, merge_expert_template


def _build_orchestrator(args, workdir: str, log_path: Path, backend, base_branch: str,
                        commit_template: str, merge_expert_template: str, merge_expert_model: str):
    """Composition root: construct the full dependency graph for KanbanSessionManager."""
    from ..board.kanban_init import init_kanban_board
    from ..agents.infra.composition import build_session_manager
    from ..config import OrcConfig
    from ..notifications.adapters import TelegramNotify
    from ..tasks.execution.worker import AgentTaskWorker

    engine = TaskExecutionEngine(
        worker=AgentTaskWorker(backend=backend),
        log_path=log_path,
        notify=TelegramNotify(log_path=log_path),
    )
    tasks_dir = init_kanban_board(Path(workdir))
    orc_config = OrcConfig.from_namespace(args)
    return build_session_manager(
        workdir=workdir,
        tasks_dir=tasks_dir,
        config=orc_config,
        log_path=log_path,
        engine=engine,
        backend=backend,
        commit_template=commit_template,
        merge_expert_template=merge_expert_template,
        merge_expert_model=merge_expert_model,
        main_branch=base_branch,
        max_sessions=max(2, min(int(getattr(args, "max_sessions", 0) or 4), 4)),
    )


def main() -> int:
    os.setpgrp()  # ORC becomes process group leader
    atexit.register(_atexit_kill_group)
    args = build_parser().parse_args()
    role_registry = RoleProfileRegistry()
    workdir = str(Path(args.workspace).resolve())
    set_log_context(workdir=workdir)
    base_branch = detect_base_branch(workdir)
    lock_path = state_lock_path(workdir)
    log_path = app_log_path(workdir)
    install_crash_handlers(
        entrypoint="orc_core.cli_app:main",
        phase="main",
        workspace=workdir,
        log_path=log_path,
    )
    lock_acquired = False

    backend = get_backend(getattr(args, "backend", "cursor") or "cursor")

    try:
        if args.telegram_test is not None:
            send_telegram_message(args.telegram_test, log_path)
            return 0

        if getattr(args, "init_kanban", False):
            from ..board.kanban_init import init_kanban_board
            tasks_dir = init_kanban_board(Path(workdir))
            ui_info(f"[orc] Kanban board initialized at {tasks_dir}")
            return 0

        try:
            ensure_agent_installed(backend)
        except AgentNotInstalledError as exc:
            ui_error(str(exc))
            return 2

        args.model = _resolve_model(args, workdir, role_registry)

        debug_log_path = init_debug_logging(enabled=bool(args.debug), workdir=workdir)
        if debug_log_path is not None:
            ui_info(f"[orc] debug log: {debug_log_path}")
            log_event(log_path, "INFO", "debug logging enabled", debug_log_path=str(debug_log_path))

        args.agent_output_log_path = ""
        if bool(args.agent_output_log):
            transcript_path = _build_agent_output_log_path()
            args.agent_output_log_path = str(transcript_path)
            ui_info(f"[orc] agent output log: {transcript_path}")

        # Validate workspace
        gitignore_ok, gitignore_error = validate_workspace_gitignore(workdir)
        if not gitignore_ok:
            log_event(log_path, "ERROR", "workspace gitignore validation failed", reason=gitignore_error)
            ui_error(f"❌ {gitignore_error}")
            return 2

        acquire_lock(lock_path, log_path)
        lock_acquired = True
        try:
            try:
                args.commit_model, commit_template, merge_expert_model, merge_expert_template = (
                    _resolve_templates(args, workdir, role_registry)
                )
            except FileNotFoundError as exc:
                log_event(log_path, "ERROR", "prompt file missing", error=str(exc))
                ui_error(str(exc))
                return 2

            manager = _build_orchestrator(
                args, workdir, log_path, backend, base_branch,
                commit_template, merge_expert_template, merge_expert_model,
            )

            def _run_orchestrator(snapshot_publisher: Callable[[str, MonitorSnapshot | None], None]) -> int:
                return asyncio.run(manager.run_async(snapshot_publisher))

            app = OrcApp(_run_orchestrator, session_manager=manager)
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
            elif exit_code not in (0, 130):
                ui_error(f"❌ {_failure_message(manager.last_failure_reason)}")
            if exit_code in (0, 130):
                print(f"\n{manager.get_summary()}", flush=True)
            return exit_code
        except KeyboardInterrupt:
            log_event(log_path, "WARN", "keyboard interrupt")
            ui_warn("⏹️ Прервано. Состояние сохранено.")
            return 130
        finally:
            if lock_acquired:
                release_lock(lock_path, log_path)
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


def main_multi() -> int:
    saved_argv = sys.argv[:]
    sys.argv = [sys.argv[0], "--max-sessions", "4"] + sys.argv[1:]
    try:
        return main()
    finally:
        sys.argv = saved_argv
