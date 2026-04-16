#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from orc_core.board.kanban_card import KanbanCard
from orc_core.board.use_cases.check_board_health import diagnose_board_health


class _BoardStub:
    def __init__(self, cards):
        self.cards = cards

    def detect_wip_deadlock(self) -> str:
        return ""


class _DistributorStub:
    def has_remaining_work(self) -> bool:
        return False

    def diagnose_no_work(self) -> str:
        return ""


class TestCheckBoardHealth(unittest.TestCase):
    def test_returns_structured_cycle_metadata(self):
        cards = [
            KanbanCard(id="A-1", stage="2_Estimate", action="Coding", dependencies=["B-1"]),
            KanbanCard(id="B-1", stage="2_Estimate", action="Coding", dependencies=["A-1"]),
        ]
        diagnostic = diagnose_board_health(_BoardStub(cards), _DistributorStub())
        self.assertIsNotNone(diagnostic)
        self.assertTrue(diagnostic.has_cycle)
        self.assertEqual(diagnostic.cycle_edges, (("A-1", "B-1"), ("B-1", "A-1")))
        self.assertIn("Circular dependency detected", diagnostic.deadlock)


if __name__ == "__main__":
    unittest.main()
