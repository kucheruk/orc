#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

from .logging import ORC_ROOT, debug_log, log_event
from .telegram import post_telegram_message, resolve_telegram_credentials, truncate_telegram_message


def _telegram_disabled() -> bool:
    value = os.environ.get("ORC_TELEGRAM_DISABLE", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def send_telegram_message(message: str, log_path: Path) -> None:
    if _telegram_disabled():
        log_event(log_path, "INFO", "telegram send skipped: disabled via env", env_var="ORC_TELEGRAM_DISABLE")
        debug_log(
            "T0",
            "orc_core/notify.py:send_telegram_message",
            "telegram send skipped via ORC_TELEGRAM_DISABLE",
            {"env_var": "ORC_TELEGRAM_DISABLE"},
        )
        return
    token, chat_id, source = resolve_telegram_credentials(orc_root=ORC_ROOT, log_path=log_path, log_event=log_event)
    if not token or not chat_id:
        log_event(log_path, "ERROR", "telegram credentials missing")
        debug_log(
            "T1",
            "orc_core/notify.py:send_telegram_message",
            "telegram credentials missing",
            {"source": source},
        )
        return
    log_event(log_path, "INFO", "telegram credentials resolved", source=source, chat_id=chat_id)
    debug_log(
        "T1",
        "orc_core/notify.py:send_telegram_message",
        "telegram credentials resolved",
        {"source": source, "chat_id": chat_id},
    )
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
