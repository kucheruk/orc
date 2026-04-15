#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""set_wip_limit: change a stage's WIP limit."""

from __future__ import annotations

from ..registry import ActionContext, register_action
from ..validation import ensure_stage, require


@register_action("set_wip_limit")
class SetWipLimitHandler:
    def execute(self, ctx: ActionContext) -> None:
        stage = require(ctx.params, "stage")
        limit = int(require(ctx.params, "limit"))
        ensure_stage(stage)
        if limit < 1:
            raise ValueError(f"WIP limit must be >= 1, got {limit}")
        ctx.board.set_wip_limit(stage, limit)
        ctx.publisher.emit("teamlead", "", f"WIP {stage}: → {limit}: {ctx.reason}")
