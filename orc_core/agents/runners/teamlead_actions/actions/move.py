#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""move_card: relocate a card to another stage (allowing backward moves)."""

from __future__ import annotations

from ..registry import ActionContext, register_action
from ..validation import ensure_stage, require


@register_action("move_card")
class MoveCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        to_stage = require(ctx.params, "to_stage")
        ensure_stage(to_stage)
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        if card.assigned_agent:
            ctx.board.release_agent(card)
        ctx.board.move_card(
            card, to_stage, allow_backward=True,
            reason=f"teamlead: {ctx.reason}" if ctx.reason else "teamlead action",
        )
        ctx.publisher.emit("teamlead", card_id, f"Moved {card_id} → {to_stage}: {ctx.reason}")
