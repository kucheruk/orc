#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: assign a card to a worker agent."""

from __future__ import annotations

from ...board.kanban_card import KanbanCard
from ...board.kanban_distributor import KanbanDistributor


def assign_worker(
    distributor: KanbanDistributor,
    card: KanbanCard,
    worker_id: str,
) -> bool:
    """Assign a card to a worker through the distributor.

    Returns True when the assignment was recorded, False when the card is
    already claimed by another agent.
    """
    if card.assigned_agent and card.assigned_agent != worker_id:
        return False
    distributor.board.assign_agent(card, worker_id)
    return True
