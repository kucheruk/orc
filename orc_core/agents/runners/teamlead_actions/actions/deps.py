#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""modify_deps: add/remove dependency ids on a card."""

from __future__ import annotations

from ..registry import ActionContext, register_action
from ..validation import require


@register_action("modify_deps")
class ModifyDepsHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        to_add = ctx.params.get("add", []) or []
        to_remove = ctx.params.get("remove", []) or []
        if not isinstance(to_add, list):
            to_add = [to_add]
        if not isinstance(to_remove, list):
            to_remove = [to_remove]
        to_add = [str(d) for d in to_add]
        to_remove = [str(d) for d in to_remove]
        changed = False
        for dep in to_remove:
            if dep in card.dependencies:
                card.dependencies.remove(dep)
                changed = True
        for dep in to_add:
            if dep not in card.dependencies:
                card.dependencies.append(dep)
                changed = True
        if changed:
            ctx.board.save_card(card)
            ctx.publisher.emit("teamlead", card_id,
                               f"{card_id} deps: +[{','.join(to_add)}] -[{','.join(to_remove)}]: {ctx.reason}")
