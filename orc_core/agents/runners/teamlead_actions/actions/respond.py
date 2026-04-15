#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""respond: emit a plain message on the teamlead channel."""

from __future__ import annotations

from ..registry import ActionContext, register_action


@register_action("respond")
class RespondHandler:
    def execute(self, ctx: ActionContext) -> None:
        msg = str(ctx.params.get("message", ""))
        if msg:
            ctx.publisher.emit("teamlead", "", msg)
