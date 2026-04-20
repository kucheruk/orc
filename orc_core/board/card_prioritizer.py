#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Card prioritization: sorting candidates by class-of-service, deadline, ROI.

ROI here is "effective ROI" — the card's own ROI plus the ROI of every
still-active card that depends on it. Cards that unblock downstream
work climb the queue so the pipeline doesn't starve on low-own-ROI
enablers (e.g. an Estimate card whose architecture step unblocks five
Todo cards worth picking sooner than a high-ROI leaf that unblocks
nothing). Summation is one-level on purpose — it keeps the math O(N)
over the board and avoids the cycle/weighting headaches of transitive
closure while still capturing the dominant critical-path signal.
"""

from __future__ import annotations

import logging
from typing import Callable, Iterable, Optional

from .kanban_card import KanbanCard
from .action_constants import COS_PRIORITY, ClassOfService


def build_downstream_roi_map(all_cards: Iterable[KanbanCard]) -> dict[str, float]:
    """Map card_id → sum of ROIs of non-Done cards that list it as a dep.

    Passing every active card on the board (including the Done set, so
    closed deps are skipped correctly) is cheap — computation is linear
    in total dependency edges.
    """
    cards_list = list(all_cards)
    done_ids = {c.id for c in cards_list if c.is_done}
    downstream: dict[str, float] = {}
    for c in cards_list:
        if c.is_done:
            continue
        for dep_id in c.dependencies:
            if not dep_id or dep_id in done_ids:
                continue
            downstream[dep_id] = downstream.get(dep_id, 0.0) + float(c.roi or 0.0)
    return downstream


def _effective_roi(card: KanbanCard, downstream_roi: dict[str, float]) -> float:
    return float(card.roi or 0.0) + downstream_roi.get(card.id, 0.0)


def priority_key(
    card: KanbanCard,
    downstream_roi: Optional[dict[str, float]] = None,
) -> tuple[int, str, float]:
    cos_rank = COS_PRIORITY.get(card.class_of_service, 9)
    deadline = card.deadline if card.class_of_service == ClassOfService.FIXED_DATE else "9999-12-31"
    eff = _effective_roi(card, downstream_roi) if downstream_roi else float(card.roi or 0.0)
    return (cos_rank, deadline, -eff)


def pick_best(
    candidates: list[KanbanCard],
    *,
    check_deps: Callable[[KanbanCard], bool] | None = None,
    all_cards: Optional[Iterable[KanbanCard]] = None,
) -> Optional[KanbanCard]:
    """Select the highest-priority card from candidates.

    Args:
        candidates: Pre-filtered list of unassigned cards with matching action.
        check_deps: Optional predicate returning True if card has unmet dependencies.
        all_cards: Full board view for enabler-ROI lift. If omitted, falls back
            to plain per-card ROI (legacy behavior; keep this for unit tests).
    """
    exhausted = [c for c in candidates if c.is_budget_exhausted]
    if exhausted:
        logging.getLogger(__name__).info(
            "pick_best: filtered %d budget-exhausted cards: %s",
            len(exhausted), [c.id for c in exhausted],
        )
    candidates = [c for c in candidates if not c.is_budget_exhausted]
    if check_deps is not None:
        candidates = [c for c in candidates if not check_deps(c)]
    if not candidates:
        return None
    downstream = build_downstream_roi_map(all_cards) if all_cards is not None else None
    return sorted(candidates, key=lambda c: priority_key(c, downstream))[0]
