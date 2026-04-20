#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: escalate a card for human attention by blocking it in place."""

from __future__ import annotations

from ...board.gateway import BoardGateway, CardView


def escalate_card(board: BoardGateway, card: CardView, *, reason: str = "") -> None:
    """Block the card in its current stage for human attention.

    Earlier versions forced the card into 7_Handoff. That conflated two
    very different states: a Done/Testing card that failed late
    (where "move back to Handoff" reads as "back to integration
    review") vs. an Estimate/Todo card bouncing between Product and
    Architect because of an unmet dependency — where dropping it into
    Handoff pretended it was integration-ready and stripped the actual
    context (the card had never been coded). It also bypassed the
    normal stage-sequence guard via allow_backward=True, letting
    cards leapfrog stages they never entered.

    BlockedSweepStep already scans every stage for action=Blocked, so
    there is no operational reason to centralize blocked cards in
    Handoff. Keeping the card where it is preserves the work context
    for the human reviewer, and unblock lands back on the exact stage
    the card stalled in rather than a fake Handoff position.
    """
    card.block(reason)
    board.save_card(card)
