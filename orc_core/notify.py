#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from .logging import ORC_ROOT, log_event
from .debug_log import debug_log
from .telegram import post_telegram_message, resolve_telegram_credentials, truncate_telegram_message


class Notifier(Protocol):
    """Abstraction for sending notifications."""

    def send(self, message: str) -> None: ...

# Cache telegram availability to avoid repeated credential lookups.
# None = not checked yet, True = available, False = unavailable.
_telegram_checked: bool = False
_telegram_ok: bool = False
_telegram_token: str = ""
_telegram_chat_id: str = ""


def _telegram_disabled() -> bool:
    value = os.environ.get("ORC_TELEGRAM_DISABLE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _resolve_once(log_path: Path, orc_root: Path) -> tuple[str, str]:
    """Resolve credentials once and cache. Returns (token, chat_id)."""
    global _telegram_checked, _telegram_ok, _telegram_token, _telegram_chat_id
    if _telegram_checked:
        return _telegram_token, _telegram_chat_id
    _telegram_checked = True
    token, chat_id, source = resolve_telegram_credentials(
        orc_root=orc_root, log_path=log_path, log_event=log_event,
    )
    if token and chat_id:
        _telegram_ok = True
        _telegram_token = token
        _telegram_chat_id = chat_id
        log_event(log_path, "INFO", "telegram credentials resolved", source=source, chat_id=chat_id)
    else:
        log_event(log_path, "INFO", "telegram not configured, notifications disabled for this session")
    return _telegram_token, _telegram_chat_id


def send_telegram_message(message: str, log_path: Path, *, orc_root: Path | None = None) -> None:
    if _telegram_disabled():
        return
    token, chat_id = _resolve_once(log_path, orc_root or ORC_ROOT)
    if not token or not chat_id:
        return
    message, truncated = truncate_telegram_message(message)
    if truncated:
        log_event(log_path, "WARN", "telegram message truncated", max_len=3800)
    data, raw, error = post_telegram_message(token=token, chat_id=chat_id, message=message, timeout=15)
    if error:
        log_event(log_path, "ERROR", "telegram send failed", error=error)
        debug_log(
            "T2",
            "orc_core/notify.py:send_telegram_message",
            "telegram send failed",
            {"error": error},
        )
        return
    if not isinstance(data, dict) or not data.get("ok"):
        raw_preview = (raw or "")[:500]
        log_event(log_path, "ERROR", "telegram send error", response=data, raw=raw_preview)
        debug_log(
            "T3",
            "orc_core/notify.py:send_telegram_message",
            "telegram send error",
            {"response": data},
        )
        return
    log_event(log_path, "INFO", "telegram sent", response=data)
    debug_log(
        "T4",
        "orc_core/notify.py:send_telegram_message",
        "telegram sent",
        {"response": data},
    )


class TelegramNotifier:
    """Concrete Notifier implementation backed by Telegram."""

    def __init__(self, log_path: Path, orc_root: Path | None = None) -> None:
        self._log_path = log_path
        self._orc_root = orc_root

    def send(self, message: str) -> None:
        send_telegram_message(message, self._log_path, orc_root=self._orc_root)
