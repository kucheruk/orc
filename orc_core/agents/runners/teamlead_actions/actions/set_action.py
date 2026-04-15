#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""set_action: change a card's Action and forward-move when possible."""

from __future__ import annotations

from orc_core.agents.infra.agent_output import _FORWARD_MOVES

from ..registry import ActionContext, register_action
from ..validation import ensure_action, require


@register_action("set_action")
class SetActionHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        action_str = require(ctx.params, "action")
        ensure_action(action_str)
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        old = card.action
        card.action = action_str
        if card.assigned_agent:
            ctx.board.release_agent(card)
        ctx.board.save_card(card, old_action=old, role="teamlead")
        new_stage = _FORWARD_MOVES.get((card.stage, action_str))
        if new_stage and ctx.board.has_wip_room(new_stage):
            ctx.board.move_card(card, new_stage, reason=f"teamlead: {old} → {action_str}")
            ctx.publisher.emit("teamlead", card_id,
                               f"{card_id} action: {old} → {action_str}, moved → {new_stage}: {ctx.reason}")
        else:
            ctx.publisher.emit("teamlead", card_id, f"{card_id} action: {old} → {action_str}: {ctx.reason}")
