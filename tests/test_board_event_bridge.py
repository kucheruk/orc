#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from orc_core.agents.infra.board_event_bridge import BoardEventBridge


class BoardEventBridgePublishTest(unittest.TestCase):
    def _make_bridge(self):
        distributor = MagicMock()
        distributor.board = SimpleNamespace()
        publisher = MagicMock()
        outcomes = MagicMock()
        outcomes.is_dirty.return_value = False
        pool = SimpleNamespace(session_snapshots={})
        bridge = BoardEventBridge(
            workdir="/tmp/project",
            distributor=distributor,
            publisher=publisher,
            outcomes=outcomes,
            pool=pool,
        )
        return bridge, distributor, publisher, outcomes

    @patch("orc_core.agents.infra.board_event_bridge.time.time")
    def test_publish_board_state_throttles_refresh(self, time_mock) -> None:
        bridge, distributor, publisher, _outcomes = self._make_bridge()
        time_mock.side_effect = [100.0, 100.2, 102.0]

        bridge.publish_board_state()
        bridge.publish_board_state()
        bridge.publish_board_state()

        self.assertEqual(distributor.refresh.call_count, 2)
        self.assertEqual(publisher.publish_board.call_count, 2)

    @patch("orc_core.agents.infra.board_event_bridge.save_kanban_state")
    @patch("orc_core.agents.infra.board_event_bridge.time.time", return_value=200.0)
    def test_publish_board_state_persists_dirty_outcomes_even_without_publish(
        self,
        _time_mock,
        save_state_mock,
    ) -> None:
        bridge, _distributor, _publisher, outcomes = self._make_bridge()
        outcomes.is_dirty.return_value = True
        outcomes.state_snapshot.return_value = {
            "card_fail_counts": {"TASK-1": 1},
            "arbitrated_at_loop": {"TASK-1": 2},
            "applied_result_runs": ["TASK-1:4_Coding:attempt-1"],
        }
        bridge._last_board_publish_at = 199.9

        bridge.publish_board_state()

        save_state_mock.assert_called_once_with(
            "/tmp/project",
            {"TASK-1": 1},
            {"TASK-1": 2},
            ["TASK-1:4_Coding:attempt-1"],
        )
        outcomes.clear_dirty.assert_called_once()


if __name__ == "__main__":
    unittest.main()
