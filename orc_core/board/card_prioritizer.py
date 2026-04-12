#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Card prioritization: sorting candidates by class-of-service, deadline, ROI."""

from __future__ import annotations

from typing import Callable, Optional

from .kanban_card import KanbanCard
from .kanban_constants import COS_PRIORITY


def priority_key(card: KanbanCard) -> tuple[int, str, float]:
    cos_rank = COS_PRIORITY.get(card.class_of_service, 9)
    deadline = card.deadline if card.class_of_service == "fixed-date" else "9999-12-31"
    return (cos_rank, deadline, -card.roi)


def pick_best(
    candidates: list[KanbanCard],
    *,
    check_deps: Callable[[KanbanCard], bool] | None = None,
) -> Optional[KanbanCard]:
    """Select the highest-priority card from candidates.

    Args:
        candidates: Pre-filtered list of unassigned cards with matching action.
        check_deps: Optional predicate returning True if card has unmet dependencies.
    """
    if check_deps is not None:
        candidates = [c for c in candidates if not check_deps(c)]
    if not candidates:
        return None
    return sorted(candidates, key=priority_key)[0]
