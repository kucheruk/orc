#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skip_card: mark a card DONE and move it to the done column."""

from __future__ import annotations

from orc_core.board.action_constants import Action
from orc_core.board.stage_constants import STAGE_DONE

from ..registry import ActionContext, register_action
from ..validation import require


@register_action("skip_card")
class SkipCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        if card.assigned_agent:
            ctx.board.release_agent(card)
        card.action = Action.DONE.value
        ctx.board.save_card(card)
        ctx.board.move_card(
            card, STAGE_DONE, allow_backward=True,
            reason=f"teamlead skip: {ctx.reason}" if ctx.reason else "teamlead skip",
        )
        ctx.publisher.emit("teamlead", card_id, f"Skipped {card_id} → {STAGE_DONE}: {ctx.reason}")
