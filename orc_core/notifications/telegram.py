#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

LogFn = Callable[[Path, str, str], None]


def load_telegram_config(*, orc_root: Path, log_path: Path, log_event: LogFn) -> dict:
    from ..infra.io.logging import ORC_ROOT

    candidates = [
        orc_root / ".orc" / "telegram.json",
    ]
    # Fall back to the ORC installation directory (where the config usually lives)
    if orc_root.resolve() != ORC_ROOT.resolve():
        candidates.append(ORC_ROOT / ".orc" / "telegram.json")
    # Fall back to global user config
    from ..persistence.state_paths import telegram_config_path
    candidates.append(telegram_config_path())

    for config_path in candidates:
        if config_path.exists():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except Exception as exc:
                log_event(log_path, "ERROR", "telegram config invalid", error=str(exc), path=str(config_path))
                return {}

    log_event(log_path, "ERROR", "telegram config missing",
              searched=[str(c) for c in candidates])
    return {}


def resolve_telegram_credentials(*, orc_root: Path, log_path: Path, log_event: LogFn) -> tuple[str, str, str]:
    env_token = os.environ.get("ORC_TELEGRAM_TOKEN", "").strip()
    env_chat_id = os.environ.get("ORC_TELEGRAM_CHAT_ID", "").strip()
    if env_token and env_chat_id:
        return env_token, env_chat_id, "env"
    cfg = load_telegram_config(orc_root=orc_root, log_path=log_path, log_event=log_event)
    token = str(cfg.get("token") or "").strip()
    chat_id = str(cfg.get("chat_id") or "").strip()
    return token, chat_id, "config"


def truncate_telegram_message(message: str, max_len: int = 3800) -> tuple[str, bool]:
    if len(message) <= max_len:
        return message, False
    suffix = "\n...(truncated)"
    cutoff = max_len - len(suffix)
    if cutoff <= 0:
        return suffix.strip(), True
    return message[:cutoff] + suffix, True


def post_telegram_message(*, token: str, chat_id: str, message: str, timeout: int = 15) -> tuple[Optional[dict], Optional[str], Optional[str]]:
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
    request = urllib.request.Request(api_url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            return data, raw, None
    except Exception as exc:
        return None, None, str(exc)
