#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: release a worker's card lock."""

from __future__ import annotations

from ...board.kanban_distributor import KanbanDistributor


def release_worker(distributor: KanbanDistributor, card_id: str) -> None:
    """Release a card lock held by a worker via the distributor."""
    distributor.release_card(card_id)
