#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notify: send a Telegram message from the teamlead."""

from __future__ import annotations

from orc_core.notifications.notify import send_telegram_message

from ..registry import ActionContext, register_action


@register_action("notify")
class NotifyHandler:
    def execute(self, ctx: ActionContext) -> None:
        message = str(ctx.params.get("message", "")).strip()
        if not message:
            raise ValueError("Missing required param: 'message'")
        if ctx.log_path is None:
            raise ValueError("notify action requires log_path (internal error)")
        send_telegram_message(message, ctx.log_path)
        ctx.publisher.emit("teamlead", "", f"[TL] Telegram sent: {message[:100]}")
