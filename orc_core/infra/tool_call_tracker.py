#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tool call lifecycle tracker for stream monitor."""

from __future__ import annotations

import re
import time
from collections import deque
from typing import Deque, Dict

from .debug_log import debug_mode_log


class ToolCallTracker:
    def __init__(self) -> None:
        self._active_tool_calls: dict[str, dict[str, object]] = {}
        self._active_tool_order: Deque[str] = deque(maxlen=32)

    @property
    def active_tool_calls(self) -> dict[str, dict[str, object]]:
        return self._active_tool_calls

    def _tool_call_name(self, payload_key: str) -> str:
        normalized = re.sub(r"ToolCall$", "", payload_key.strip())
        return normalized.strip()

    def _is_subagent_tool(self, tool_label: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]", "", str(tool_label or "").strip().lower())
        return normalized in {"task", "subagent", "subagenttask", "subagentdrivendevelopment"}

    def _tool_call_label_from_event(
        self, event: Dict[str, object], format_fn
    ) -> tuple[str, str]:
        tool_call_payload = event.get("tool_call")
        if isinstance(tool_call_payload, dict):
            for payload_key, payload_value in tool_call_payload.items():
                if not isinstance(payload_key, str) or not payload_key.strip():
                    continue
                tool_name = self._tool_call_name(payload_key)
                formatted = format_fn(payload_key, payload_value)
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

    def _remember_tool_activity(
        self, event: Dict[str, object], event_type: str, subtype: str,
        format_fn, set_live_status_fn,
    ) -> None:
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
            tool_name, label = self._tool_call_label_from_event(event, format_fn)
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
            set_live_status_fn(
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
                set_live_status_fn(
                    "subagent" if is_subagent else "tool_call",
                    f"running {label}",
                    is_subagent=is_subagent,
                )
            else:
                set_live_status_fn("waiting", "waiting for next event", is_subagent=False)
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

    def force_finalize_live_tool_calls(self, reason: str, set_live_status_fn, recent_events: Deque[str]) -> dict[str, object]:
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
        set_live_status_fn("waiting", f"waiting after forced tool close: {normalized_reason}", is_subagent=False)
        recent_events.append(
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

    def _format_tool_call_with_args(self, payload_key: str, payload: object, string_arg_fn, shorten_fn) -> str:
        if not isinstance(payload, dict):
            return ""
        args = payload.get("args")
        if not isinstance(args, dict):
            return ""

        tool_name = self._tool_call_name(payload_key)
        tool_label = tool_name.lower() if tool_name else "tool"

        command = shorten_fn(string_arg_fn(args.get("command")))
        if command:
            return command

        path = shorten_fn(string_arg_fn(args.get("path")))
        if tool_label == "read" and path:
            return f"{tool_label} {path}"

        pattern = string_arg_fn(args.get("pattern"))
        if tool_label in {"grep", "rg"} and pattern:
            target_path = shorten_fn(string_arg_fn(args.get("path")))
            if target_path:
                return f'{tool_label} "{pattern}" in {target_path}'
            return f'{tool_label} "{pattern}"'

        glob_pattern = string_arg_fn(args.get("globPattern"))
        target_dir = shorten_fn(string_arg_fn(args.get("targetDirectory")))
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
            normalized = string_arg_fn(value)
            if normalized:
                kv_parts.append(f"{key_name}={shorten_fn(normalized)}")
            elif isinstance(value, (int, float, bool)):
                kv_parts.append(f"{key_name}={value}")

        if kv_parts:
            return f"{tool_label} " + " ".join(kv_parts[:4])
        return ""
