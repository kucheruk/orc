#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapters implementing supervision NotifyPort."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import notify as _notify_module


class TelegramNotify:
    """NotifyPort adapter that delivers messages via Telegram."""

    def __init__(self, log_path: Path, *, orc_root: Optional[Path] = None) -> None:
        self._log_path = log_path
        self._orc_root = orc_root

    def send(self, message: str) -> None:
        _notify_module.send_telegram_message(message, self._log_path, orc_root=self._orc_root)
