#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, Iterable, Optional

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from .logging import log_event
from .text_parse import clean_summary_lines
from .ui import ui_console


@dataclass
class MetricsStore:
    tokens_total: Optional[int] = None
    files_edited: Optional[int] = None
    command_count: int = 0
    total_lines: int = 0
    total_output_chars: int = 0
    git_added: Optional[int] = None
    git_deleted: Optional[int] = None


class StreamJsonMonitor:
    def __init__(
        self,
        proc,
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        workdir: str,
    ) -> None:
        self.proc = proc
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.started_at = time.time()
        self.metrics = MetricsStore()
        self.last_output_time = time.time()
        self.init_pid: Optional[int] = proc.pid
        self.stderr_count = 0
        self.last_stderr_line = ""
        self.last_nudge_time = 0.0
        self.status_only_reports = 0
        self.ui_followup_prompt = False
        self.result_status: Optional[str] = None
        self.result_seen_at: Optional[float] = None
        self._line_buffer: Deque[str] = deque(maxlen=max(summary_lines, 1))
        self._report_interval = max(report_interval, 1.0)
        self._last_report_time = 0.0
        self._last_git_stats_time = 0.0
        self._last_ui_render = 0.0
        self._spinner_idx = 0
        self._last_event_type = "init"
        self._last_event_note = "starting"
        self._recent_commands: Deque[str] = deque(maxlen=8)
        self._recent_files: Deque[str] = deque(maxlen=10)
        self._recent_events: Deque[str] = deque(maxlen=8)
        self._progress_done = 0
        self._progress_total = 1
        self._console = ui_console()
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=8,
            auto_refresh=False,
            transient=False,
        )
        self._live_started = False
        self._live.start()
        self._live_started = True
        self._stop = threading.Event()
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def set_progress(self, done: int, total: int) -> None:
        self._progress_done = max(0, int(done))
        self._progress_total = max(1, int(total))

    def _extract_tokens(self, obj: object) -> Optional[int]:
        max_tokens: Optional[int] = None

        def visit(value: object) -> None:
            nonlocal max_tokens
            if isinstance(value, dict):
                for key, inner in value.items():
                    key_lower = key.lower()
                    if key_lower in {
                        "tokens",
                        "token_count",
                        "tokens_total",
                        "total_tokens",
                        "input_tokens",
                        "output_tokens",
                        "completion_tokens",
                        "prompt_tokens",
                    } and isinstance(inner, (int, float)):
                        candidate = int(inner)
                        if max_tokens is None or candidate > max_tokens:
                            max_tokens = candidate
                    visit(inner)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(obj)
        return max_tokens

    def _extract_text(self, event: Dict[str, object]) -> str:
        pieces = []
        for key in ("text", "message", "content", "delta"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                pieces.append(value)
        msg = event.get("message")
        if isinstance(msg, dict):
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                pieces.append(content)
        return "\n".join(pieces).strip()

    def _iter_values(self, value: object):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key, inner
                yield from self._iter_values(inner)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_values(item)

    def _remember_command(self, event: Dict[str, object]) -> None:
        for key, value in self._iter_values(event):
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            key_lower = key.lower()
            val = " ".join(value.split())
            if not val:
                continue
            if key_lower in {"command", "cmd", "shell_command"}:
                self._recent_commands.append(val[:180])
                return
            if key_lower in {"tool", "tool_name", "function", "name"} and "tool_call" in str(event.get("type") or ""):
                self._recent_commands.append(val[:180])
                return

    def _remember_paths(self, event: Dict[str, object]) -> None:
        for key, value in self._iter_values(event):
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            key_lower = key.lower()
            if key_lower in {"path", "filepath", "file_path", "target_notebook"}:
                path = value.strip()
                if not path:
                    continue
                if path not in self._recent_files:
                    self._recent_files.append(path[:200])

    def _render(self):
        elapsed = int(max(time.time() - self.started_at, 0))
        minutes = elapsed // 60
        seconds = elapsed % 60
        tokens = self.metrics.tokens_total if self.metrics.tokens_total is not None else "-"
        files_edited = self.metrics.files_edited if self.metrics.files_edited is not None else "-"
        spinner = "|/-\\"[self._spinner_idx % 4]
        pct = min(max(self._progress_done / max(self._progress_total, 1), 0.0), 1.0)
        width = max(20, min(self._console.size.width - 30, 80))

        status_table = Table.grid(padding=(0, 1))
        status_table.add_row("Task", self.task_id)
        status_table.add_row("Elapsed", f"{minutes:02d}:{seconds:02d}")
        status_table.add_row(
            "Progress",
            Group(
                ProgressBar(total=100, completed=int(pct * 100), width=width),
                Text(f"{self._progress_done}/{self._progress_total} ({int(pct * 100)}%)"),
            ),
        )
        status_table.add_row("Lines", str(self.metrics.total_lines))
        status_table.add_row("Commands", str(self.metrics.command_count))
        status_table.add_row("Files", str(files_edited))
        status_table.add_row("Tokens", str(tokens))
        status_table.add_row("Last", f"{self._last_event_type}:{self._last_event_note[:60]}")
        status_panel = Panel(status_table, title=f"ORC {spinner}", border_style="cyan")

        cmd_table = Table(show_header=True, header_style="bold", expand=True)
        cmd_table.add_column("#", width=3)
        cmd_table.add_column("Recent Commands", no_wrap=True, overflow="ellipsis")
        commands = list(self._recent_commands)
        if not commands:
            cmd_table.add_row("-", "waiting for tool calls...")
        else:
            for idx, cmd in enumerate(commands[-5:], start=max(len(commands) - 4, 1)):
                cmd_table.add_row(str(idx), cmd)
        cmd_panel = Panel(cmd_table, title="Recent Commands", border_style="magenta")

        file_table = Table(show_header=True, header_style="bold", expand=True)
        file_table.add_column("#", width=3)
        file_table.add_column("Edited/Touched Files", no_wrap=True, overflow="ellipsis")
        files = list(self._recent_files)
        if not files:
            file_table.add_row("-", "waiting for file operations...")
        else:
            for idx, path in enumerate(files[-6:], start=max(len(files) - 5, 1)):
                file_table.add_row(str(idx), path)
        files_panel = Panel(file_table, title="Files", border_style="green")

        events = Text("\n".join(list(self._recent_events)[-4:]) or "waiting for events...")
        events_panel = Panel(events, title="Event Feed", border_style="yellow")

        term_height = max(self._console.size.height, 16)
        available = max(term_height - 2, 14)
        status_h = min(10, max(6, available // 3))
        cmds_h = min(8, max(4, available // 5))
        files_h = min(9, max(4, available // 4))
        used = status_h + cmds_h + files_h
        events_h = max(4, available - used)

        layout = Layout()
        layout.split_column(
            Layout(status_panel, size=status_h),
            Layout(cmd_panel, size=cmds_h),
            Layout(files_panel, size=files_h),
            Layout(events_panel, size=events_h),
        )
        return layout

    def _record_event(self, event: Dict[str, object]) -> None:
        self.last_output_time = time.time()
        self.metrics.total_lines += 1
        raw = json.dumps(event, ensure_ascii=False)
        self.metrics.total_output_chars += len(raw)

        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        self._last_event_type = event_type or "event"
        self._last_event_note = subtype or "update"
        self._recent_events.append(f"{event_type}:{subtype or 'update'}")
        if event_type == "tool_call" and subtype == "started":
            self.metrics.command_count += 1

        if event_type == "result":
            status = subtype or str(event.get("status") or "")
            self.result_status = status.lower() if status else "success"
            self.result_seen_at = time.time()

        tokens = self._extract_tokens(event)
        if tokens is not None:
            self.metrics.tokens_total = max(self.metrics.tokens_total or 0, tokens)

        text = self._extract_text(event)
        if text:
            for line in clean_summary_lines(text.splitlines()):
                self._line_buffer.append(line)
            preview = self._line_buffer[-1] if self._line_buffer else ""
            if preview:
                self._last_event_note = preview[:80]

        self._remember_command(event)
        self._remember_paths(event)

        log_event(self.log_path, "INFO", "stream_json_event", event_type=event_type, subtype=subtype, size=len(raw))

    def _read_stdout(self) -> None:
        if self.proc.stdout is None:
            return
        for line in self.proc.stdout:
            if self._stop.is_set():
                break
            raw = line.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except Exception as exc:
                log_event(self.log_path, "WARN", "stream_json_bad_line", error=str(exc), raw=raw[:500])
                continue
            if isinstance(event, dict):
                self._record_event(event)

    def _read_stderr(self) -> None:
        if self.proc.stderr is None:
            return
        for line in self.proc.stderr:
            if self._stop.is_set():
                break
            raw = line.strip()
            if not raw:
                continue
            self.last_stderr_line = raw[:500]
            self.stderr_count += 1
            log_event(self.log_path, "WARN", "agent_stderr", line=self.last_stderr_line)

    def _update_git_stats(self) -> None:
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat"],
                cwd=self.workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except Exception:
            return
        if result.returncode != 0:
            return
        added = 0
        deleted = 0
        for line in result.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            try:
                added += int(parts[0])
            except ValueError:
                pass
            try:
                deleted += int(parts[1])
            except ValueError:
                pass
        self.metrics.git_added = added
        self.metrics.git_deleted = deleted
        # Git diff is a pragmatic proxy for "files edited" when the event stream
        # does not expose a stable field across CLI versions.
        self.metrics.files_edited = len([line for line in result.stdout.splitlines() if line.strip()]) or self.metrics.files_edited

    def _write_metrics_snapshot(self) -> None:
        try:
            payload = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "task_id": self.task_id,
                "tokens_total": self.metrics.tokens_total,
                "lines": self.metrics.total_lines,
                "commands": self.metrics.command_count,
                "files_edited": self.metrics.files_edited,
            }
            path = Path(self.workdir) / ".orc" / "orc-metrics.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            log_event(self.log_path, "ERROR", "metrics snapshot write failed", error=str(exc))

    def maybe_report(self) -> None:
        now = time.time()
        if now - self._last_report_time < self._report_interval:
            return
        self._last_report_time = now
        if now - self._last_git_stats_time >= 10.0:
            self._last_git_stats_time = now
            self._update_git_stats()
        self._write_metrics_snapshot()
        now2 = time.time()
        if now2 - self._last_ui_render >= 0.7:
            self._spinner_idx += 1
            if self._live_started:
                self._live.update(self._render(), refresh=True)
            self._last_ui_render = now2
        log_event(
            self.log_path,
            "INFO",
            "stats report",
            tokens=self.metrics.tokens_total if self.metrics.tokens_total is not None else "-",
            lines=self.metrics.total_lines,
            commands=self.metrics.command_count,
            files_edited=self.metrics.files_edited if self.metrics.files_edited is not None else "-",
        )

    def get_summary_text(self) -> str:
        return "\n".join(self._line_buffer)

    def send_keys(self, keys: Iterable[str], label: str = "", fallback: Optional[Iterable[Iterable[str]]] = None) -> bool:
        # stream-json flow has no PTY key injection channel; keep interface for compatibility.
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        _ = fallback
        return False

    def stop(self) -> None:
        self._stop.set()
        if self._live_started:
            self._live.stop()
            self._live_started = False
