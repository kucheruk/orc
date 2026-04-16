#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""write_feedback: append text into a card's Feedback & Checklist section."""

from __future__ import annotations

from .....board.kanban_card import SECTION_FEEDBACK
from ..registry import ActionContext, register_action
from ..validation import require


@register_action("write_feedback")
class WriteFeedbackHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        text = str(ctx.params.get("text", "")).strip()
        if not text:
            raise ValueError("Missing required param: 'text'")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        body = card.body or ""
        if SECTION_FEEDBACK in body:
            body = body.rstrip() + "\n\n" + text + "\n"
        else:
            body = body.rstrip() + f"\n\n{SECTION_FEEDBACK}\n\n{text}\n"
        card.body = body
        ctx.board.save_card(card)
        ctx.publisher.emit("teamlead", card_id, f"{card_id} feedback updated: {ctx.reason}")
