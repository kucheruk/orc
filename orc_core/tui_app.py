#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
from typing import Callable, Optional

from textual import work
from textual.app import App

from .backlog_status import BacklogStatus
from .quit_signal import clear_stop_request, request_stop
from .start_menu import StartMenuChoice
from .stream_monitor_state import MonitorSnapshot
from .tui.messages import OrchestratorFinished, SnapshotUpdated
from .tui.screens.confirm_quit import ConfirmQuitModal
from .tui.screens.execution import ExecutionScreen
from .tui.screens.start_menu import StartMenuScreen


class _StartMenuApp(App[Optional[StartMenuChoice]]):
    CSS_PATH = "tui/orc.tcss"
    BINDINGS = [("escape", "request_quit", "Quit"), ("t", "toggle_dark", "Theme")]

    def __init__(
        self,
        backlog_status: BacklogStatus,
        models: list[str],
        default_model: str,
        resume_task_id: str = "",
    ) -> None:
        super().__init__()
        self._backlog_status = backlog_status
        self._models = models
        self._default_model = default_model
        self._resume_task_id = resume_task_id

    def on_mount(self) -> None:
        self.push_screen(
            StartMenuScreen(
                self._backlog_status,
                models=self._models,
                default_model=self._default_model,
                resume_task_id=self._resume_task_id,
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
    BINDINGS = [("escape", "request_quit", "Stop ORC"), ("t", "toggle_dark", "Theme")]

    def __init__(self, run_orchestrator: Callable[[Callable[[MonitorSnapshot], None]], int]) -> None:
        super().__init__()
        self._run_orchestrator = run_orchestrator
        self._execution_screen = ExecutionScreen()
        self._last_error: str | None = None

    def on_mount(self) -> None:
        clear_stop_request()
        self.push_screen(self._execution_screen)
        self._run_in_background_worker()

    @work(thread=True)
    def _run_in_background_worker(self) -> None:
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

    def _publish_snapshot_from_worker(self, snapshot: MonitorSnapshot) -> None:
        self.call_from_thread(self.post_message, SnapshotUpdated(snapshot))

    def on_snapshot_updated(self, message: SnapshotUpdated) -> None:
        self._execution_screen.update_from_snapshot(message.snapshot)

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


def run_start_menu(
    backlog_status: BacklogStatus,
    *,
    models: list[str],
    default_model: str,
    resume_task_id: str = "",
) -> Optional[StartMenuChoice]:
    app = _StartMenuApp(
        backlog_status,
        models=models,
        default_model=default_model,
        resume_task_id=resume_task_id,
    )
    return app.run(mouse=False)
