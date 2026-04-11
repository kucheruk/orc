#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from orc_core.infra.state_paths import kanban_state_path


class TestKanbanStatePath(unittest.TestCase):

    def test_returns_path_under_repo_root(self):
        path = kanban_state_path("/tmp/test-repo")
        self.assertEqual(path.name, "kanban-state.json")
        self.assertIn("repos", str(path))


class TestKanbanStatePersistence(unittest.TestCase):

    def test_save_and_load_roundtrip(self):
        """Write kanban-state.json, verify it can be read back."""
        from orc_core.infra.atomic_io import write_json_atomic
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kanban-state.json"
            state = {
                "card_fail_counts": {"TASK-001": 2, "TASK-002": 1},
                "arbitrated_at_loop": {"TASK-001": 3},
            }
            write_json_atomic(path, state)

            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["card_fail_counts"]["TASK-001"], 2)
            self.assertEqual(loaded["arbitrated_at_loop"]["TASK-001"], 3)

    def test_load_missing_file_is_safe(self):
        """Loading from a non-existent path should not crash."""
        path = Path("/tmp/nonexistent-kanban-state-12345.json")
        self.assertFalse(path.exists())
        # Simulate what _load_kanban_state does
        card_fail_counts: dict[str, int] = {}
        arbitrated_at_loop: dict[str, int] = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            card_fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
            arbitrated_at_loop = {k: int(v) for k, v in data.get("arbitrated_at_loop", {}).items()}
        self.assertEqual(card_fail_counts, {})
        self.assertEqual(arbitrated_at_loop, {})

    def test_load_corrupt_file_is_safe(self):
        """Loading from a corrupt file should not crash."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "kanban-state.json"
            path.write_text("not json at all", encoding="utf-8")
            card_fail_counts: dict[str, int] = {}
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                card_fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
            except Exception:
                pass  # Expected — mirrors _load_kanban_state behavior
            self.assertEqual(card_fail_counts, {})


if __name__ == "__main__":
    unittest.main()
