#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path

from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_card import KanbanCard
from orc_core.git.worktree_card_sync import sync_card_to_worktree


class WorktreeCardSyncTest(unittest.TestCase):
    def test_sync_card_to_worktree_replaces_stale_stage_copy(self) -> None:
        repo = FsCardRepository()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "repo" / "tasks" / "5_Review" / "CTRL-001.md"
            stale = root / "wt" / "tasks" / "4_Coding" / "CTRL-001.md"
            canonical.parent.mkdir(parents=True, exist_ok=True)
            stale.parent.mkdir(parents=True, exist_ok=True)

            card = KanbanCard(id="CTRL-001", stage="5_Review", action="Reviewing", body="fresh body")
            repo.write_card(card, canonical)
            stale.write_text("---\nid: CTRL-001\nstage: 4_Coding\naction: Coding\n---\n\nstale body", encoding="utf-8")

            synced = sync_card_to_worktree(card, str(root / "wt"))

            self.assertEqual(synced, root / "wt" / "tasks" / "5_Review" / "CTRL-001.md")
            self.assertFalse(stale.exists())
            self.assertEqual(synced.read_text(encoding="utf-8"), canonical.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
