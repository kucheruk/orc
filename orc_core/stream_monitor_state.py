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
    tokens_status: str = "unknown"
    tokens_source: str = "none"
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
    last_event_at: float


class StreamMonitorState:
    _TOTAL_TOKEN_KEYS = {
        "tokens",
        "tokencount",
        "tokenstotal",
        "totaltokens",
    }
    _PROMPT_TOKEN_KEYS = {
        "prompttokens",
        "inputtokens",
        "input",
    }
    _COMPLETION_TOKEN_KEYS = {
        "completiontokens",
        "outputtokens",
        "output",
    }

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
        self._reasoning_buffer = ""
        self._reasoning_stream_kind = ""
        self._progress_done = 0
        self._progress_total = 1
        self._spinner_idx = 0
        self._last_event_at = started_at
        self._seen_token_usage_keys: set[str] = set()

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
            last_event_at=self._last_event_at,
        )

    def summary_text(self) -> str:
        return "\n".join(self._line_buffer)

    def normalize_reasoning_fragment(self, fragment: str) -> str:
        text = fragment.replace("\r", "")
        text = re.sub(r"(\*\*|__|`)", "", text)
        text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
        return text

    def _trim_fragment(self, value: str, *, max_len: int = 220) -> str:
        if len(value) <= max_len:
            return value
        candidate = value[:max_len]
        split_at = candidate.rfind(" ")
        if split_at >= 24:
            return candidate[:split_at]
        return candidate

    def append_reasoning_fragment(self, fragment: str) -> None:
        chunk = self.normalize_reasoning_fragment(fragment)
        if not chunk.strip():
            return
        normalized = re.sub(r"\s+", " ", chunk).strip()
        self._recent_reasoning.append(self._trim_fragment(normalized))

    def _append_to_reasoning_buffer(self, fragment: str) -> None:
        chunk = self.normalize_reasoning_fragment(fragment)
        if not chunk:
            return
        self._reasoning_buffer += chunk

    def _should_flush_reasoning_buffer(self, fragment: str, subtype: str) -> bool:
        if not self._reasoning_buffer:
            return False
        if "\n" in fragment:
            return True
        if len(self._reasoning_buffer) >= 220:
            return True
        if subtype in {"completed", "complete", "done", "end"}:
            return True
        sentence_markers = (".", "!", "?", ":", ";")
        return len(self._reasoning_buffer) >= 48 and any(marker in fragment for marker in sentence_markers)

    def _flush_reasoning_buffer(self) -> None:
        buffered = self.normalize_reasoning_fragment(self._reasoning_buffer)
        self._reasoning_buffer = ""
        self._reasoning_stream_kind = ""
        if not buffered.strip():
            return
        lines = clean_summary_lines(buffered.splitlines())
        for line in lines[-5:]:
            self.append_reasoning_fragment(line[:220])

    def _reasoning_stream_kind_for_event(self, event_type: str, subtype: str) -> str:
        event_lower = str(event_type or "").strip().lower()
        subtype_lower = str(subtype or "").strip().lower()
        if event_lower in {"thinking", "analysis"}:
            return event_lower
        if event_lower == "assistant":
            return "assistant_text"
        if event_lower in {"assistant", "message"} and subtype_lower in {"reasoning", "analysis", "thinking"}:
            return subtype_lower or "reasoning"
        return ""

    def _extract_reasoning_fragment(self, event: Dict[str, object], fallback_text: str) -> str:
        value = event.get("text")
        if isinstance(value, str):
            return value
        message = event.get("message")
        if isinstance(message, dict):
            for key in ("content", "text", "delta", "value"):
                extracted = self._extract_reasoning_text_fragment(message.get(key))
                if extracted is not None:
                    return extracted
        for key in ("content", "delta", "value"):
            extracted = self._extract_reasoning_text_fragment(event.get(key))
            if extracted is not None:
                return extracted
        return fallback_text

    def _extract_reasoning_text_fragment(self, value: object) -> Optional[str]:
        parts: list[str] = []
        has_text = False

        def visit(inner: object) -> None:
            nonlocal has_text
            if isinstance(inner, str):
                has_text = True
                parts.append(inner)
                return
            if isinstance(inner, dict):
                for key in ("text", "content", "delta", "value"):
                    visit(inner.get(key))
                return
            if isinstance(inner, list):
                for item in inner:
                    visit(item)

        visit(value)
        if not has_text:
            return None
        return "".join(parts)

    def _remember_reasoning_from_stream(
        self,
        event: Dict[str, object],
        event_type: str,
        subtype: str,
        fallback_text: str,
    ) -> None:
        stream_kind = self._reasoning_stream_kind_for_event(event_type, subtype)
        if not stream_kind:
            if self._reasoning_buffer:
                self._flush_reasoning_buffer()
            return

        subtype_lower = str(subtype or "").strip().lower()
        fragment = self._extract_reasoning_fragment(event, fallback_text)

        if self._reasoning_stream_kind and self._reasoning_stream_kind != stream_kind and self._reasoning_buffer:
            self._flush_reasoning_buffer()
        self._reasoning_stream_kind = stream_kind

        if subtype_lower in {"completed", "complete", "done", "end"}:
            self._flush_reasoning_buffer()
            return

        self._append_to_reasoning_buffer(fragment)
        if self._should_flush_reasoning_buffer(fragment, subtype_lower):
            self._flush_reasoning_buffer()

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
                    key_lower = self._normalize_token_key(key)
                    if key_lower in (
                        self._TOTAL_TOKEN_KEYS
                        | self._PROMPT_TOKEN_KEYS
                        | self._COMPLETION_TOKEN_KEYS
                    ) and isinstance(inner, (int, float)):
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

    def _extract_request_id(self, event: Dict[str, object]) -> Optional[str]:
        for key in ("request_id", "requestId", "response_id", "responseId", "id"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _to_non_negative_int(self, value: object) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            candidate = int(value)
            if candidate >= 0:
                return candidate
        return None

    def _normalize_token_key(self, key: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(key).strip().lower())

    def _extract_token_metric(self, value: Dict[str, object], aliases: set[str]) -> Optional[int]:
        for key, item in value.items():
            if self._normalize_token_key(key) in aliases:
                parsed = self._to_non_negative_int(item)
                if parsed is not None:
                    return parsed
        return None

    def _extract_structured_token_entries(self, event: Dict[str, object]) -> list[tuple[str, int]]:
        request_id = self._extract_request_id(event) or ""
        entries: list[tuple[str, int]] = []

        def visit(value: object) -> None:
            if isinstance(value, dict):
                total = self._extract_token_metric(value, self._TOTAL_TOKEN_KEYS)
                prompt = self._extract_token_metric(value, self._PROMPT_TOKEN_KEYS)
                completion = self._extract_token_metric(value, self._COMPLETION_TOKEN_KEYS)
                if total is None and (prompt is not None or completion is not None):
                    total = (prompt or 0) + (completion or 0)
                if total is not None:
                    usage_payload = {
                        "total_tokens": total,
                        "prompt_tokens": prompt,
                        "completion_tokens": completion,
                    }
                    signature = json.dumps(usage_payload, ensure_ascii=False, sort_keys=True)
                    usage_key = f"{request_id}:{signature}" if request_id else signature
                    entries.append((usage_key, total))
                for inner in value.values():
                    visit(inner)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(event)
        # stable de-duplication within one event
        result: list[tuple[str, int]] = []
        seen_local: set[str] = set()
        for usage_key, total in entries:
            if usage_key in seen_local:
                continue
            seen_local.add(usage_key)
            result.append((usage_key, total))
        return result

    def _string_arg(self, value: object) -> str:
        if isinstance(value, str):
            return " ".join(value.split()).strip()
        return ""

    def _tool_call_name(self, payload_key: str) -> str:
        normalized = re.sub(r"ToolCall$", "", payload_key.strip())
        return normalized.strip()

    def _format_tool_call_with_args(self, payload_key: str, payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        args = payload.get("args")
        if not isinstance(args, dict):
            return ""

        tool_name = self._tool_call_name(payload_key)
        tool_label = tool_name.lower() if tool_name else "tool"

        command = self._string_arg(args.get("command"))
        if command:
            return command

        path = self._string_arg(args.get("path"))
        if tool_label == "read" and path:
            return f"{tool_label} {path}"

        pattern = self._string_arg(args.get("pattern"))
        if tool_label in {"grep", "rg"} and pattern:
            target_path = self._string_arg(args.get("path"))
            if target_path:
                return f'{tool_label} "{pattern}" in {target_path}'
            return f'{tool_label} "{pattern}"'

        glob_pattern = self._string_arg(args.get("globPattern"))
        target_dir = self._string_arg(args.get("targetDirectory"))
        if tool_label == "glob" and (glob_pattern or target_dir):
            left = f"{tool_label} {glob_pattern}".strip()
            if target_dir:
                return f"{left} in {target_dir}"
            return left

        kv_parts: list[str] = []
        for key, value in args.items():
            key_name = str(key).strip()
            if not key_name:
                continue
            normalized = self._string_arg(value)
            if normalized:
                kv_parts.append(f"{key_name}={normalized}")
            elif isinstance(value, (int, float, bool)):
                kv_parts.append(f"{key_name}={value}")

        if kv_parts:
            return f"{tool_label} " + " ".join(kv_parts[:4])
        return ""

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
                    self._recent_commands.append(val[:180])
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
        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        if self._reasoning_stream_kind_for_event(event_type, subtype):
            return True
        markers = ("reason", "analysis", "think", "thought")
        event_type_lower = event_type.lower()
        subtype_lower = subtype.lower()
        if any(marker in event_type_lower for marker in markers):
            return True
        if any(marker in subtype_lower for marker in markers):
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

    def record_event(self, event: Dict[str, object]) -> tuple[str, str, str]:
        raw = json.dumps(event, ensure_ascii=False)
        self.metrics.total_lines += 1
        self.metrics.total_output_chars += len(raw)
        self._last_event_at = time.time()

        event_type = str(event.get("type") or "")
        subtype = str(event.get("subtype") or "")
        stream_kind = self._reasoning_stream_kind_for_event(event_type, subtype)
        self._last_event_type = event_type or "event"
        self._last_event_note = subtype or "update"
        if event_type == "tool_call" and subtype == "started":
            self.metrics.command_count += 1

        tokens = self.extract_tokens(event)
        structured_entries = self._extract_structured_token_entries(event)
        text = self._extract_text(event)
        if not stream_kind:
            self._recent_events.append(self._summarize_event(event, text))
        if structured_entries:
            total_delta = 0
            for usage_key, usage_tokens in structured_entries:
                if usage_key in self._seen_token_usage_keys:
                    continue
                self._seen_token_usage_keys.add(usage_key)
                total_delta += usage_tokens
            if total_delta > 0:
                self.metrics.tokens_total = (self.metrics.tokens_total or 0) + total_delta
                self.metrics.tokens_status = "known"
                self.metrics.tokens_source = "structured"
        if tokens is None and text:
            tokens = extract_tokens_from_text(text)
        if tokens is not None and not structured_entries:
            self.metrics.tokens_total = max(self.metrics.tokens_total or 0, tokens)
            self.metrics.tokens_status = "known"
            self.metrics.tokens_source = "heuristic"

        if text:
            for line in clean_summary_lines(text.splitlines()):
                self._line_buffer.append(line)
            preview = self._line_buffer[-1] if self._line_buffer else ""
            if preview:
                self._last_event_note = preview[:80]
        self._remember_reasoning_from_stream(event, event_type, subtype, text)

        self._remember_command(event)
        self._remember_paths(event)
        return event_type, subtype, raw

