#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import textwrap
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from .text_parse import clean_summary_lines, extract_tokens_from_text


@dataclass
class MetricsStore:
    tokens_total: Optional[int] = None
    files_edited: Optional[int] = None
    command_count: int = 0
    total_lines: int = 0
    total_output_chars: int = 0
    git_added: Optional[int] = None
    git_deleted: Optional[int] = None


@dataclass(frozen=True)
class MonitorSnapshot:
    task_id: str
    started_at: float
    progress_done: int
    progress_total: int
    metrics: MetricsStore
    last_event_type: str
    last_event_note: str
    recent_commands: list[str]
    recent_files: list[str]
    recent_events: list[str]
    reasoning_lines: list[str]
    spinner_idx: int


class StreamMonitorState:
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
        self._recent_reasoning: Deque[str] = deque(maxlen=12)
        self._progress_done = 0
        self._progress_total = 1
        self._spinner_idx = 0

    def set_progress(self, done: int, total: int) -> None:
        self._progress_done = max(0, int(done))
        self._progress_total = max(1, int(total))

    def tick_spinner(self) -> None:
        self._spinner_idx += 1

    def build_snapshot(self) -> MonitorSnapshot:
        return MonitorSnapshot(
            task_id=self.task_id,
            started_at=self.started_at,
            progress_done=self._progress_done,
            progress_total=self._progress_total,
            metrics=self.metrics,
            last_event_type=self._last_event_type,
            last_event_note=self._last_event_note,
            recent_commands=list(self._recent_commands),
            recent_files=list(self._recent_files),
            recent_events=list(self._recent_events),
            reasoning_lines=self.reasoning_lines_for_panel(max_width=90, max_lines=5),
            spinner_idx=self._spinner_idx,
        )

    def summary_text(self) -> str:
        return "\n".join(self._line_buffer)

    def normalize_reasoning_fragment(self, fragment: str) -> str:
        text = fragment.replace("\r", "").replace("\n", " ")
        text = re.sub(r"(\*\*|__|`)", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text

    def should_stitch_reasoning(self, prev: str, chunk: str) -> bool:
        if "\n" in prev or "\n" in chunk:
            return False
        chunk_stripped = chunk.lstrip()
        if not chunk_stripped:
            return False
        if chunk_stripped[0] in {".", ",", "!", "?", ":", ";", ")", "]", "}", "%"}:
            return True
        if prev and prev[-1].isalnum() and chunk_stripped[0].islower():
            return True
        if len(chunk_stripped) <= 20 and " " not in chunk_stripped and not prev.endswith((".", "?", "!", ":", ";")):
            return True
        return False

    def join_reasoning_chunks(self, prev: str, chunk: str) -> str:
        chunk_stripped = chunk.lstrip()
        if chunk_stripped in {"**", "__", "`", "*"}:
            return f"{prev}{chunk}"
        if prev and prev[-1] in {"(", "[", "{", "/", "-", "_", "`", "*"}:
            return f"{prev}{chunk_stripped}"
        if chunk_stripped and chunk_stripped[0] in {".", ",", "!", "?", ":", ";", ")", "]", "}", "%"}:
            return f"{prev}{chunk_stripped}"
        prev_last = prev.split(" ")[-1] if prev.strip() else ""
        first_token = chunk_stripped.split(" ")[0] if chunk_stripped else ""
        if prev_last.isalpha() and first_token.isalpha() and len(prev_last) <= 2 and len(first_token) >= 3:
            return f"{prev}{chunk_stripped}"
        if prev and prev[-1].isalnum() and first_token and first_token[0].islower():
            return f"{prev}{chunk_stripped}"
        if chunk.startswith(" "):
            return f"{prev}{chunk}"
        return f"{prev} {chunk_stripped}"

    def append_reasoning_fragment(self, fragment: str) -> None:
        chunk = self.normalize_reasoning_fragment(fragment)
        if not chunk.strip():
            return
        if not self._recent_reasoning:
            self._recent_reasoning.append(chunk.strip())
            return
        prev = self._recent_reasoning[-1]
        if self.should_stitch_reasoning(prev, chunk):
            self._recent_reasoning[-1] = self.join_reasoning_chunks(prev, chunk)[:220]
            return
        self._recent_reasoning.append(chunk.strip()[:220])

    def reasoning_lines_for_panel(self, max_width: int = 90, max_lines: int = 5) -> list[str]:
        width = max(24, max_width)
        lines: list[str] = []
        for entry in self._recent_reasoning:
            normalized = entry.strip()
            if not normalized:
                continue
            wrapped = textwrap.wrap(
                normalized,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            )
            lines.extend(wrapped or [normalized])
        if not lines:
            return ["waiting for reasoning..."]
        return lines[-max_lines:]

    def extract_tokens(self, obj: object) -> Optional[int]:
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

    def _iter_values(self, value: object):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key, inner
                yield from self._iter_values(inner)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_values(item)

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
            if key.lower() in {"path", "filepath", "file_path", "target_notebook"}:
                path = value.strip()
                if path and path not in self._recent_files:
                    self._recent_files.append(path[:200])

    def _is_reasoning_event(self, event: Dict[str, object]) -> bool:
        markers = ("reason", "analysis", "think", "thought")
        event_type = str(event.get("type") or "").lower()
        subtype = str(event.get("subtype") or "").lower()
        if any(marker in event_type for marker in markers):
            return True
        if any(marker in subtype for marker in markers):
            return True
        for key, _ in self._iter_values(event):
            if isinstance(key, str) and any(marker in key.lower() for marker in markers):
                return True
        return False

    def _remember_reasoning(self, event: Dict[str, object], text: str) -> None:
        if not text.strip() or not self._is_reasoning_event(event):
            return
        lines = clean_summary_lines(text.splitlines())
        for line in lines[-5:]:
            self.append_reasoning_fragment(line[:220])

    def _summarize_event(self, event: Dict[str, object], text: str) -> str:
        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "") or "update"
        base = f"{event_type}:{subtype}"
        preview_lines = clean_summary_lines(text.splitlines()) if text else []
        preview = preview_lines[-1][:60] if preview_lines else ""
        if event_type == "tool_call":
            for key in ("tool_name", "tool", "name", "function"):
                value = event.get(key)
                if isinstance(value, str) and value.strip():
                    return f"{base} {value.strip()[:40]}"
        if event_type == "result":
            status = str(event.get("status") or subtype).strip()
            if status:
                return f"{base} status={status[:20]}"
        for key in ("command", "cmd", "shell_command"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return f"{base} {value.strip()[:50]}"
        return f"{base} {preview}" if preview else base

    def record_event(self, event: Dict[str, object]) -> tuple[str, str, str]:
        raw = json.dumps(event, ensure_ascii=False)
        self.metrics.total_lines += 1
        self.metrics.total_output_chars += len(raw)

        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        self._last_event_type = event_type or "event"
        self._last_event_note = subtype or "update"
        if event_type == "tool_call" and subtype == "started":
            self.metrics.command_count += 1

        tokens = self.extract_tokens(event)
        text = self._extract_text(event)
        self._recent_events.append(self._summarize_event(event, text))
        if tokens is None and text:
            tokens = extract_tokens_from_text(text)
        if tokens is not None:
            self.metrics.tokens_total = max(self.metrics.tokens_total or 0, tokens)

        if text:
            for line in clean_summary_lines(text.splitlines()):
                self._line_buffer.append(line)
            preview = self._line_buffer[-1] if self._line_buffer else ""
            if preview:
                self._last_event_note = preview[:80]
            self._remember_reasoning(event, text)

        self._remember_command(event)
        self._remember_paths(event)
        return event_type, subtype, raw

