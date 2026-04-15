#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stateless utilities for extracting text content from stream events."""

from typing import Dict


def iter_event_values(value: object):
    """Recursively yield (key, inner_value) pairs from dicts and lists."""
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key, inner
            yield from iter_event_values(inner)
    elif isinstance(value, list):
        for item in value:
            yield from iter_event_values(item)


def extract_text(event: Dict[str, object]) -> str:
    """Extract human-readable text content from a stream event."""
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


def string_arg(value: object) -> str:
    """Normalize a value to a single-line string."""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    return ""
