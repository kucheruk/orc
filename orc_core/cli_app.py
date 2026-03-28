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
from .session_manager import SessionManager
from .backlog_status import inspect_backlog
from .failure_reasons import format_known_failure_message
from .gitignore_guard import validate_workspace_gitignore
from .logging import (
    ORC_LOG_NAME,
    emit_crash_stdout_payload,
    init_debug_logging,
    install_crash_handlers,
    log_event,
    set_log_context,
)
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
from .role_config import (
    ROLE_ANALYSIS_PLANNING,
    ROLE_CODE_REVIEW,
    ROLE_CODER,
    ROLE_HANDOFF,
    ROLE_MERGE_EXPERT,
    ROLE_TESTER,
    ROLE_DESIGN,
    RoleProfileRegistry,
)
from .resume_state import resumable_task_id
from .start_menu import show_start_menu
from .supervisor import _cleanup_stale_task_file, _create_temp_backlog, _delete_task_file, _load_task_payload
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine, TaskStageSpec
from .tui_app import OrcApp
from .ui import ui_error, ui_info, ui_warn
from .worktree_flow import detect_base_branch
from .state_paths import active_task_path, app_log_path, lock_path as state_lock_path, run_root as state_run_root

def load_prompt(path: Path) -> str:
    # Backward-compatible shim for tests and legacy imports.
    return RoleProfileRegistry().load_prompt(path)


def _build_agent_output_log_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(tempfile.gettempdir()) / f"orc-agent-output-{stamp}.log"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="BACKLOG.md")
    ap.add_argument("--task", default="", help="Run a one-off task by creating a temporary backlog")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--model", default="")
    ap.add_argument(
        "--prompt-coder",
        default="",
        help="Path to a default coder prompt file (does not affect continue/commit/merge_expert phases)",
    )
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
    ap.add_argument(
        "--require-stage-artifacts",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Require non-empty SDLC stage artifacts before allowing stage completion (default: false)",
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
    ap.add_argument("--hooks", action="store_true", help="Install agent hooks (default: off, conversation_id captured from stream)")
    ap.add_argument("--max-sessions", type=int, default=1, help="Max parallel agent sessions (1-4, default: 1)")
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
    workdir: str = "",
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
        workdir=workdir or str(backlog_path.parent.resolve()),
    )
    args.mode = "backlog" if choice.mode == "resume" else choice.mode
    args.debug = bool(args.debug or choice.debug_enabled)
    args.model = choice.model
    args.task_id = choice.task_id if choice.mode == "single" else ""
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


def _validate_inputs(args, backlog_path: Path, workdir: str, log_path: Path) -> bool:
    if args.mode in {"backlog", "single"} and not backlog_path.exists():
        ui_error(f"Backlog not found: {backlog_path}")
        return False
    if args.mode == "single" and not args.task_id.strip():
        ui_error("Single mode requires --task-id (or choose task in interactive menu)")
        return False
    gitignore_ok, gitignore_error = validate_workspace_gitignore(workdir)
    if not gitignore_ok:
        log_event(log_path, "ERROR", "workspace gitignore validation failed", reason=gitignore_error)
        ui_error(f"❌ {gitignore_error}")
        return False
    return True


def _failure_message(reason: str) -> str:
    normalized = str(reason or "").strip()
    if normalized == "missing_conversation_id":
        return (
            "Resume state повреждён: в active task state отсутствует `conversation_id`."
            " Запустите с `--drop` для чистого старта или удалите файл состояния вручную."
        )
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


def _build_stage_specs(
    *,
    planning_config,
    design_config,
    coder_model: str,
    coder_prompt: str,
    review_config,
    testing_config,
    handoff_config,
    commit_phase: bool,
    default_handoff_model: str,
    enforce_coder_artifact_contract: bool = False,
) -> list[TaskStageSpec]:
    coder_prompt_template = coder_prompt
    if enforce_coder_artifact_contract:
        coder_prompt_template = _append_sdlc_artifact_contract_if_missing(coder_prompt_template)
    stage_specs: list[TaskStageSpec] = []
    if bool(planning_config.enabled):
        stage_specs.append(
            TaskStageSpec(
                stage_id="planning",
                model=planning_config.model,
                prompt_template=planning_config.prompt,
            )
        )
    if bool(design_config.enabled):
        stage_specs.append(
            TaskStageSpec(
                stage_id="design",
                model=design_config.model,
                prompt_template=design_config.prompt,
            )
        )
    stage_specs.append(
        TaskStageSpec(
            stage_id="implementation",
            model=coder_model,
            prompt_template=coder_prompt_template,
        )
    )
    if bool(review_config.enabled):
        stage_specs.append(
            TaskStageSpec(
                stage_id="review",
                model=review_config.model,
                prompt_template=review_config.prompt,
            )
        )
    if bool(testing_config.enabled):
        stage_specs.append(
            TaskStageSpec(
                stage_id="testing",
                model=testing_config.model,
                prompt_template=testing_config.prompt,
            )
        )
    if bool(commit_phase) and handoff_config is not None:
        stage_specs.append(
            TaskStageSpec(
                stage_id="handoff",
                model=handoff_config.model or default_handoff_model,
                prompt_template=handoff_config.prompt,
            )
        )
    return stage_specs


def _append_sdlc_artifact_contract_if_missing(template: str) -> str:
    text = str(template or "")
    if "{artifact_implementation}" in text:
        return text
    return (
        text.rstrip()
        + "\n\n"
        + "## SDLC Artifact Contract (mandatory)\n"
        + "- Artifact directory: `{artifacts_dir}`.\n"
        + "- Write a non-empty implementation report to `{artifact_implementation}`.\n"
        + "- Do not finish the task until `{artifact_implementation}` is written.\n"
    )


