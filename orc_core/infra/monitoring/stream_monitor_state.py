#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import time
from collections import deque
from typing import Deque, Dict, Optional

from .monitor_types import MetricsStore, MonitorSnapshot
from ..io.text_parse import clean_summary_lines
from .token_tracker import TokenTracker
from .reasoning_tracker import ReasoningTracker
from .tool_call_tracker import ToolCallTracker


def make_terminal_snapshot(
    task_id: str,
    phase: str,
    status: str,
    *,
    base: Optional[MonitorSnapshot] = None,
) -> MonitorSnapshot:
    """Create a snapshot that represents a terminal state (failed/completed).

    If *base* is given, metrics and progress are carried over so the panel
    keeps showing accumulated stats.  Otherwise a minimal empty snapshot is
    returned.
    """
    now = time.time()
    if base is not None:
        return MonitorSnapshot(
            task_id=task_id or base.task_id,
            started_at=base.started_at,
            progress_done=base.progress_done,
            progress_total=base.progress_total,
            metrics=base.metrics,
            last_event_type=base.last_event_type,
            last_event_note=base.last_event_note,
            recent_commands=base.recent_commands,
            recent_files=base.recent_files,
            recent_events=base.recent_events,
            reasoning_lines=base.reasoning_lines,
            spinner_idx=base.spinner_idx,
            last_event_at=now,
            progress_remaining=base.progress_remaining,
            progress_in_progress=base.progress_in_progress,
            progress_added_delta=base.progress_added_delta,
            live_phase=phase,
            live_status=status,
            live_since=now,
            active_tool_call_count=0,
            is_subagent_activity=False,
        )
    return MonitorSnapshot(
        task_id=task_id,
        started_at=now,
        progress_done=0,
        progress_total=1,
        metrics=MetricsStore(),
        last_event_type="",
        last_event_note="",
        recent_commands=[],
        recent_files=[],
        recent_events=[],
        reasoning_lines=[],
        spinner_idx=0,
        last_event_at=now,
        live_phase=phase,
        live_status=status,
        live_since=now,
    )




# ---------------------------------------------------------------------------
# Internal tracker: progress & ETA
# ---------------------------------------------------------------------------

class ProgressTracker:
    def __init__(self) -> None:
        self._done = 0
        self._total = 1
        self._in_progress = 0
        self._baseline_total: Optional[int] = None
        self._added_delta = 0
        self._eta_seconds: Optional[float] = None
        self._spinner_idx = 0

    def set_progress(self, done: int, total: int, in_progress: int = 0) -> None:
        self._done = max(0, int(done))
        self._total = max(1, int(total))
        self._in_progress = max(0, int(in_progress))
        if self._baseline_total is None:
            self._baseline_total = self._total
        self._added_delta = max(self._total - self._baseline_total, 0)

    def set_eta_seconds(self, eta_seconds: Optional[float]) -> None:
        if eta_seconds is None:
            self._eta_seconds = None
            return
        self._eta_seconds = max(float(eta_seconds), 0.0)

    def tick_spinner(self) -> None:
        self._spinner_idx += 1


# ---------------------------------------------------------------------------
# Public API class — delegates to internal trackers
# ---------------------------------------------------------------------------

