#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback
from typing import Callable, Optional, Protocol, runtime_checkable

from textual import work
from textual.app import App

from ..infra.state.quit_signal import clear_stop_request, request_stop, toggle_quit_after_task
from ..infra.monitoring.monitor_types import MonitorSnapshot


@runtime_checkable
class SessionManagerProtocol(Protocol):
    """TUI's view of the session manager — only the methods TUI needs."""

    def add_inbox_card(self, text: str) -> None: ...
    def unblock_card(self, card_id: str, directive: str) -> None: ...
    def queue_teamlead_directive(self, text: str) -> None: ...
    def request_add_session(self) -> Optional[str]: ...
    def request_remove_session(self, session_id: str) -> None: ...
from ..tui.kanban_messages import (
    BoardUpdated,
    InboxCardRequested,
    JournalEntryAdded,
    TeamleadDirectiveRequested,
    UnblockCardRequested,
)
from ..tui.messages import (
    OrchestratorFinished,
    SnapshotUpdated,
)
from ..tui.screens.confirm_quit import ConfirmQuitModal
from ..tui.screens.kanban_screen import KanbanScreen


class OrcApp(App[int]):
    CSS_PATH = "tui/orc.tcss"
    TITLE = "ORC"
    BINDINGS = [
        ("escape", "request_quit", "Stop ORC"),
        ("q", "request_quit_after_task", "Quit After Task"),
        ("t", "toggle_dark", "Theme"),
        ("f2", "add_session", "+Agent"),
        ("f3", "remove_session", "-Agent"),
    ]

    def __init__(self, run_orchestrator: Callable[[Callable[[str, MonitorSnapshot | None], None]], int], *, session_manager: SessionManagerProtocol | None = None) -> None:
        super().__init__()
        self._run_orchestrator = run_orchestrator
        self._session_manager = session_manager
        self._kanban_screen = KanbanScreen()
        self._last_error: str | None = None

    def on_mount(self) -> None:
        clear_stop_request()
        self.push_screen(self._kanban_screen)
        self._run_in_background_worker()

    @work(thread=True)
    def _run_in_background_worker(self) -> None:
        if self._session_manager:
            publisher = getattr(self._session_manager, "publisher", None)
            if publisher:
                publisher.board_callback = self._publish_board_from_worker
                publisher.journal_callback = self._publish_journal_from_worker
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

    def _publish_snapshot_from_worker(self, session_id: str, snapshot: MonitorSnapshot | None) -> None:
        try:
            if snapshot is not None:
                self.call_from_thread(self.post_message, SnapshotUpdated(session_id, snapshot))
        except RuntimeError:
            pass  # App already shut down

    def _publish_board_from_worker(self, snapshot) -> None:
        try:
            self.call_from_thread(self.post_message, BoardUpdated(snapshot))
        except RuntimeError:
            pass

    def _publish_journal_from_worker(self, entry) -> None:
        try:
            self.call_from_thread(self.post_message, JournalEntryAdded(entry))
        except RuntimeError:
            pass

    def on_board_updated(self, message: BoardUpdated) -> None:
        self._kanban_screen.update_board(message.snapshot)

    def on_journal_entry_added(self, message: JournalEntryAdded) -> None:
        self._kanban_screen.add_journal_entry(message.entry)

    def on_inbox_card_requested(self, message: InboxCardRequested) -> None:
        if self._session_manager:
            self._session_manager.add_inbox_card(message.text)

    def on_unblock_card_requested(self, message: UnblockCardRequested) -> None:
        if self._session_manager:
            self._session_manager.unblock_card(message.card_id, message.directive)

    def on_teamlead_directive_requested(self, message: TeamleadDirectiveRequested) -> None:
        if self._session_manager:
            self._session_manager.queue_teamlead_directive(message.text)

    def on_snapshot_updated(self, message: SnapshotUpdated) -> None:
        # Forward to card detail screen if it's active on top
        try:
            top = self.screen
        except Exception:
            return
        if top is not self._kanban_screen and hasattr(top, "update_session"):
            top.update_session(message.session_id, message.snapshot)

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
        self._journal_user("Stop requested, waiting for agents to finish...")

    def action_request_quit_after_task(self) -> None:
        requested = toggle_quit_after_task()
        if requested:
            self._journal_user("Quit-after-task ON: agents will finish current tasks then exit")
        else:
            self._journal_user("Quit-after-task OFF: normal operation resumed")

    def action_add_session(self) -> None:
        if not self._session_manager:
            return
        sid = self._session_manager.request_add_session()
        if sid:
            self._journal_user(f"Added agent {sid}")
        else:
            self._journal_user("Cannot add agent: max sessions reached")

    def action_remove_session(self) -> None:
        if self._session_manager:
            self._session_manager.request_remove_session()
            self._journal_user("Removing agent...")

    def _journal_user(self, text: str) -> None:
        import time as _time
        from ..board.kanban_snapshot import JournalEntry
        entry = JournalEntry(timestamp=_time.time(), category="user", card_id="", message=text)
        self._kanban_screen.add_journal_entry(entry)
