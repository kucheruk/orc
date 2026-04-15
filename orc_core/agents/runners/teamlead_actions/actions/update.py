#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_card: mutate a whitelisted field on a card."""

from __future__ import annotations

from ..registry import ActionContext, register_action
from ..validation import require

_UPDATABLE_FIELDS = frozenset({
    "value_score", "effort_score", "class_of_service",
    "cos_justification", "deadline", "loop_count", "title",
})


@register_action("update_card")
class UpdateCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = require(ctx.params, "card_id")
        field_name = require(ctx.params, "field")
        value = require(ctx.params, "value")
        if field_name not in _UPDATABLE_FIELDS:
            raise ValueError(f"Field '{field_name}' not updatable (allowed: {', '.join(sorted(_UPDATABLE_FIELDS))})")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        old_val = getattr(card, field_name, None)
        if field_name in ("value_score", "effort_score", "loop_count"):
            if not isinstance(value, (int, float, str)):
                raise ValueError(f"Expected number for {field_name}, got {type(value).__name__}")
            value = int(value)
        setattr(card, field_name, value)
        card.refresh_roi()
        ctx.board.save_card(card)
        ctx.publisher.emit("teamlead", card_id, f"{card_id}.{field_name}: {old_val} → {value}: {ctx.reason}")
