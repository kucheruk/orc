#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Token counting / extraction tracker for stream monitor."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from ...tasks.ports import MetricsStore


class TokenTracker:
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

    def __init__(self) -> None:
        self._seen_token_usage_keys: set[str] = set()
        self._max_tokens_by_request: dict[str, int] = {}

    def _normalize_token_key(self, key: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(key).strip().lower())

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

    def _extract_token_metric(self, value: Dict[str, object], aliases: set[str]) -> Optional[int]:
        for key, item in value.items():
            if self._normalize_token_key(key) in aliases:
                parsed = self._to_non_negative_int(item)
                if parsed is not None:
                    return parsed
        return None

    def _extract_request_id(self, event: Dict[str, object]) -> Optional[str]:
        for key in ("request_id", "requestId", "response_id", "responseId", "id"):
            value = event.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
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

    def process_event_tokens(self, event: Dict[str, object], raw: str, metrics: "MetricsStore") -> None:
        tokens = self.extract_tokens(event)
        structured_entries = self._extract_structured_token_entries(event)
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
                metrics.tokens_total = (metrics.tokens_total or 0) + total_delta
                metrics.tokens_status = "known"
                metrics.tokens_source = "structured"
                structured_applied = True
        raw_tokens = self._extract_tokens_from_raw(raw)
        if raw_tokens is not None and (tokens is None or raw_tokens > tokens):
            tokens = raw_tokens
        if tokens is not None and (
            not structured_entries or (not structured_applied and metrics.tokens_total is None)
        ):
            metrics.tokens_total = max(metrics.tokens_total or 0, tokens)
            metrics.tokens_status = "known"
            metrics.tokens_source = "heuristic"
