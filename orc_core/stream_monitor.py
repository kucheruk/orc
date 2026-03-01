#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

from .execution_screen import PromptToolkitExecutionScreen
from .logging import log_event
from .stream_monitor_state import StreamMonitorState


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
        self.last_output_time = time.time()
        self.init_pid: Optional[int] = proc.pid
        self.stderr_count = 0
        self.last_stderr_line = ""
        self.last_nudge_time = 0.0
        self.status_only_reports = 0
        self.ui_followup_prompt = False
        self.result_status: Optional[str] = None
        self.result_seen_at: Optional[float] = None

        self._state = StreamMonitorState(task_id=task_id, started_at=self.started_at, summary_lines=summary_lines)
        self.metrics = self._state.metrics
        self._report_interval = max(report_interval, 1.0)
        self._last_report_time = 0.0
        self._last_git_stats_time = 0.0
        self._stop = threading.Event()
        self._screen = PromptToolkitExecutionScreen(self._state.build_snapshot, refresh_interval=0.2)
        self._screen.start()

        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def set_progress(self, done: int, total: int) -> None:
        self._state.set_progress(done, total)
        self._screen.request_render()

    # Backward-compatible wrappers for tests/helpers.
    def _append_reasoning_fragment(self, fragment: str) -> None:
        self._state.append_reasoning_fragment(fragment)

    def _remember_reasoning(self, event: Dict[str, object], text: str) -> None:
        self._state._remember_reasoning(event, text)

    def _reasoning_lines_for_panel(self, max_width: int = 90, max_lines: int = 5) -> list[str]:
        return self._state.reasoning_lines_for_panel(max_width=max_width, max_lines=max_lines)

    def _summarize_event(self, event: Dict[str, object], text: str) -> str:
        return self._state._summarize_event(event, text)

    def _record_event(self, event: Dict[str, object]) -> None:
        self.last_output_time = time.time()
        event_type, subtype, raw = self._state.record_event(event)
        if event_type == "result":
            status = subtype or str(event.get("status") or "")
            self.result_status = status.lower() if status else "success"
            self.result_seen_at = time.time()
        if "add a follow-up" in raw.lower():
            self.ui_followup_prompt = True
        log_event(self.log_path, "INFO", "stream_json_event", event_type=event_type, subtype=subtype, size=len(raw))
        self._screen.request_render()

    def _read_stdout(self) -> None:
        if self.proc.stdout is None:
            return
        try:
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
        except Exception as exc:
            log_event(self.log_path, "ERROR", "stream_stdout_reader_failed", error=str(exc))

    def _read_stderr(self) -> None:
        if self.proc.stderr is None:
            return
        try:
            for line in self.proc.stderr:
                if self._stop.is_set():
                    break
                raw = line.strip()
                if not raw:
                    continue
                self.last_stderr_line = raw[:500]
                self.stderr_count += 1
                log_event(self.log_path, "WARN", "agent_stderr", line=self.last_stderr_line)
        except Exception as exc:
            log_event(self.log_path, "ERROR", "stream_stderr_reader_failed", error=str(exc))

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
        files_changed = len([line for line in result.stdout.splitlines() if line.strip()])
        if files_changed:
            self.metrics.files_edited = files_changed

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
        self._state.tick_spinner()
        self._screen.request_render()
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
        return self._state.summary_text()

    def send_keys(self, keys: Iterable[str], label: str = "", fallback: Optional[Iterable[Iterable[str]]] = None) -> bool:
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        _ = fallback
        return False

    def stop(self) -> None:
        self._stop.set()
        self._screen.stop()
