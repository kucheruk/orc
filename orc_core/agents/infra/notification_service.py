#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification service: Telegram messages + project hooks on card events."""

from __future__ import annotations

from pathlib import Path

from ...board.kanban_card import KanbanCard
from ...board.stage_constants import STAGE_SHORT_NAMES
from ...board.kanban_notifications import format_completion_message
from ...git.project_hooks import fire_hooks
from ...notifications.notify import send_telegram_message


class NotificationService:
    """Sends Telegram messages and fires project hooks on card lifecycle events."""

    def __init__(self, *, workdir: str, log_path: Path, get_progress) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._get_progress = get_progress

    def send_telegram(self, message: str) -> None:
        send_telegram_message(message, self._log_path, orc_root=Path(self._workdir))

    def notify_completion(
        self,
        card: KanbanCard,
        role: str,
        old_stage: str,
        old_action: str,
        old_cos: str,
        elapsed: float,
    ) -> None:
        msg = format_completion_message(
            card, role, old_stage, old_action, old_cos, elapsed,
            self._get_progress(),
        )
        if msg:
            self.send_telegram(msg)

        fr = STAGE_SHORT_NAMES.get(old_stage, old_stage)
        to = STAGE_SHORT_NAMES.get(card.stage, card.stage)
        fire_hooks(self._workdir, "on_complete", {
            "ORC_CARD_ID": card.id,
            "ORC_CARD_TITLE": card.title,
            "ORC_FROM_STAGE": fr,
            "ORC_TO_STAGE": to,
            "ORC_ROLE": role,
            "ORC_REASON": f"{old_action} -> {card.action}",
            "ORC_ELAPSED_MIN": f"{elapsed / 60.0:.1f}",
        })
