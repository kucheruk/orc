#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""create_card: create a new inbox or expedite card."""

from __future__ import annotations

from orc_core.board.stage_constants import STAGE_INBOX
from orc_core.board.use_cases.create_card import (
    create_expedite_card,
    create_inbox_card,
)

from ..registry import ActionContext, register_action
from ..validation import ensure_action, ensure_stage, require


@register_action("create_card")
class CreateCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        title = require(ctx.params, "title")
        stage = str(ctx.params.get("stage", STAGE_INBOX))
        action_str = str(ctx.params.get("action", "Product"))
        body = str(ctx.params.get("body", ""))
        ensure_stage(stage)
        ensure_action(action_str)
        if stage == STAGE_INBOX:
            card = create_inbox_card(ctx.board, title)
        else:
            card = create_expedite_card(
                ctx.board, title, body or "",
                stage=stage, action=action_str, cos_justification=ctx.reason,
            )
        ctx.publisher.emit("teamlead", card.id, f"Created {card.id}: {title}: {ctx.reason}")
