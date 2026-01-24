#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from .logging import ORC_ROOT, debug_log, log_event


def _load_telegram_config(log_path: Path) -> dict:
    config_path = ORC_ROOT / ".orc" / "telegram.json"
    if not config_path.exists():
        log_event(log_path, "ERROR", "telegram config missing", path=str(config_path))
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event(log_path, "ERROR", "telegram config invalid", error=str(exc), path=str(config_path))
        return {}


def _resolve_telegram_credentials(log_path: Path) -> tuple[str, str, str]:
    env_token = os.environ.get("ORC_TELEGRAM_TOKEN", "").strip()
    env_chat_id = os.environ.get("ORC_TELEGRAM_CHAT_ID", "").strip()
    if env_token and env_chat_id:
        return env_token, env_chat_id, "env"
    cfg = _load_telegram_config(log_path)
    token = str(cfg.get("token") or "").strip()
    chat_id = str(cfg.get("chat_id") or "").strip()
    return token, chat_id, "config"


def _truncate_message(message: str, max_len: int = 3800) -> tuple[str, bool]:
    if len(message) <= max_len:
        return message, False
    suffix = "\n...(truncated)"
    cutoff = max_len - len(suffix)
    if cutoff <= 0:
        return suffix.strip(), True
    return message[:cutoff] + suffix, True


def send_telegram_message(message: str, log_path: Path) -> None:
    token, chat_id, source = _resolve_telegram_credentials(log_path)
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
    message, truncated = _truncate_message(message)
    if truncated:
        log_event(log_path, "WARN", "telegram message truncated", max_len=3800)
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(api_url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except Exception as exc:
        log_event(log_path, "ERROR", "telegram send failed", error=str(exc))
        debug_log(
            "T2",
            "orc_core/notify.py:send_telegram_message",
            "telegram send failed",
            {"error": str(exc)},
        )
        return
    if not data.get("ok"):
        log_event(log_path, "ERROR", "telegram send error", response=data, raw=raw[:500])
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
