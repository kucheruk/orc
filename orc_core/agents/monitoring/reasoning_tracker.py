#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reasoning / thinking output tracker for stream monitor."""

from __future__ import annotations

import re
import textwrap
from collections import deque
from typing import Deque, Dict, Optional

from ...text_parse import clean_summary_lines


class ReasoningTracker:
    def __init__(self) -> None:
        self._reasoning_buffer = ""
        self._reasoning_stream_kind = ""
        self._recent_reasoning: Deque[str] = deque(maxlen=12)

    @property
    def reasoning_stream_kind(self) -> str:
        return self._reasoning_stream_kind

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

    def _is_reasoning_event(self, event: Dict[str, object], iter_values_fn) -> bool:
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
        for key, _ in iter_values_fn(event):
            if isinstance(key, str) and any(marker in key.lower() for marker in markers):
                return True
        return False

    def _remember_reasoning(self, event: Dict[str, object], text: str, iter_values_fn) -> None:
        if not text.strip() or not self._is_reasoning_event(event, iter_values_fn):
            return
        lines = clean_summary_lines(text.splitlines())
        for line in lines[-5:]:
            self.append_reasoning_fragment(line[:220])
