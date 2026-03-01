#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Iterable, Optional, TextIO

from .logging import log_event
from .process_groups import resolve_process_group_id, subprocess_group_spawn_kwargs
from .stream_monitor_state import MonitorSnapshot, StreamMonitorState

GIT_STATS_TIMEOUT_SECONDS = 10.0


class _ProcessProxy:
    def __init__(self) -> None:
        self.pid: Optional[int] = None
        self.returncode: Optional[int] = None

    def poll(self) -> Optional[int]:
        return self.returncode


class StreamJsonMonitor:
    def __init__(
        self,
        agent_cmd: list[str],
        log_path: Path,
        report_interval: float,
        summary_lines: int,
        task_id: str,
        workdir: str,
        agent_output_log_path: Optional[str] = None,
        snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]] = None,
    ) -> None:
        self._agent_cmd = list(agent_cmd)
        self.proc = _ProcessProxy()
        self.log_path = log_path
        self.task_id = task_id
        self.workdir = workdir
        self.started_at = time.time()
        self.last_output_time = time.time()
        self.init_pid: Optional[int] = None
        self.process_group_id: Optional[int] = None
        self.stderr_count = 0
        self.last_stderr_line = ""
        self.last_nudge_time = 0.0
        self.status_only_reports = 0
        self.ui_followup_prompt = False
        self.result_status: Optional[str] = None
        self.result_seen_at: Optional[float] = None
        self._agent_output_log_path = str(agent_output_log_path or "").strip() or None
        self._snapshot_publisher = snapshot_publisher
        self._agent_output_file: Optional[TextIO] = None
        if self._agent_output_log_path:
            path = Path(self._agent_output_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._agent_output_file = path.open("a", encoding="utf-8")
            self._agent_output_file.write(f"# stream start task_id={self.task_id}\n")
            self._agent_output_file.flush()
            log_event(self.log_path, "INFO", "agent output stream enabled", task_id=self.task_id, path=str(path))

        self._state = StreamMonitorState(task_id=task_id, started_at=self.started_at, summary_lines=summary_lines)
        self.metrics = self._state.metrics
        self._report_interval = max(report_interval, 1.0)
        self._last_report_time = 0.0
        self._last_git_stats_time = 0.0
        self._stop = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._spawned = threading.Event()
        self._spawn_error: Optional[BaseException] = None
        self._runner_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._runner_thread.start()
        if not self._spawned.wait(timeout=20.0):
            raise RuntimeError("Failed to start async monitor process")
        if self._spawn_error is not None:
            raise self._spawn_error

    def set_progress(self, done: int, total: int) -> None:
        self._state.set_progress(done, total)
        self._publish_snapshot()

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
        if self._is_followup_prompt_event(event_type, subtype, raw):
            self.ui_followup_prompt = True
        log_event(self.log_path, "INFO", "stream_json_event", event_type=event_type, subtype=subtype, size=len(raw))
        self._publish_snapshot()

    def _is_followup_prompt_event(self, event_type: str, subtype: str, raw: str) -> bool:
        if event_type != "result":
            return False
        status = (subtype or "").strip().lower()
        if status not in {"error", "failed", "failure"}:
            return False
        normalized = raw.lower()
        markers = (
            "add a follow-up",
            "follow-up",
            "follow up",
            "need your input",
            "waiting for your input",
        )
        return any(marker in normalized for marker in markers)

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._spawn_and_monitor())
        finally:
            self._loop.close()

    async def _spawn_and_monitor(self) -> None:
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *self._agent_cmd,
                cwd=self.workdir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **subprocess_group_spawn_kwargs(),
            )
        except Exception as exc:
            self._spawn_error = exc
            self._spawned.set()
            log_event(self.log_path, "ERROR", "failed to spawn async subprocess", error=str(exc))
            raise
        self.proc.pid = self._proc.pid
        self.init_pid = self._proc.pid
        self.process_group_id = resolve_process_group_id(self._proc.pid)
        self._spawned.set()
        if self._proc.stdout is None or self._proc.stderr is None:
            self.proc.returncode = 1
            return
        stdout_task = asyncio.create_task(self._read_stdout(self._proc.stdout))
        stderr_task = asyncio.create_task(self._read_stderr(self._proc.stderr))
        await self._proc.wait()
        self.proc.returncode = self._proc.returncode
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

    def _append_agent_output(self, stream_name: str, payload: str) -> None:
        if self._agent_output_file is None:
            return
        self._agent_output_file.write(f"[{stream_name}] {payload}")
        if not payload.endswith("\n"):
            self._agent_output_file.write("\n")
        self._agent_output_file.flush()

    async def _read_stdout(self, stream: asyncio.StreamReader) -> None:
        while not self._stop.is_set():
            line = await stream.readline()
            if not line:
                return
            decoded = line.decode("utf-8", errors="replace")
            self._append_agent_output("stdout", decoded)
            raw = decoded.strip()
            if not raw:
                continue
            self.last_output_time = time.time()
            try:
                event = json.loads(raw)
            except Exception as exc:
                log_event(self.log_path, "WARN", "stream_json_bad_line", error=str(exc), raw=raw[:500])
                continue
            if isinstance(event, dict):
                self._record_event(event)

    async def _read_stderr(self, stream: asyncio.StreamReader) -> None:
        while not self._stop.is_set():
            line = await stream.readline()
            if not line:
                return
            decoded = line.decode("utf-8", errors="replace")
            self._append_agent_output("stderr", decoded)
            raw = decoded.strip()
            if not raw:
                continue
            self.last_output_time = time.time()
            self.last_stderr_line = raw[:500]
            self.stderr_count += 1
            log_event(self.log_path, "WARN", "agent_stderr", line=self.last_stderr_line)

    def _update_git_stats(self) -> None:
        def read_numstat(args: list[str]) -> Optional[str]:
            try:
                result = subprocess.run(
                    args,
                    cwd=self.workdir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=GIT_STATS_TIMEOUT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                return None
            except Exception:
                return None
            if result.returncode != 0:
                return None
            return result.stdout

        unstaged = read_numstat(["git", "diff", "--numstat"])
        staged = read_numstat(["git", "diff", "--numstat", "--cached"])
        if unstaged is None and staged is None:
            return

        added = 0
        deleted = 0
        files: set[str] = set()
        for output in (unstaged or "", staged or ""):
            for line in output.splitlines():
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                try:
                    added += int(parts[0])
                except ValueError:
                    pass
                try:
                    deleted += int(parts[1])
                except ValueError:
                    pass
                path = parts[2].strip()
                if path:
                    files.add(path)
        self.metrics.git_added = added
        self.metrics.git_deleted = deleted
        files_changed = len(files)
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
                "git_added": self.metrics.git_added,
                "git_deleted": self.metrics.git_deleted,
                "tokens_status": self.metrics.tokens_status,
                "tokens_source": self.metrics.tokens_source,
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
        self._publish_snapshot()
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

    def send_keys(self, keys: Iterable[str], label: str = "") -> bool:
        log_event(self.log_path, "INFO", "send_keys_ignored", keys=list(keys), label=label)
        return False

    def stop(self) -> None:
        self._stop.set()
        loop = self._loop
        if loop is not None and not loop.is_closed():
            try:
                loop.call_soon_threadsafe(lambda: None)
            except RuntimeError:
                pass
        if self._runner_thread.is_alive():
            self._runner_thread.join(timeout=1.0)
        if self._agent_output_file is not None:
            self._agent_output_file.close()
            self._agent_output_file = None

    def _publish_snapshot(self) -> None:
        if self._snapshot_publisher is not None:
            self._snapshot_publisher(self._state.build_snapshot())
