#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
from typing import Callable, Optional

from textual import work
from textual.app import App

from .backlog_status import BacklogStatus
from .quit_signal import clear_stop_request, request_stop, toggle_quit_after_task
from .start_menu import StartMenuChoice
from .stream_monitor_state import MonitorSnapshot
from .tui.messages import (
    OrchestratorFinished,
    SessionAdded,
    SessionClosing,
    SessionFailed,
    SessionRemoved,
    SnapshotUpdated,
    TaskBodyUpdated,
)
from .tui.screens.confirm_quit import ConfirmQuitModal
from .tui.screens.execution import ExecutionScreen
from .tui.screens.start_menu import StartMenuScreen


class _StartMenuApp(App[Optional[StartMenuChoice]]):
    CSS_PATH = "tui/orc.tcss"
    TITLE = "ORC"
    BINDINGS = [("escape", "request_quit", "Quit"), ("t", "toggle_dark", "Theme")]

    def __init__(
        self,
        backlog_status: BacklogStatus,
        models: list[str],
        default_model: str,
        resume_task_id: str = "",
        status_line: str = "",
        workdir: str = "",
    ) -> None:
        super().__init__()
        self._backlog_status = backlog_status
        self._models = models
        self._default_model = default_model
        self._resume_task_id = resume_task_id
        self._status_line = status_line
        self._workdir = workdir

    def on_mount(self) -> None:
        self.push_screen(
            StartMenuScreen(
                self._backlog_status,
                models=self._models,
                default_model=self._default_model,
                resume_task_id=self._resume_task_id,
                status_line=self._status_line,
                workdir=self._workdir,
            ),
            self._on_choice,
        )

    def _on_choice(self, choice: Optional[StartMenuChoice]) -> None:
        self.exit(choice)

    def action_request_quit(self) -> None:
        self.push_screen(ConfirmQuitModal(), self._on_quit_confirm)

    def _on_quit_confirm(self, confirmed: bool) -> None:
        if confirmed:
            self.exit(None)


class OrcApp(App[int]):
    CSS_PATH = "tui/orc.tcss"
    TITLE = "ORC"
    BINDINGS = [
        ("escape", "request_quit", "Stop ORC"),
        ("q", "request_quit_after_task", "Quit After Task"),
        ("t", "toggle_dark", "Theme"),
        ("+", "add_session", "Add Session"),
        ("-", "remove_session", "Remove Session"),
    ]

    def __init__(self, run_orchestrator: Callable[[Callable[[str, MonitorSnapshot], None]], int], *, session_manager=None) -> None:
        super().__init__()
        self._run_orchestrator = run_orchestrator
        self._session_manager = session_manager
        self._execution_screen = ExecutionScreen()
        self._last_error: str | None = None

    def on_mount(self) -> None:
        clear_stop_request()
        self.push_screen(self._execution_screen)
        self._run_in_background_worker()

    @work(thread=True)
    def _run_in_background_worker(self) -> None:
        if self._session_manager:
            self._session_manager.task_body_publisher = self._publish_task_body_from_worker
            self._session_manager.session_removed_publisher = self._publish_session_removed_from_worker
        code = 1
        try:
            code = int(self._run_orchestrator(self._publish_snapshot_from_worker))
        except KeyboardInterrupt:
            code = 130
        except Exception:
            error_text = traceback.format_exc()
            self.call_from_thread(self.post_message, OrchestratorFinished(code, error_text))
            return
        self.call_from_thread(self.post_message, OrchestratorFinished(code))

    def _publish_task_body_from_worker(self, session_id: str, body: str) -> None:
        try:
            self.call_from_thread(self.post_message, TaskBodyUpdated(session_id, body))
        except RuntimeError:
            pass

    def _publish_session_removed_from_worker(self, session_id: str) -> None:
        try:
            self.call_from_thread(self.post_message, SessionRemoved(session_id))
        except RuntimeError:
            pass

    def _publish_snapshot_from_worker(self, session_id: str, snapshot: MonitorSnapshot | None) -> None:
        try:
            if snapshot is None:
                self.call_from_thread(self.post_message, SessionAdded(session_id))
            else:
                self.call_from_thread(self.post_message, SnapshotUpdated(session_id, snapshot))
        except RuntimeError:
            pass  # App already shut down

    def on_snapshot_updated(self, message: SnapshotUpdated) -> None:
        self._execution_screen.update_session(message.session_id, message.snapshot)

    def on_session_added(self, message: SessionAdded) -> None:
        self._execution_screen.add_session(message.session_id)

    async def on_session_removed(self, message: SessionRemoved) -> None:
        await self._execution_screen.remove_session(message.session_id)

    def on_session_failed(self, message: SessionFailed) -> None:
        self._execution_screen.mark_session_failed(message.session_id)

    def on_session_closing(self, message: SessionClosing) -> None:
        self._execution_screen.mark_session_closing(message.session_id)

    def on_task_body_updated(self, message: TaskBodyUpdated) -> None:
        if message.session_id == "_global":
            self._execution_screen.set_global_status(message.body)
        else:
            self._execution_screen.set_task_body(message.session_id, message.body)

    def on_orchestrator_finished(self, message: OrchestratorFinished) -> None:
        if message.error_text:
            self._last_error = message.error_text
            code = 1
        else:
            code = int(message.exit_code)
        self.exit(code)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def action_request_quit(self) -> None:
        self.push_screen(ConfirmQuitModal(), self._on_quit_confirm)

    def _on_quit_confirm(self, confirmed: bool) -> None:
        if not confirmed:
            return
        request_stop()
        self.exit(130)

    def action_request_quit_after_task(self) -> None:
        requested = toggle_quit_after_task()
        self._execution_screen.set_quit_after_task_requested(requested)

    def action_add_session(self) -> None:
        if not self._session_manager:
            return
        sid = self._session_manager.request_add_session()
        if sid:
            self._execution_screen.add_session(sid)

    def action_remove_session(self) -> None:
        if self._session_manager:
            self._session_manager.request_remove_session()


def run_start_menu(
    backlog_status: BacklogStatus,
    *,
    models: list[str],
    default_model: str,
    resume_task_id: str = "",
    status_line: str = "",
    workdir: str = "",
) -> Optional[StartMenuChoice]:
    app = _StartMenuApp(
        backlog_status,
        models=models,
        default_model=default_model,
        resume_task_id=resume_task_id,
        status_line=status_line,
        workdir=workdir,
    )
    return app.run(mouse=False)
