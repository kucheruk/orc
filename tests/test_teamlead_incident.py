#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tempfile
import threading
import time
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from orc_core.kanban_board import KanbanBoard
from orc_core.kanban_card import KanbanCard, write_card
from orc_core.kanban_init import init_kanban_board
from orc_core.teamlead_incident import (
    DECISION_FILENAME,
    FIX_CARD_PREFIX,
    Incident,
    IncidentPhase,
    TriageDecision,
    build_incident_prompt,
    fallback_decision,
    parse_incident_decision,
)


def _make_board(tmp: str) -> tuple[Path, KanbanBoard]:
    root = Path(tmp)
    tasks_dir = init_kanban_board(root)
    return tasks_dir, KanbanBoard(tasks_dir)


def _add_card(tasks_dir: Path, card: KanbanCard) -> None:
    stage_dir = tasks_dir / card.stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / f"{card.id}.md"
    card.body = card.body or "test body"
    write_card(card, path)


def _sample_incident(**overrides) -> Incident:
    defaults = dict(
        id="INC-001",
        phase=IncidentPhase.SCALE_DOWN,
        error_type="worker_crash",
        source_task_id="TASK-001",
        source_slot_id="s2",
        error_message="worker_crashed:RuntimeError",
        traceback=(
            'Traceback (most recent call last):\n'
            '  File "/project/src/app.py", line 42, in run\n'
            '    raise RuntimeError("test failure")\n'
            'RuntimeError: test failure\n'
        ),
    )
    defaults.update(overrides)
    return Incident(**defaults)


# ── parse_incident_decision ──────────────────────────────────────


class TestParseIncidentDecision(unittest.TestCase):

    def _write_decision(self, tmp: str, content: str) -> Path:
        p = Path(tmp) / DECISION_FILENAME
        p.write_text(content, encoding="utf-8")
        return p

    def test_valid_project_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, (
                "---\n"
                "classification: project\n"
                "target_role: coder\n"
                'fix_title: "Fix broken test in app.py"\n'
                "---\n\n"
                "# 1. Product Requirements\n\nFix the test.\n\n"
                "# 2. Technical Design & DoD\n\n- [ ] Fix it\n"
            ))
            d = parse_incident_decision(p)
            self.assertEqual(d.classification, "project")
            self.assertEqual(d.target_role, "coder")
            self.assertEqual(d.fix_title, "Fix broken test in app.py")
            self.assertIn("Product Requirements", d.body)

    def test_valid_orc_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, (
                "---\n"
                "classification: orc\n"
                "target_role: coder\n"
                'fix_title: "Bug in kanban_board.py"\n'
                "---\n\n"
                "ORC BUG: kanban_board.move_card\n"
            ))
            d = parse_incident_decision(p)
            self.assertEqual(d.classification, "orc")
            self.assertIn("kanban_board", d.body)

    def test_missing_frontmatter_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, "No frontmatter here")
            with self.assertRaises(ValueError):
                parse_incident_decision(p)

    def test_invalid_classification_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, (
                "---\n"
                "classification: unknown\n"
                "target_role: coder\n"
                'fix_title: "Something"\n'
                "---\n\nbody\n"
            ))
            with self.assertRaises(ValueError):
                parse_incident_decision(p)

    def test_missing_fix_title_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, (
                "---\n"
                "classification: project\n"
                "target_role: coder\n"
                "---\n\nbody\n"
            ))
            with self.assertRaises(ValueError):
                parse_incident_decision(p)

    def test_classification_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = self._write_decision(tmp, (
                "---\n"
                "classification: PROJECT\n"
                "target_role: CODER\n"
                'fix_title: "Fix it"\n'
                "---\n\nbody\n"
            ))
            d = parse_incident_decision(p)
            self.assertEqual(d.classification, "project")
            self.assertEqual(d.target_role, "coder")


# ── fallback_decision ────────────────────────────────────────────


class TestFallbackDecision(unittest.TestCase):

    def test_generates_project_decision(self):
        incident = _sample_incident()
        d = fallback_decision(incident)
        self.assertEqual(d.classification, "project")
        self.assertEqual(d.target_role, "coder")
        self.assertIn("TASK-001", d.fix_title)
        self.assertIn("Product Requirements", d.body)
        self.assertIn("RuntimeError", d.body)

    def test_truncates_long_traceback(self):
        incident = _sample_incident(traceback="x" * 3000)
        d = fallback_decision(incident)
        # Body should contain traceback but not the full 3000 chars
        self.assertIn("x" * 100, d.body)
        self.assertTrue(len(d.body) < 3000)


# ── build_incident_prompt ────────────────────────────────────────


