#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notification service: Telegram messages + project hooks on card events."""

from __future__ import annotations

import os
from pathlib import Path

from ...board.kanban_card import KanbanCard
from ...board.stage_constants import STAGE_SHORT_NAMES
from ...board.kanban_notifications import format_completion_message
from ...git.project_hooks import fire_hooks
from ...notifications.messages import (
    Severity,
    format_blocked_accumulation,
    format_card_blocked,
    format_card_skipped,
    format_cycle_autounblock,
    format_escalation,
    format_orc_shutdown,
    format_orc_startup,
    format_stale_assignments_released,
    with_teamlead_signature,
)
from ...notifications.notify import send_telegram_message


_VALID_MODES = ("normal", "debug")


def _current_mode() -> str:
    raw = str(os.environ.get("ORC_NOTIFY_MODE", "normal") or "normal").strip().lower()
    return raw if raw in _VALID_MODES else "normal"


def _should_deliver(severity: Severity) -> bool:
    """Drop `INFO` messages in normal mode; pass everything in debug."""
    if _current_mode() == "debug":
        return True
    return severity != Severity.INFO


class NotificationService:
    """Sends Telegram messages and fires project hooks on card lifecycle events."""

    def __init__(self, *, workdir: str, log_path: Path, get_progress) -> None:
        self._workdir = workdir
        self._log_path = log_path
        self._get_progress = get_progress

    def _dispatch(self, envelope: tuple[Severity, str] | None) -> None:
        if envelope is None:
            return
        severity, message = envelope
        if not _should_deliver(severity):
            return
        send_telegram_message(message, self._log_path, orc_root=Path(self._workdir))

    def send_telegram(self, message: str) -> None:
        """Raw send — always delivered. Kept for legacy callers; prefer the
        severity-aware ``_dispatch`` via a formatter."""
        send_telegram_message(message, self._log_path, orc_root=Path(self._workdir))

    def notify_card_blocked(self, card_id: str, count: int, reason: str) -> None:
        self._dispatch(format_card_blocked(card_id, count, reason))

    def notify_escalation(self, card_id: str, title: str, stage: str, loop_count: int) -> None:
        # Escalation decisions come from the teamlead loop — sign them.
        self._dispatch(with_teamlead_signature(*format_escalation(card_id, title, stage, loop_count)))

    def notify_cycle_autounblock(self, from_id: str, to_id: str, decomposition_id: str) -> None:
        self._dispatch(with_teamlead_signature(*format_cycle_autounblock(from_id, to_id, decomposition_id)))

    def notify_stale_assignments_released(self, count: int) -> None:
        self._dispatch(with_teamlead_signature(*format_stale_assignments_released(count)))

    def notify_blocked_accumulation(self, cards: list[tuple[str, str]]) -> None:
        if not cards:
            return
        self._dispatch(with_teamlead_signature(*format_blocked_accumulation(cards)))

    def notify_card_skipped(self, card_id: str, reason: str = "") -> None:
        self._dispatch(with_teamlead_signature(*format_card_skipped(card_id, reason)))

    def notify_orc_startup(self, workspace: str, max_sessions: int) -> None:
        self._dispatch(format_orc_startup(workspace, max_sessions))

    def notify_orc_shutdown(self, reason: str = "") -> None:
        self._dispatch(format_orc_shutdown(reason))

    def notify_completion(
        self,
        card: KanbanCard,
        role: str,
        old_stage: str,
        old_action: str,
        old_cos: str,
        elapsed: float,
    ) -> None:
        envelope = format_completion_message(
            card, role, old_stage, old_action, old_cos, elapsed,
            self._get_progress(),
        )
        self._dispatch(envelope)

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
