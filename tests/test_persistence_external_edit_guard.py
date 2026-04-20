#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BoardCardPersistence must not clobber external edits.

An operator editing a card file by hand while ORC is running bumps the
state_version on disk. Before this guard, ORC's next save_card would
race in and overwrite the edit with stale in-memory YAML — exactly the
"human reset of EMP-001 got reverted" incident.

Guard: on every save/assign/release, compare disk state_version to the
in-memory copy. If disk is newer, abort the write (and let the next
board.refresh() reconcile).
"""

import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from orc_core.board.board_card_persistence import BoardCardPersistence
from orc_core.board.board_listeners import BoardListenerBus
from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.kanban_card_serializer import card_to_markdown, parse_card


def _write_card_to(path: Path, card: KanbanCard) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    card.file_path = path
    path.write_text(card_to_markdown(card), encoding="utf-8")


class TestExternalEditGuard(unittest.TestCase):
    def _persistence(self) -> BoardCardPersistence:
        lock = threading.RLock()
        return BoardCardPersistence(
            repo=FsCardRepository(),
            lock=lock,
            listeners=BoardListenerBus(lock=lock),
        )

    def _reload(self, path: Path) -> KanbanCard:
        return parse_card(path.read_text(encoding="utf-8"), file_path=path)

    def test_save_aborts_when_disk_state_version_newer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "4_Coding" / "X-1.md"
            # In-memory card at state_version 5.
            card = KanbanCard(id="X-1", stage="4_Coding", action="Coding")
            card.state_version = 5
            _write_card_to(path, card)

            # Simulate operator hand-edit: bump state_version on disk + change
            # action to "Blocked". ORC still holds the old in-memory copy.
            operator_card = self._reload(path)
            operator_card.action = "Blocked"
            operator_card.state_version = 10
            path.write_text(card_to_markdown(operator_card), encoding="utf-8")

            # ORC's in-memory card tries to save its own mutation.
            card.action = "Reviewing"
            # card.state_version is STILL 5 in memory.
            self._persistence().save(card)

            # Disk still reflects the operator's edit, unchanged by ORC's save.
            reloaded = self._reload(path)
            self.assertEqual(reloaded.action, "Blocked")
            self.assertEqual(reloaded.state_version, 10)

    def test_save_proceeds_when_disk_matches_memory(self):
        """Normal flow: disk has the version the card was loaded at. Save
        applies and bumps state_version by one."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "4_Coding" / "X-2.md"
            card = KanbanCard(id="X-2", stage="4_Coding", action="Coding")
            card.state_version = 3
            _write_card_to(path, card)

            card.action = "Reviewing"
            self._persistence().save(card)

            reloaded = self._reload(path)
            self.assertEqual(reloaded.action, "Reviewing")
            self.assertGreater(reloaded.state_version, 3)

    def test_assign_aborts_on_external_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "4_Coding" / "X-3.md"
            card = KanbanCard(id="X-3", stage="4_Coding", action="Coding")
            card.state_version = 1
            _write_card_to(path, card)

            operator = self._reload(path)
            operator.action = "Blocked"
            operator.state_version = 99
            path.write_text(card_to_markdown(operator), encoding="utf-8")

            self._persistence().assign(card, "s2")

            reloaded = self._reload(path)
            self.assertEqual(reloaded.action, "Blocked",
                             "operator's action preserved")
            self.assertEqual(reloaded.assigned_agent, "",
                             "ORC's assign must not have landed")

    def test_missing_file_does_not_block_save(self):
        """If the card file doesn't exist yet, there's nothing to clobber
        — save must proceed normally so the first write actually creates
        the file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "4_Coding" / "X-4.md"
            card = KanbanCard(id="X-4", stage="4_Coding", action="Coding")
            card.state_version = 0
            card.file_path = path
            path.parent.mkdir(parents=True, exist_ok=True)
            # Don't pre-write the file — disk peek will return None.

            self._persistence().save(card)

            self.assertTrue(path.exists())
            reloaded = self._reload(path)
            self.assertEqual(reloaded.id, "X-4")


if __name__ == "__main__":
    unittest.main()