def main() -> int:
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
    task_path = active_task_path(workdir)
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

        prompt_coder_path = str(args.prompt_coder).strip()
        prompt_coder_text = ""
        if prompt_coder_path:
            try:
                prompt_coder_text = role_registry.load_prompt(Path(prompt_coder_path))
            except FileNotFoundError as exc:
                log_event(log_path, "ERROR", "prompt-coder file missing", error=str(exc))
                ui_error(f"--prompt-coder file not found: {prompt_coder_path}")
                return 2
            ui_info(f"[orc] prompt coder: {prompt_coder_path}")

        interactive_requested = _should_use_interactive_flow(args)
        model_loader = start_model_list_loading() if interactive_requested else None

        default_coder_model = role_registry.resolve_role(workdir, ROLE_CODER).model
        last_model = str(args.model).strip() or load_last_selected_model(workdir) or default_coder_model or DEFAULT_MODEL
        models = model_loader.result(timeout=30.0) if model_loader is not None else [DEFAULT_MODEL]
        prompt_coder_status = f"Prompt coder: {prompt_coder_path}" if prompt_coder_path else ""
        status_line = prompt_coder_status
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
                    workdir=workdir,
                )
                status_line = prompt_coder_status
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
            if not _validate_inputs(args, backlog_path, workdir, log_path):
                return 2

            _cleanup_stale_task_file(task_path, log_path, allowed_backlog=backlog_path)
            acquire_lock(lock_path, log_path)
            lock_acquired = True
            try:
                try:
                    coder_config = role_registry.resolve_role(
                        workdir,
                        ROLE_CODER,
                        cli_model=str(args.model).strip(),
                        cli_prompt_path=str(args.prompt_template).strip(),
                    )
                    args.model = coder_config.model
                    template = coder_config.prompt
                    if prompt_coder_text and not str(args.prompt_template).strip():
                        template = prompt_coder_text
                    continue_template = role_registry.resolve_continue_prompt(str(args.continue_template).strip())
                    commit_template = ""
                    merge_expert_template = ""
                    merge_expert_model = ""
                    planning_config = role_registry.resolve_role(
                        workdir,
                        ROLE_ANALYSIS_PLANNING,
                        cli_model=str(args.model).strip(),
                    )
                    design_config = role_registry.resolve_role(
                        workdir,
                        ROLE_DESIGN,
                        cli_model=str(args.model).strip(),
                    )
                    review_config = role_registry.resolve_role(
                        workdir,
                        ROLE_CODE_REVIEW,
                        cli_model=str(args.model).strip(),
                    )
                    testing_config = role_registry.resolve_role(
                        workdir,
                        ROLE_TESTER,
                        cli_model=str(args.model).strip(),
                    )
                    handoff_config = None
                    if args.commit_phase:
                        handoff_config = role_registry.resolve_role(
                            workdir,
                            ROLE_HANDOFF,
                            cli_model=str(args.commit_model).strip(),
                            cli_prompt_path=str(args.commit_template).strip(),
                        )
                        args.commit_model = handoff_config.model
                        commit_template = handoff_config.prompt
                    merge_expert_config = role_registry.resolve_role(
                        workdir,
                        ROLE_MERGE_EXPERT,
                    )
                    merge_expert_model = merge_expert_config.model
                    merge_expert_template = merge_expert_config.prompt
                    stage_specs = _build_stage_specs(
                        planning_config=planning_config,
                        design_config=design_config,
                        coder_model=coder_config.model,
                        coder_prompt=template,
                        review_config=review_config,
                        testing_config=testing_config,
                        handoff_config=handoff_config,
                        commit_phase=bool(args.commit_phase),
                        default_handoff_model=args.commit_model or args.model,
                        enforce_coder_artifact_contract=bool(
                            getattr(args, "require_stage_artifacts", False)
                            and prompt_coder_text
                            and not str(args.prompt_template).strip()
                        ),
                    )
                except FileNotFoundError as exc:
                    log_event(log_path, "ERROR", "prompt file missing", error=str(exc))
                    ui_error(str(exc))
                    return 2

                engine = TaskExecutionEngine(log_path=log_path)
                manager = SessionManager(
                    workdir=workdir,
                    backlog_path=backlog_path,
                    args=args,
                    log_path=log_path,
                    engine=engine,
                    prompt_template=template,
                    continue_template=continue_template,
                    commit_template=commit_template,
                    merge_expert_template=merge_expert_template,
                    merge_expert_model=merge_expert_model,
                    integrate_to_main=True,
                    main_branch=base_branch,
                    stage_specs=stage_specs,
                    max_sessions=max(1, min(int(getattr(args, "max_sessions", 1) or 1), 4)),
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
                elif exit_code != 0:
                    ui_error(f"❌ {_failure_message(manager.last_failure_reason)}")
                if exit_code == 0:
                    print(f"\n{manager.get_summary()}", flush=True)
                if interactive_requested and exit_code == 0 and str(args.mode).strip() == "single":
                    completed_task_id = str(args.task_id).strip()
                    task_done_msg = f"Задача {completed_task_id} завершена успешно" if completed_task_id else "Задача завершена успешно"
                    status_line = f"{task_done_msg} | {prompt_coder_status}" if prompt_coder_status else task_done_msg
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


def main_multi() -> int:
    sys.argv.insert(1, "--max-sessions")
    sys.argv.insert(2, "4")
    return main()
