#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import textwrap
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from .logging import debug_mode_log
from .text_parse import clean_summary_lines


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
    progress_remaining: int = 0
    progress_added_delta: int = 0
    eta_seconds: Optional[float] = None
    live_phase: str = "starting"
    live_status: str = "starting, no messages yet"
    live_since: float = 0.0
    active_tool_call_count: int = 0
    is_subagent_activity: bool = False


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
    _RAW_TOKEN_FIELD_RE = re.compile(
        r'"?([a-zA-Z_]+tokens|tokens[a-zA-Z_]*|token_count)"?\s*[:=]\s*"?([0-9]+(?:\.[0-9]+)?)"?',
        re.IGNORECASE,
    )
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
        self._recent_reasoning: Deque[str] = deque(maxlen=12)
        self._reasoning_buffer = ""
        self._reasoning_stream_kind = ""
        self._progress_done = 0
        self._progress_total = 1
        self._progress_baseline_total: Optional[int] = None
        self._progress_added_delta = 0
        self._eta_seconds: Optional[float] = None
        self._spinner_idx = 0
        self._last_event_at = started_at
        self._seen_token_usage_keys: set[str] = set()
        self._max_tokens_by_request: dict[str, int] = {}
        self._active_tool_calls: dict[str, dict[str, object]] = {}
        self._active_tool_order: Deque[str] = deque(maxlen=32)
        self._live_phase = "starting"
        self._live_status = "starting, no messages yet"
        self._live_since = started_at
        self._is_subagent_activity = False

    def set_progress(self, done: int, total: int) -> None:
        self._progress_done = max(0, int(done))
        self._progress_total = max(1, int(total))
        if self._progress_baseline_total is None:
            self._progress_baseline_total = self._progress_total
        self._progress_added_delta = max(self._progress_total - self._progress_baseline_total, 0)

    def set_eta_seconds(self, eta_seconds: Optional[float]) -> None:
        if eta_seconds is None:
            self._eta_seconds = None
            return
        self._eta_seconds = max(float(eta_seconds), 0.0)

    def tick_spinner(self) -> None:
        self._spinner_idx += 1

    def build_snapshot(self) -> MonitorSnapshot:
        remaining = max(self._progress_total - self._progress_done, 0)
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
            progress_remaining=remaining,
            progress_added_delta=self._progress_added_delta,
            eta_seconds=self._eta_seconds,
            live_phase=self._live_phase,
            live_status=self._live_status,
            live_since=self._live_since,
            active_tool_call_count=len(self._active_tool_calls),
            is_subagent_activity=self._is_subagent_activity,
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
        if isinstance(value, str):
            stripped = value.strip()
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", stripped):
                candidate = int(float(stripped))
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

    def _extract_structured_token_entries(self, event: Dict[str, object]) -> list[tuple[str, str, int]]:
        request_id = self._extract_request_id(event) or ""
        entries: list[tuple[str, str, int]] = []

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
                    entries.append((request_id, usage_key, total))
                for inner in value.values():
                    visit(inner)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(event)
        # stable de-duplication within one event
        result: list[tuple[str, str, int]] = []
        seen_local: set[str] = set()
        for request_key, usage_key, total in entries:
            if usage_key in seen_local:
                continue
            seen_local.add(usage_key)
            result.append((request_key, usage_key, total))
        return result

    def _extract_tokens_from_raw(self, raw: str) -> Optional[int]:
        total_tokens: Optional[int] = None
        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None
        unlabeled_tokens: Optional[int] = None

        for key, value in self._RAW_TOKEN_FIELD_RE.findall(raw):
            parsed = self._to_non_negative_int(value)
            if parsed is None:
                continue
            normalized = self._normalize_token_key(key)
            if normalized in self._TOTAL_TOKEN_KEYS:
                total_tokens = max(total_tokens or 0, parsed)
            elif normalized in self._PROMPT_TOKEN_KEYS:
                prompt_tokens = max(prompt_tokens or 0, parsed)
            elif normalized in self._COMPLETION_TOKEN_KEYS:
                completion_tokens = max(completion_tokens or 0, parsed)
            elif normalized == "tokens":
                unlabeled_tokens = max(unlabeled_tokens or 0, parsed)

        if total_tokens is not None:
            return total_tokens
        if prompt_tokens is not None or completion_tokens is not None:
            return (prompt_tokens or 0) + (completion_tokens or 0)
        return unlabeled_tokens

    def _string_arg(self, value: object) -> str:
        if isinstance(value, str):
            return " ".join(value.split()).strip()
        return ""

    def _shorten_worktree_paths(self, value: str) -> str:
        if not value:
            return value
        return self._WORKTREE_PREFIX_RE.sub("[worktree]", value)

    def _tool_call_name(self, payload_key: str) -> str:
        normalized = re.sub(r"ToolCall$", "", payload_key.strip())
        return normalized.strip()

    def _is_subagent_tool(self, tool_label: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]", "", str(tool_label or "").strip().lower())
        return normalized in {"task", "subagent", "subagenttask", "subagentdrivendevelopment"}

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

    def _tool_call_label_from_event(self, event: Dict[str, object]) -> tuple[str, str]:
        tool_call_payload = event.get("tool_call")
        if isinstance(tool_call_payload, dict):
            for payload_key, payload_value in tool_call_payload.items():
                if not isinstance(payload_key, str) or not payload_key.strip():
                    continue
                tool_name = self._tool_call_name(payload_key)
                formatted = self._format_tool_call_with_args(payload_key, payload_value)
                if formatted:
                    return tool_name, formatted
                if tool_name:
                    return tool_name, tool_name.lower()
        for key in ("tool_name", "tool", "name", "function"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip(), value.strip().lower()
        return "tool", "tool"

    def _active_tool_status(self) -> tuple[str, bool]:
        while self._active_tool_order and self._active_tool_order[0] not in self._active_tool_calls:
            self._active_tool_order.popleft()
        if self._active_tool_order:
            entry = self._active_tool_calls.get(self._active_tool_order[0], {})
            label = str(entry.get("label") or "tool").strip() or "tool"
            is_subagent = bool(entry.get("is_subagent") is True)
            return label, is_subagent
        if not self._active_tool_calls:
            return "tool", False
        first_entry = next(iter(self._active_tool_calls.values()))
        label = str(first_entry.get("label") or "tool").strip() or "tool"
        is_subagent = bool(first_entry.get("is_subagent") is True)
        return label, is_subagent

    def _remember_tool_activity(self, event: Dict[str, object], event_type: str, subtype: str) -> None:
        if event_type != "tool_call":
            return
        subtype_lower = str(subtype or "").strip().lower()
        call_id_raw = event.get("call_id")
        call_id = str(call_id_raw).strip() if isinstance(call_id_raw, str) else ""
        # #region agent log
        debug_mode_log(
            "run1",
            "H1",
            "orc_core/stream_monitor_state.py:_remember_tool_activity:entry",
            "tool_call event received",
            {
                "subtype": subtype_lower,
                "call_id": call_id,
                "has_tool_call_payload": isinstance(event.get("tool_call"), dict),
                "active_before": len(self._active_tool_calls),
            },
        )
        # #endregion
        if subtype_lower == "started":
            tool_name, label = self._tool_call_label_from_event(event)
            entry = {
                "tool_name": tool_name,
                "label": label,
                "started_at": time.time(),
                "is_subagent": self._is_subagent_tool(tool_name),
            }
            if not call_id:
                call_id = f"anon-{int(time.time() * 1000)}-{len(self._active_tool_calls)}"
            self._active_tool_calls[call_id] = entry
            self._active_tool_order.appendleft(call_id)
            # #region agent log
            debug_mode_log(
                "run1",
                "H2",
                "orc_core/stream_monitor_state.py:_remember_tool_activity:started",
                "tool_call marked active",
                {
                    "call_id": call_id,
                    "tool_name": tool_name,
                    "label": label,
                    "is_subagent": bool(entry["is_subagent"]),
                    "active_after": len(self._active_tool_calls),
                },
            )
            # #endregion
            self._set_live_status(
                "subagent" if bool(entry["is_subagent"]) else "tool_call",
                f"running {label}",
                is_subagent=bool(entry["is_subagent"]),
            )
            return
        if subtype_lower == "completed":
            removed_by = "none"
            if call_id and call_id in self._active_tool_calls:
                self._active_tool_calls.pop(call_id, None)
                removed_by = "exact_call_id"
            elif self._active_tool_order:
                fallback_id = self._active_tool_order.popleft()
                self._active_tool_calls.pop(fallback_id, None)
                removed_by = "fallback_order"
            # #region agent log
            debug_mode_log(
                "run1",
                "H2",
                "orc_core/stream_monitor_state.py:_remember_tool_activity:completed",
                "tool_call completion processed",
                {
                    "call_id": call_id,
                    "removed_by": removed_by,
                    "active_after": len(self._active_tool_calls),
                },
            )
            # #endregion
            if self._active_tool_calls:
                label, is_subagent = self._active_tool_status()
                self._set_live_status(
                    "subagent" if is_subagent else "tool_call",
                    f"running {label}",
                    is_subagent=is_subagent,
                )
            else:
                self._set_live_status("waiting", "waiting for next event", is_subagent=False)
            return
        # #region agent log
        debug_mode_log(
            "run1",
            "H1",
            "orc_core/stream_monitor_state.py:_remember_tool_activity:unhandled",
            "tool_call subtype not handled as lifecycle transition",
            {
                "subtype": subtype_lower,
                "call_id": call_id,
                "active_after": len(self._active_tool_calls),
            },
        )
        # #endregion

    def force_finalize_live_tool_calls(self, reason: str) -> dict[str, object]:
        if not self._active_tool_calls:
            return {"cleared": 0, "reason": str(reason or "").strip() or "unknown"}
        now = time.time()
        pending: list[dict[str, object]] = []
        while self._active_tool_order and self._active_tool_order[0] not in self._active_tool_calls:
            self._active_tool_order.popleft()
        ordered_ids = list(self._active_tool_order) or list(self._active_tool_calls.keys())
        for call_id in ordered_ids:
            entry = self._active_tool_calls.get(call_id)
            if not isinstance(entry, dict):
                continue
            started_at = float(entry.get("started_at") or now)
            pending.append(
                {
                    "call_id": str(call_id),
                    "label": str(entry.get("label") or "tool"),
                    "age_seconds": round(max(now - started_at, 0.0), 3),
                    "is_subagent": bool(entry.get("is_subagent") is True),
                }
            )
        self._active_tool_calls.clear()
        self._active_tool_order.clear()
        normalized_reason = str(reason or "").strip() or "unknown"
        self._set_live_status("waiting", f"waiting after forced tool close: {normalized_reason}", is_subagent=False)
        self._recent_events.append(
            f"[{time.strftime('%H:%M:%S', time.localtime(now))}] tool_call:forced_close {normalized_reason}"
        )
        return {"cleared": len(pending), "reason": normalized_reason, "pending": pending[:5]}

    def active_tool_calls_watchdog_snapshot(self) -> dict[str, object]:
        now = time.time()
        while self._active_tool_order and self._active_tool_order[0] not in self._active_tool_calls:
            self._active_tool_order.popleft()
        if not self._active_tool_calls:
            return {
                "count": 0,
                "oldest_age_seconds": 0.0,
                "oldest_label": "",
                "oldest_is_subagent": False,
            }
        ordered_ids = list(self._active_tool_order) or list(self._active_tool_calls.keys())
        oldest_age = 0.0
        oldest_label = ""
        oldest_is_subagent = False
        for call_id in ordered_ids:
            entry = self._active_tool_calls.get(call_id)
            if not isinstance(entry, dict):
                continue
            started_at = float(entry.get("started_at") or now)
            age_seconds = max(now - started_at, 0.0)
            if age_seconds >= oldest_age:
                oldest_age = age_seconds
                oldest_label = str(entry.get("label") or "tool")
                oldest_is_subagent = bool(entry.get("is_subagent") is True)
        return {
            "count": len(self._active_tool_calls),
            "oldest_age_seconds": round(oldest_age, 3),
            "oldest_label": oldest_label,
            "oldest_is_subagent": oldest_is_subagent,
        }

    def _format_tool_call_with_args(self, payload_key: str, payload: object) -> str:
        if not isinstance(payload, dict):
            return ""
        args = payload.get("args")
        if not isinstance(args, dict):
            return ""

        tool_name = self._tool_call_name(payload_key)
        tool_label = tool_name.lower() if tool_name else "tool"

        command = self._shorten_worktree_paths(self._string_arg(args.get("command")))
        if command:
            return command

        path = self._shorten_worktree_paths(self._string_arg(args.get("path")))
        if tool_label == "read" and path:
            return f"{tool_label} {path}"

        pattern = self._string_arg(args.get("pattern"))
        if tool_label in {"grep", "rg"} and pattern:
            target_path = self._shorten_worktree_paths(self._string_arg(args.get("path")))
            if target_path:
                return f'{tool_label} "{pattern}" in {target_path}'
            return f'{tool_label} "{pattern}"'

        glob_pattern = self._string_arg(args.get("globPattern"))
        target_dir = self._shorten_worktree_paths(self._string_arg(args.get("targetDirectory")))
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
                kv_parts.append(f"{key_name}={self._shorten_worktree_paths(normalized)}")
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
        self._remember_tool_activity(event, event_type, subtype)
        self._last_event_type = event_type or "event"
        self._last_event_note = subtype or "update"
        if event_type == "tool_call" and subtype == "started":
            self.metrics.command_count += 1

        tokens = self.extract_tokens(event)
        structured_entries = self._extract_structured_token_entries(event)
        text = self._extract_text(event)
        if not stream_kind:
            self._recent_events.append(self._summarize_event(event, text))
        structured_applied = False
        if structured_entries:
            total_delta = 0
            for request_key, usage_key, usage_tokens in structured_entries:
                if usage_key in self._seen_token_usage_keys:
                    continue
                self._seen_token_usage_keys.add(usage_key)
                if request_key:
                    previous_max = self._max_tokens_by_request.get(request_key, 0)
                    if usage_tokens > previous_max:
                        total_delta += usage_tokens - previous_max
                        self._max_tokens_by_request[request_key] = usage_tokens
                    continue
                total_delta += usage_tokens
            if total_delta > 0:
                self.metrics.tokens_total = (self.metrics.tokens_total or 0) + total_delta
                self.metrics.tokens_status = "known"
                self.metrics.tokens_source = "structured"
                structured_applied = True
        raw_tokens = self._extract_tokens_from_raw(raw)
        if raw_tokens is not None and (tokens is None or raw_tokens > tokens):
            tokens = raw_tokens
        if tokens is not None and (
            not structured_entries or (not structured_applied and self.metrics.tokens_total is None)
        ):
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
        if event_type in {"thinking", "analysis"}:
            fragment = self._extract_reasoning_fragment(event, text)
            preview = self._trim_fragment(" ".join(fragment.split()).strip()) if fragment else ""
            status = f"thinking {preview}" if preview else "thinking"
            self._set_live_status("thinking", status, is_subagent=False)
        elif event_type == "assistant":
            preview = self._trim_fragment(" ".join(text.split()).strip()) if text else ""
            status = f"responding {preview}" if preview else "responding"
            self._set_live_status("assistant", status, is_subagent=False)
        elif event_type == "result":
            status = str(event.get("status") or subtype or "result").strip().lower() or "result"
            self._set_live_status("waiting", f"result {status}", is_subagent=False)
        elif event_type != "tool_call" and self._active_tool_calls:
            label, is_subagent = self._active_tool_status()
            self._set_live_status(
                "subagent" if is_subagent else "tool_call",
                f"running {label}",
                is_subagent=is_subagent,
            )
        elif event_type not in {"tool_call", "thinking", "analysis", "assistant", "result"}:
            self._set_live_status("waiting", "waiting for output", is_subagent=False)

        self._remember_command(event)
        self._remember_paths(event)
        return event_type, subtype, raw

