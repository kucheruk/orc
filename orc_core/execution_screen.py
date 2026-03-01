#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil
import threading
import time
from typing import Callable

from prompt_toolkit.output.defaults import create_output

from .stream_monitor_state import MonitorSnapshot
from .ui import ui_warn


class PromptToolkitExecutionScreen:
    def __init__(self, snapshot_getter: Callable[[], MonitorSnapshot], refresh_interval: float = 0.2) -> None:
        self._snapshot_getter = snapshot_getter
        self._refresh_interval = max(0.1, float(refresh_interval))
        self._output = create_output()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._enabled = False
        self._warned = False
        self._last_render = 0.0

    def start(self) -> None:
        if self._enabled:
            return
        if not self._output.responds_to_cpr:
            # Still allow rendering in non-CPR terminals; only skip if stream isn't a TTY.
            pass
        if not self._output.stdout.isatty():
            return
        self._enabled = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def request_render(self) -> None:
        if self._enabled:
            self._wake.set()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._enabled = False
        self._clear_screen()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(timeout=self._refresh_interval)
            self._wake.clear()
            now = time.time()
            if now - self._last_render < self._refresh_interval:
                continue
            self._last_render = now
            self._render_once()

    def _render_once(self) -> None:
        try:
            snapshot = self._snapshot_getter()
            text = self._render_text(snapshot)
            self._output.write("\x1b[2J\x1b[H")
            self._output.write(text)
            self._output.flush()
        except (BlockingIOError, OSError):
            self._disable_on_output_error()

    def _disable_on_output_error(self) -> None:
        if self._warned:
            return
        self._warned = True
        try:
            ui_warn("[orc] live UI disabled: terminal write is not available. Task continues.")
        except Exception:
            pass
        self._enabled = False
        self._stop.set()

    def _clear_screen(self) -> None:
        try:
            self._output.write("\x1b[2J\x1b[H")
            self._output.flush()
        except Exception:
            return

    def _render_text(self, snapshot: MonitorSnapshot) -> str:
        width = max(80, shutil.get_terminal_size((120, 40)).columns)
        elapsed = int(max(time.time() - snapshot.started_at, 0))
        minutes = elapsed // 60
        seconds = elapsed % 60
        pct = min(max(snapshot.progress_done / max(snapshot.progress_total, 1), 0.0), 1.0)
        progress_bar_width = max(12, min(64, width - 40))
        progress_fill = int(progress_bar_width * pct)
        progress_bar = "#" * progress_fill + "-" * (progress_bar_width - progress_fill)
        spinner = "|/-\\"[snapshot.spinner_idx % 4]

        tokens = snapshot.metrics.tokens_total if snapshot.metrics.tokens_total is not None else "-"
        files_edited = snapshot.metrics.files_edited if snapshot.metrics.files_edited is not None else "-"
        commands = snapshot.recent_commands[-5:] or ["waiting for tool calls..."]
        files = snapshot.recent_files[-6:] or ["waiting for file operations..."]
        events = snapshot.recent_events[-4:] or ["waiting for events..."]
        reasoning = snapshot.reasoning_lines or ["waiting for reasoning..."]

        left_recent = [f"  - {line}" for line in commands]
        right_recent = [f"  - {line}" for line in files]
        split = max(44, width // 2)

        rows = max(len(left_recent), len(right_recent))
        while len(left_recent) < rows:
            left_recent.append("")
        while len(right_recent) < rows:
            right_recent.append("")

        combined_recent = []
        for left, right in zip(left_recent, right_recent):
            combined_recent.append(f"{left[: split - 2]:<{split}}{right}")

        lines = [
            f"ORC {spinner}",
            f"Task: {snapshot.task_id}",
            f"Elapsed: {minutes:02d}:{seconds:02d}",
            f"Progress: [{progress_bar}] {snapshot.progress_done}/{snapshot.progress_total} ({int(pct * 100)}%)",
            f"Lines: {snapshot.metrics.total_lines}  Commands: {snapshot.metrics.command_count}  Files: {files_edited}  Tokens: {tokens}",
            f"Last: {snapshot.last_event_type}:{snapshot.last_event_note[:100]}",
            "",
            "Recent Commands | Files",
            *combined_recent,
            "",
            "Reasoning (latest)",
            *[f"  {line}" for line in reasoning[-5:]],
            "",
            "Event Feed",
            *[f"  {line}" for line in events],
            "",
            "Press Ctrl+C to stop.",
        ]
        return "\n".join(lines[: max(20, shutil.get_terminal_size((120, 40)).lines - 1)])
