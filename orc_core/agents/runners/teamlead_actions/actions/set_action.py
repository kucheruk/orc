#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""set_action: change a card's Action and forward-move when possible."""

from __future__ import annotations

from orc_core.board.action_constants import Action
from orc_core.board.state_machine import FORWARD_MOVES

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
        # Reject teamlead attempts to flip a deps-gated card into Blocked.
        # "Waiting on upstream card X" is a system-gated state — pull
        # strategies already refuse to pick up the card until its
        # dependencies are Done — so there is nothing a human reviewer can
        # productively act on. The card only sits idle while BlockedSweep
        # pings operators and every subsequent teamlead arbitration burns
        # tokens re-reading the accumulated "## Block Reason" body.
        # Observed on jeeves 2026-04-20: NOTIF-004-B (deps NOTIF-004-A in
        # Coding) and QA-003-A (deps QA-001-C/QA-002-C in Estimate) were
        # both routed to Blocked through this path even though nothing
        # human-actionable was pending.
        if (
            action_str == Action.BLOCKED
            and old != Action.BLOCKED
            and ctx.board.has_unmet_dependencies(card)
        ):
            ctx.publisher.emit(
                "teamlead",
                card_id,
                f"{card_id} block rejected: deps-gated (system waits, not human)",
            )
            raise ValueError(
                f"Cannot set {card_id}=Blocked: card has unmet dependencies "
                "and is already system-gated; Blocked is for human-actionable issues only."
            )
        # When teamlead transitions a Blocked card to anything non-Blocked,
        # route through KanbanCard.unblock so the cleanup invariants run:
        # strip accumulated "## Block Reason" sections, reset loop_count /
        # finalize_retries, and offset tokens_discarded to match tokens_spent
        # so the recovered card isn't immediately re-blocked by the budget
        # check on the very next pick_best. Bypassing unblock (as the old
        # direct card.action = action_str did) leaves all that state stale
        # and turns teamlead arbitration into a no-op — observed as
        # AUDIT-001-C bouncing Blocked → Arbitration → Blocked every ~60s.
        if old == Action.BLOCKED and action_str != Action.BLOCKED:
            card.unblock()
            card.action = action_str
        else:
            card.action = action_str
        if card.assigned_agent:
            ctx.board.release_agent(card)
        ctx.board.save_card(card, old_action=old, role="teamlead")
        new_stage = FORWARD_MOVES.get((card.stage, action_str))
        if new_stage and ctx.board.has_wip_room(new_stage):
            ctx.board.move_card(card, new_stage, reason=f"teamlead: {old} → {action_str}")
            ctx.publisher.emit("teamlead", card_id,
                               f"{card_id} action: {old} → {action_str}, moved → {new_stage}: {ctx.reason}")
        else:
            ctx.publisher.emit("teamlead", card_id, f"{card_id} action: {old} → {action_str}: {ctx.reason}")
