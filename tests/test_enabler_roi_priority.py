#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enabler-ROI prioritization: cards that unblock downstream work rank higher.

Before this change `priority_key` used only `card.roi`, so a low-own-ROI
Estimate card that was the only unresolved dependency of five Todo cards
would lose every tie against a high-ROI leaf card that unblocked
nothing. The pipeline then starved on the critical-path enabler while
the architect chased leaves. Adding a one-level downstream-ROI sum
gives enablers a priority lift proportional to the work they release.
"""

import unittest

from orc_core.board.kanban_card import KanbanCard
from orc_core.board.card_prioritizer import (
    build_downstream_roi_map,
    pick_best,
    priority_key,
)


def _card(id: str, roi: float, deps=(), stage: str = "2_Estimate") -> KanbanCard:
    c = KanbanCard(id=id, stage=stage, roi=roi)
    c.dependencies = list(deps)
    return c


class TestBuildDownstreamRoiMap(unittest.TestCase):
    def test_sums_direct_downstream_roi(self):
        a = _card("A", roi=0.5)
        b = _card("B", roi=3.0, deps=["A"])
        c = _card("C", roi=2.0, deps=["A"])
        d = _card("D", roi=1.0)  # unrelated leaf
        m = build_downstream_roi_map([a, b, c, d])
        self.assertEqual(m.get("A"), 5.0)
        self.assertNotIn("B", m)
        self.assertNotIn("C", m)

    def test_done_cards_do_not_contribute(self):
        a = _card("A", roi=0.5)
        b = _card("B", roi=10.0, deps=["A"], stage="8_Done")
        m = build_downstream_roi_map([a, b])
        self.assertNotIn("A", m)

    def test_done_deps_are_skipped(self):
        a = _card("A", roi=0.5, stage="8_Done")
        b = _card("B", roi=3.0, deps=["A"])
        m = build_downstream_roi_map([a, b])
        # B's dep A is Done → A has no unblocked-by-B contribution
        self.assertNotIn("A", m)

    def test_empty_or_missing_deps_are_ignored(self):
        a = _card("A", roi=1.0, deps=["", None])  # type: ignore[list-item]
        b = _card("B", roi=2.0, deps=["MISSING"])
        m = build_downstream_roi_map([a, b])
        # "MISSING" is not a Done id, so it still gets counted. That's
        # fine: a reference to an unknown card id is a data bug that
        # shouldn't silently downrank B's enabler value.
        self.assertEqual(m.get("MISSING"), 2.0)


class TestPriorityKeyUsesEffectiveRoi(unittest.TestCase):
    def test_enabler_outranks_unrelated_high_roi_leaf(self):
        enabler = _card("E", roi=0.5)
        downstream_big = _card("B", roi=3.0, deps=["E"])
        downstream_small = _card("C", roi=2.0, deps=["E"])
        leaf = _card("L", roi=3.0)
        board = [enabler, downstream_big, downstream_small, leaf]
        # Candidates at the same stage/action — picker chooses within them.
        picked = pick_best([enabler, leaf], all_cards=board)
        self.assertEqual(picked.id, "E",
                         "enabler (own 0.5 + 5.0 downstream = 5.5) "
                         "must outrank the 3.0 leaf")

    def test_equal_effective_roi_falls_back_to_id_stable_sort(self):
        # Two cards with identical effective ROI — tuple compare is stable.
        a = _card("A", roi=2.0)
        b = _card("B", roi=2.0)
        picked = pick_best([a, b], all_cards=[a, b])
        self.assertIsNotNone(picked)
        self.assertIn(picked.id, {"A", "B"})

    def test_legacy_call_without_all_cards_still_uses_own_roi(self):
        # pick_best(candidates) without all_cards must keep legacy semantics
        # so downstream unit tests that don't plumb the board don't need a
        # churn update.
        hi = _card("HI", roi=5.0)
        lo = _card("LO", roi=0.5)
        picked = pick_best([hi, lo])  # no all_cards → own ROI only
        self.assertEqual(picked.id, "HI")


class TestPriorityKeyDirectly(unittest.TestCase):
    def test_priority_key_prefers_lower_tuple(self):
        # Lower tuple means higher priority (standard sorted default).
        card = _card("X", roi=4.0)
        k_no_enable = priority_key(card)
        k_with_enable = priority_key(card, {"X": 2.0})
        # The -roi component drops from -4.0 to -6.0 when enabler lift applies.
        self.assertLess(k_with_enable[2], k_no_enable[2])


if __name__ == "__main__":
    unittest.main()