class TestBuildIncidentPrompt(unittest.TestCase):

    def test_renders_all_variables(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="TASK-001", stage="4_Coding", action="Coding",
                title="Test task", body="test body",
            ))
            board.refresh()
            card = board.card_by_id("TASK-001")
            incident = _sample_incident()

            orc_root = Path(tmp) / ".orc"
            prompt = build_incident_prompt(
                incident, board, card,
                decision_path=str(orc_root / DECISION_FILENAME),
                orc_root=orc_root,
            )

            self.assertIn("worker_crash", prompt)
            self.assertIn("s2", prompt)  # source_slot_id
            self.assertIn("RuntimeError", prompt)
            self.assertIn("TASK-001", prompt)
            self.assertIn("incident-decision.md", prompt)
            self.assertIn("incident-traceback.txt", prompt)
            # Traceback file should be written
            tb_path = orc_root / "incident-traceback.txt"
            self.assertTrue(tb_path.exists())
            self.assertIn("RuntimeError", tb_path.read_text())

    def test_no_source_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            incident = _sample_incident(source_task_id="")

            orc_root = Path(tmp) / ".orc"
            prompt = build_incident_prompt(
                incident, board, None,
                decision_path=str(orc_root / DECISION_FILENAME),
                orc_root=orc_root,
            )
            self.assertIn("No card was being processed", prompt)


# ── Incident dataclass ───────────────────────────────────────────


class TestIncident(unittest.TestCase):

    def test_default_values(self):
        inc = _sample_incident()
        self.assertEqual(inc.error_class, "")
        self.assertEqual(inc.fix_card_id, "")
        self.assertEqual(inc.original_worker_count, 0)
        self.assertEqual(inc.removed_session_ids, [])
        self.assertGreater(inc.created_at, 0)

    def test_worktree_path(self):
        inc = _sample_incident(worktree_path="/tmp/wt/TASK-001")
        self.assertEqual(inc.worktree_path, "/tmp/wt/TASK-001")


# ── FIX_CARD_PREFIX ──────────────────────────────────────────────


class TestFixCardPrefix(unittest.TestCase):

    def test_prefix(self):
        self.assertEqual(FIX_CARD_PREFIX, "FIX-")
        self.assertTrue("FIX-TASK-001".startswith(FIX_CARD_PREFIX))


# ── KanbanBoard.create_expedite_card ─────────────────────────────


class TestCreateExpediteCard(unittest.TestCase):

    def test_creates_card_in_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            card = board.create_expedite_card(
                card_id="FIX-T1",
                title="Fix something",
                body="# 1. Product Requirements\n\nFix it\n",
                stage="4_Coding",
                action="Coding",
                cos_justification="Incident INC-001",
            )
            self.assertEqual(card.id, "FIX-T1")
            self.assertEqual(card.stage, "4_Coding")
            self.assertEqual(card.action, "Coding")
            self.assertEqual(card.class_of_service, "expedite")
            self.assertEqual(card.cos_justification, "Incident INC-001")
            self.assertEqual(card.value_score, 100)
            # Verify it's on the board
            board.refresh()
            found = board.card_by_id("FIX-T1")
            self.assertIsNotNone(found)
            self.assertEqual(found.stage, "4_Coding")

    def test_expedite_card_has_highest_priority(self):
        """Expedite cards should be picked first by pick_best."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(
                id="T-1", stage="4_Coding", action="Coding",
                class_of_service="standard", value_score=90, effort_score=10,
            ))
            board.create_expedite_card(
                card_id="FIX-T2", title="Fix", body="body",
                stage="4_Coding", action="Coding",
            )
            board.refresh()
            best = board.pick_best("4_Coding", "Coding")
            self.assertEqual(best.id, "FIX-T2")


# ── SessionSlot.crash_traceback ──────────────────────────────────


class TestSessionSlotCrashTraceback(unittest.TestCase):

    def test_default_empty(self):
        from orc_core.session_types import SessionSlot
        slot = SessionSlot(session_id="s1")
        self.assertEqual(slot.crash_traceback, "")

    def test_can_set(self):
        from orc_core.session_types import SessionSlot
        slot = SessionSlot(session_id="s1")
        slot.crash_traceback = "Traceback..."
        self.assertEqual(slot.crash_traceback, "Traceback...")


# ── KanbanPublisher.log_incident ─────────────────────────────────


class TestPublisherLogIncident(unittest.TestCase):

    def test_emits_incident_event(self):
        from orc_core.kanban_publisher import KanbanPublisher
        pub = KanbanPublisher()
        events = []
        pub.journal_callback = lambda e: events.append(e)
        pub.log_incident("INC-001", "Something happened")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].category, "incident")
        self.assertIn("INC-001", events[0].message)
        self.assertIn("Something happened", events[0].message)


if __name__ == "__main__":
    unittest.main()
