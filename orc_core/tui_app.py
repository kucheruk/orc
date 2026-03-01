#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import traceback
from typing import Callable, Optional

from textual.app import App

from .backlog_status import BacklogStatus
from .quit_signal import clear_stop_request, request_stop
from .start_menu import StartMenuChoice
from .tui.bus import consume_latest_snapshot
from .tui.screens.confirm_quit import ConfirmQuitModal
from .tui.screens.execution import ExecutionScreen
from .tui.screens.start_menu import StartMenuScreen


class _StartMenuApp(App[Optional[StartMenuChoice]]):
    CSS_PATH = "tui/orc.tcss"
    BINDINGS = [("escape", "request_quit", "Quit"), ("t", "toggle_dark", "Theme")]

    def __init__(self, backlog_status: BacklogStatus, models: list[str], default_model: str) -> None:
        super().__init__()
        self._backlog_status = backlog_status
        self._models = models
        self._default_model = default_model

    def on_mount(self) -> None:
        self.push_screen(
            StartMenuScreen(self._backlog_status, models=self._models, default_model=self._default_model),
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

    def __init__(self, run_orchestrator: Callable[[], int]) -> None:
        super().__init__()
        self._run_orchestrator = run_orchestrator
        self._execution_screen = ExecutionScreen()
        self._runner_thread: threading.Thread | None = None
        self._last_error: str | None = None

    def on_mount(self) -> None:
        clear_stop_request()
        self.push_screen(self._execution_screen)
        self.set_interval(0.2, self._drain_snapshot_updates)
        self._runner_thread = threading.Thread(target=self._run_in_background, daemon=True)
        self._runner_thread.start()

    def _run_in_background(self) -> None:
        code = 1
        try:
            code = int(self._run_orchestrator())
        except KeyboardInterrupt:
            code = 130
        except Exception:
            self._last_error = traceback.format_exc()
            code = 1
        self.call_from_thread(self.exit, code)

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _drain_snapshot_updates(self) -> None:
        snapshot = consume_latest_snapshot()
        if snapshot is not None:
            self._execution_screen.update_from_snapshot(snapshot)

    def action_request_quit(self) -> None:
        self.push_screen(ConfirmQuitModal(), self._on_quit_confirm)

    def _on_quit_confirm(self, confirmed: bool) -> None:
        if not confirmed:
            return
        request_stop()


def run_start_menu(backlog_status: BacklogStatus, *, models: list[str], default_model: str) -> Optional[StartMenuChoice]:
    app = _StartMenuApp(backlog_status, models=models, default_model=default_model)
    return app.run(mouse=False)
