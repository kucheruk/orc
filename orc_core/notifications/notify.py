#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Protocol

from ..log import log_event
from ..infra.io.logging import ORC_ROOT
from ..infra.io.debug_log import debug_log
from .telegram import post_telegram_message, resolve_telegram_credentials, truncate_telegram_message


class Notifier(Protocol):
    """Abstraction for sending notifications."""

    def send(self, message: str) -> None: ...


def _telegram_disabled() -> bool:
    value = os.environ.get("ORC_TELEGRAM_DISABLE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


class TelegramNotifier:
    """Concrete Telegram-backed notifier with pre-resolved credentials."""

    def __init__(self, token: str, chat_id: str) -> None:
        self._token = token
        self._chat_id = chat_id

    def send(self, message: str, log_path: Path) -> None:
        message, truncated = truncate_telegram_message(message)
        if truncated:
            log_event(log_path, "WARN", "telegram message truncated", max_len=3800)
        data, raw, error = post_telegram_message(
            token=self._token, chat_id=self._chat_id, message=message, timeout=15,
        )
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


def resolve_telegram_notifier(log_path: Path, orc_root: Path) -> Optional[TelegramNotifier]:
    """Resolve Telegram credentials and return a notifier instance, or None if unavailable."""
    token, chat_id, source = resolve_telegram_credentials(
        orc_root=orc_root, log_path=log_path, log_event=log_event,
    )
    if token and chat_id:
        log_event(log_path, "INFO", "telegram credentials resolved", source=source, chat_id=chat_id)
        return TelegramNotifier(token=token, chat_id=chat_id)
    log_event(log_path, "INFO", "telegram not configured, notifications disabled for this session")
    return None


def send_telegram_message(message: str, log_path: Path, *, orc_root: Path | None = None) -> None:
    if _telegram_disabled():
        return
    notifier = resolve_telegram_notifier(log_path, orc_root or ORC_ROOT)
    if notifier is None:
        return
    notifier.send(message, log_path)


def _notify_mode() -> str:
    raw = str(os.environ.get("ORC_NOTIFY_MODE", "normal") or "normal").strip().lower()
    return raw if raw in {"normal", "debug"} else "normal"


def send_severity(envelope, log_path: Path, *, orc_root: Path | None = None) -> None:
    """Deliver a `(Severity, text)` envelope respecting ORC_NOTIFY_MODE.

    Used by call sites outside NotificationService (CLI startup/shutdown,
    ad-hoc teamlead actions). Info-level messages are dropped in normal mode.
    """
    if envelope is None:
        return
    from .messages import Severity
    severity, text = envelope
    if _notify_mode() != "debug" and severity == Severity.INFO:
        return
    send_telegram_message(text, log_path, orc_root=orc_root)