class StreamMonitorState:
    _WORKTREE_PREFIX_RE = re.compile(r"/[^\s\"']*?/.orc/worktrees/[^/\s\"']+")


    def __init__(self, task_id: str, started_at: float, summary_lines: int) -> None:
        self.task_id = task_id
        self.started_at = started_at
        self.metrics = MetricsStore()
        self._line_buffer: Deque[str] = deque(maxlen=max(summary_lines, 1))
        self._last_event_type = "init"
        self._last_event_note = "starting"
        self._recent_commands: Deque[str] = deque(maxlen=8)
        self._recent_files: Deque[str] = deque(maxlen=10)
        self._recent_events: Deque[str] = deque(maxlen=8)
        self._last_event_at = started_at
        self._live_phase = "starting"
        self._live_status = "starting, no messages yet"
        self._live_since = started_at
        self._is_subagent_activity = False
        self._session_id: Optional[str] = None

        # Internal trackers
        self._tokens = TokenTracker()
        self._reasoning = ReasoningTracker()
        self._tools = ToolCallTracker()
        self._progress = ProgressTracker()

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    def set_progress(self, done: int, total: int, in_progress: int = 0) -> None:
        self._progress.set_progress(done, total, in_progress)

    def set_eta_seconds(self, eta_seconds: Optional[float]) -> None:
        self._progress.set_eta_seconds(eta_seconds)

    def tick_spinner(self) -> None:
        self._progress.tick_spinner()

    def build_snapshot(self) -> MonitorSnapshot:
        p = self._progress
        remaining = max(p._total - p._done, 0)
        return MonitorSnapshot(
            task_id=self.task_id,
            started_at=self.started_at,
            progress_done=p._done,
            progress_total=p._total,
            metrics=self.metrics,
            last_event_type=self._last_event_type,
            last_event_note=self._last_event_note,
            recent_commands=list(self._recent_commands),
            recent_files=list(self._recent_files),
            recent_events=list(self._recent_events),
            reasoning_lines=self._reasoning.reasoning_lines_for_panel(max_width=90, max_lines=5),
            spinner_idx=p._spinner_idx,
            last_event_at=self._last_event_at,
            progress_remaining=remaining,
            progress_in_progress=p._in_progress,
            progress_added_delta=p._added_delta,
            eta_seconds=p._eta_seconds,
            live_phase=self._live_phase,
            live_status=self._live_status,
            live_since=self._live_since,
            active_tool_call_count=len(self._tools.active_tool_calls),
            is_subagent_activity=self._is_subagent_activity,
        )

    def summary_text(self) -> str:
        return "\n".join(self._line_buffer)

    # -- Public delegation to trackers (used by StreamMonitor) --

    def append_reasoning_fragment(self, fragment: str) -> None:
        self._reasoning.append_reasoning_fragment(fragment)

    def reasoning_lines_for_panel(self, max_width: int = 90, max_lines: int = 5) -> list[str]:
        return self._reasoning.reasoning_lines_for_panel(max_width, max_lines)

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]:
        return self._tools.force_finalize_live_tool_calls(reason, self._set_live_status, self._recent_events)

    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]:
        return self._tools.active_tool_calls_watchdog_snapshot()

    def _format_tool_call_with_args(self, payload_key: str, payload: object) -> str:
        return self._tools._format_tool_call_with_args(
            payload_key, payload, self._string_arg, self._shorten_worktree_paths,
        )

    # -- Methods that remain on StreamMonitorState --

    def _iter_values(self, value: object):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key, inner
                yield from self._iter_values(inner)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_values(item)

    def _extract_text(self, event: Dict[str, object]) -> str:
        pieces: list[str] = []

        def append_piece(value: object) -> None:
            if isinstance(value, str):
                if value.strip():
                    pieces.append(value)
                return
            if isinstance(value, dict):
                for key in ("text", "content", "delta", "value"):
                    append_piece(value.get(key))
                return
            if isinstance(value, list):
                for item in value:
                    append_piece(item)

        for key in ("text", "message", "content", "delta"):
            append_piece(event.get(key))
        msg = event.get("message")
        if isinstance(msg, dict):
            append_piece(msg.get("content"))
            append_piece(msg.get("text"))
        deduped: list[str] = []
        seen: set[str] = set()
        for piece in pieces:
            key = piece.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(piece)
        return "\n".join(deduped).strip()

    def _string_arg(self, value: object) -> str:
        if isinstance(value, str):
            return " ".join(value.split()).strip()
        return ""

    def _shorten_worktree_paths(self, value: str) -> str:
        if not value:
            return value
        return self._WORKTREE_PREFIX_RE.sub("[worktree]", value)

    def _set_live_status(self, phase: str, status: str, *, is_subagent: Optional[bool] = None) -> None:
        normalized_phase = str(phase or "waiting").strip() or "waiting"
        normalized_status = str(status or "").strip() or "waiting for output"
        normalized_subagent = self._is_subagent_activity if is_subagent is None else bool(is_subagent)
        if (
            normalized_phase != self._live_phase
            or normalized_status != self._live_status
            or normalized_subagent != self._is_subagent_activity
        ):
            self._live_phase = normalized_phase
            self._live_status = normalized_status
            self._is_subagent_activity = normalized_subagent
            self._live_since = time.time()

    def _remember_command(self, event: Dict[str, object]) -> None:
        event_type = str(event.get("type") or "")
        if event_type == "tool_call":
            tool_call_payload = event.get("tool_call")
            if isinstance(tool_call_payload, dict):
                for payload_key, payload_value in tool_call_payload.items():
                    if not isinstance(payload_key, str) or not payload_key.strip():
                        continue
                    formatted = self._format_tool_call_with_args(payload_key, payload_value)
                    if formatted:
                        self._recent_commands.append(formatted[:180])
                        return

            for key, value in self._iter_values(event):
                if not isinstance(key, str) or not isinstance(value, str):
                    continue
                key_lower = key.lower()
                val = " ".join(value.split())
                if not val:
                    continue
                if key_lower in {"command", "cmd", "shell_command"}:
                    self._recent_commands.append(self._shorten_worktree_paths(val)[:180])
                    return

            for key in ("tool_name", "tool", "name", "function"):
                value = event.get(key)
                if isinstance(value, str) and value.strip():
                    self._recent_commands.append(value.strip()[:180])
                    return

            if isinstance(tool_call_payload, dict):
                for payload_key in tool_call_payload.keys():
                    if not isinstance(payload_key, str) or not payload_key.strip():
                        continue
                    # Cursor stream-json often sends nested keys like readToolCall/shellToolCall.
                    command_name = re.sub(r"ToolCall$", "", payload_key.strip())
                    self._recent_commands.append(command_name[:180])
                    return

        for key, value in self._iter_values(event):
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            key_lower = key.lower()
            val = " ".join(value.split())
            if not val:
                continue
            if key_lower in {"command", "cmd", "shell_command"}:
                self._recent_commands.append(self._shorten_worktree_paths(val)[:180])
                return
            if key_lower in {"tool", "tool_name", "function", "name"} and "tool_call" in str(event.get("type") or ""):
                self._recent_commands.append(val[:180])
                return

    def _remember_paths(self, event: Dict[str, object]) -> None:
        for key, value in self._iter_values(event):
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            if key.lower() in {"path", "filepath", "file_path", "target_notebook"}:
                path = self._shorten_worktree_paths(value.strip())
                if path and path not in self._recent_files:
                    self._recent_files.append(path[:200])

    def _summarize_event(self, event: Dict[str, object], text: str) -> str:
        timestamp = time.strftime("%H:%M:%S", time.localtime(self._last_event_at or time.time()))
        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "") or "update"
        base = f"{event_type}:{subtype}"
        preview_lines = clean_summary_lines(text.splitlines()) if text else []
        preview = preview_lines[-1][:60] if preview_lines else ""
        if event_type == "tool_call":
            for key in ("tool_name", "tool", "name", "function"):
                value = event.get(key)
                if isinstance(value, str) and value.strip():
                    return f"[{timestamp}] {base} {value.strip()[:40]}"
        if event_type == "result":
            status = str(event.get("status") or subtype).strip()
            if status:
                return f"[{timestamp}] {base} status={status[:20]}"
        for key in ("command", "cmd", "shell_command"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return f"[{timestamp}] {base} {value.strip()[:50]}"
        return f"[{timestamp}] {base} {preview}" if preview else f"[{timestamp}] {base}"

    def _update_live_status_for_network_event(self, event: Dict[str, object], event_type: str, subtype: str) -> bool:
        event_lower = str(event_type or "").strip().lower()
        subtype_lower = str(subtype or "").strip().lower()
        if event_lower not in {"connection", "retry"}:
            return False

        if event_lower == "connection":
            if subtype_lower in {"reconnecting", "disconnected", "degraded"}:
                self._set_live_status("network_problem", "Network problems: reconnecting", is_subagent=False)
                return True
            if subtype_lower == "reconnected":
                self._set_live_status("waiting", "Network recovered: reconnected", is_subagent=False)
                return True

        if event_lower == "retry":
            attempt_raw = event.get("attempt")
            attempt = ""
            if isinstance(attempt_raw, int) and attempt_raw > 0:
                attempt = f" (attempt {attempt_raw})"
            if subtype_lower == "starting":
                self._set_live_status("network_problem", f"Network problems: retry starting{attempt}", is_subagent=False)
                return True
            if subtype_lower == "resuming":
                self._set_live_status("network_problem", f"Network problems: retry resuming{attempt}", is_subagent=False)
                return True

        return False

    def record_event(self, event: Dict[str, object]) -> tuple[str, str, str]:
        raw = json.dumps(event, ensure_ascii=False)
        self.metrics.total_lines += 1
        self.metrics.total_output_chars += len(raw)
        self._last_event_at = time.time()

        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        if self._session_id is None:
            raw_sid = str(event.get("session_id") or "").strip()
            if raw_sid:
                self._session_id = raw_sid
        raw_bytes = len(raw.encode("utf-8"))
        if event_type in ("user", "tool_result", "system"):
            self.metrics.input_bytes += raw_bytes
        elif event_type in ("assistant", "tool_call"):
            self.metrics.output_bytes += raw_bytes
        stream_kind = self._reasoning._reasoning_stream_kind_for_event(event_type, subtype)
        self._tools._remember_tool_activity(
            event, event_type, subtype,
            self._format_tool_call_with_args,
            self._set_live_status,
        )
        self._last_event_type = event_type or "event"
        self._last_event_note = subtype or "update"
        if event_type == "tool_call" and subtype == "started":
            self.metrics.command_count += 1

        text = self._extract_text(event)
        if not stream_kind:
            self._recent_events.append(self._summarize_event(event, text))

        self._process_event_tokens(event, raw)
        self._process_event_text(text)
        self._process_event_reasoning(event, event_type, subtype, text)
        self._update_live_status_from_event(event, event_type, subtype, text)

        self._remember_command(event)
        self._remember_paths(event)
        return event_type, subtype, raw

    def _process_event_tokens(self, event: Dict[str, object], raw: str) -> None:
        self._tokens.process_event_tokens(event, raw, self.metrics)

    def _process_event_text(self, text: str) -> None:
        if text:
            for line in clean_summary_lines(text.splitlines()):
                self._line_buffer.append(line)
            preview = self._line_buffer[-1] if self._line_buffer else ""
            if preview:
                self._last_event_note = preview[:80]

    def _process_event_reasoning(self, event: Dict[str, object], event_type: str, subtype: str, text: str) -> None:
        self._reasoning._remember_reasoning_from_stream(event, event_type, subtype, text)

    def _update_live_status_from_event(self, event: Dict[str, object], event_type: str, subtype: str, text: str) -> None:
        if event_type in {"thinking", "analysis"}:
            fragment = self._reasoning._extract_reasoning_fragment(event, text)
            preview = self._reasoning._trim_fragment(" ".join(fragment.split()).strip()) if fragment else ""
            status = f"thinking {preview}" if preview else "thinking"
            self._set_live_status("thinking", status, is_subagent=False)
        elif event_type == "assistant":
            self._set_live_status("assistant", "responding", is_subagent=False)
        elif event_type == "result":
            status = str(event.get("status") or subtype or "result").strip().lower() or "result"
            self._set_live_status("waiting", f"result {status}", is_subagent=False)
        elif self._update_live_status_for_network_event(event, event_type, subtype):
            pass
        elif event_type != "tool_call" and self._tools.active_tool_calls:
            label, is_subagent = self._tools._active_tool_status()
            self._set_live_status(
                "subagent" if is_subagent else "tool_call",
                f"running {label}",
                is_subagent=is_subagent,
            )
        elif event_type not in {"tool_call", "thinking", "analysis", "assistant", "result"}:
            self._set_live_status("waiting", "waiting for output", is_subagent=False)
