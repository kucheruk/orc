#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path

from orc_core.agents.results.io import build_result_run_id
from orc_core.agents.results.worker_result_processor import process_worker_card_result
from orc_core.board.fs_card_repository import FsCardRepository
from orc_core.board.kanban_board import KanbanBoard
from orc_core.board.kanban_card import KanbanCard
from orc_core.board.kanban_init import init_kanban_board
from orc_core.tasks.completion.outcomes import TaskOutcomeTracker

write_card = FsCardRepository().write_card


def _make_board(tmp: str) -> tuple[Path, KanbanBoard]:
    tasks_dir = init_kanban_board(Path(tmp))
    return tasks_dir, KanbanBoard(tasks_dir, repo=FsCardRepository())


def _add_card(tasks_dir: Path, card: KanbanCard) -> None:
    path = tasks_dir / card.stage / f"{card.id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    card.body = card.body or (
        "# 1. Product Requirements\n\n"
        "# 2. Technical Design & DoD\n\n"
        "# 3. Implementation Notes\n\n"
        "# 4. Feedback & Checklist\n"
    )
    write_card(card, path)


def _write_result(root: Path, payload: dict) -> tuple[str, str]:
    run_id = payload["run_id"]
    path = root / "result.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path), run_id


class WorkerCardResultProcessingTest(unittest.TestCase):
    def test_product_result_updates_card_and_moves_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="P-1", stage="1_Inbox", action="Product"))
            board.refresh(force=True)
            card = board.card_by_id("P-1")
            result_file, run_id = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "product",
                "run_id": build_result_run_id(task_id="P-1", stage_id="1_Inbox", attempt=1),
                "summary": "prioritized",
                "payload": {
                    "task_id": "P-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "Architect",
                    "field_updates": {"value_score": 80},
                    "section_updates": {"product_requirements": "Ship the feature."},
                    "feedback_append": "",
                },
            })
            tracker = TaskOutcomeTracker()

            errors = process_worker_card_result(
                board, card, "product",
                agent_result_file=result_file,
                agent_run_id=run_id,
                outcomes=tracker,
            )

            self.assertEqual(errors, [])
            updated = board.card_by_id("P-1")
            self.assertEqual(updated.stage, "2_Estimate")
            self.assertEqual(updated.value_score, 80)
            self.assertIn("Ship the feature.", updated.body)

    def test_reviewer_loopback_appends_feedback_and_increments_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="R-1", stage="5_Review", action="Reviewing"))
            board.refresh(force=True)
            card = board.card_by_id("R-1")
            result_file, run_id = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "reviewer",
                "run_id": build_result_run_id(task_id="R-1", stage_id="5_Review", attempt=1),
                "summary": "needs fixes",
                "payload": {
                    "task_id": "R-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "Coding",
                    "field_updates": {},
                    "section_updates": {},
                    "feedback_append": "- [ ] [BLOCKER] Fix the failing path",
                },
            })

            errors = process_worker_card_result(
                board, card, "reviewer",
                agent_result_file=result_file,
                agent_run_id=run_id,
                outcomes=TaskOutcomeTracker(),
            )

            self.assertEqual(errors, [])
            updated = board.card_by_id("R-1")
            self.assertEqual(updated.stage, "4_Coding")
            self.assertEqual(updated.loop_count, 1)
            self.assertIn("[BLOCKER]", updated.body)

    def test_integrator_done_stays_in_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="I-1", stage="7_Handoff", action="Integrating"))
            board.refresh(force=True)
            card = board.card_by_id("I-1")
            result_file, run_id = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "integrator",
                "run_id": build_result_run_id(task_id="I-1", stage_id="7_Handoff", attempt=1),
                "summary": "delivered",
                "payload": {
                    "task_id": "I-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "Done",
                    "field_updates": {},
                    "section_updates": {"implementation_notes": "Delivery review"},
                    "feedback_append": "- [x] Integration complete",
                },
            })

            errors = process_worker_card_result(
                board, card, "integrator",
                agent_result_file=result_file,
                agent_run_id=run_id,
                outcomes=TaskOutcomeTracker(),
            )

            self.assertEqual(errors, [])
            updated = board.card_by_id("I-1")
            self.assertEqual(updated.stage, "7_Handoff")
            self.assertEqual(updated.action, "Done")

    def test_falls_back_to_prior_attempt_when_current_missing(self):
        """cursor-agent in --resume mode keeps writing to attempt-1; ORC must
        still pick it up after incrementing the attempt counter."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="W-1", stage="4_Coding", action="Coding"))
            board.refresh(force=True)
            card = board.card_by_id("W-1")
            results_dir = Path(tmp) / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            # Agent wrote attempt-1 on first session; ORC now expects attempt-3.
            attempt_1 = results_dir / "W-1__4_Coding__attempt-1.json"
            attempt_1.write_text(json.dumps({
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "coder",
                "run_id": build_result_run_id(task_id="W-1", stage_id="4_Coding", attempt=1),
                "summary": "done",
                "payload": {
                    "task_id": "W-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "Reviewing",
                    "section_updates": {"implementation_notes": "attempt-1 wrote this"},
                },
            }), encoding="utf-8")

            expected_missing = results_dir / "W-1__4_Coding__attempt-3.json"
            errors = process_worker_card_result(
                board, card, "coder",
                agent_result_file=str(expected_missing),
                agent_run_id=build_result_run_id(task_id="W-1", stage_id="4_Coding", attempt=3),
                outcomes=TaskOutcomeTracker(),
            )

            self.assertEqual(errors, [])
            updated = board.card_by_id("W-1")
            self.assertEqual(updated.stage, "5_Review")
            self.assertIn("attempt-1 wrote this", updated.body)

    def test_missing_result_file_synthesizes_and_advances(self):
        """When the agent committed work but skipped writing the result
        metadata JSON (cursor-agent's gpt-5.3-codex sometimes does this
        after a successful commit), ORC must synthesize a default
        card_update from its own view of the card and advance the stage
        instead of discarding ~40k tokens of real delivery.

        The caller already verified non-empty delivery via
        verify_and_commit_uncommitted + _reject_empty_delivery before
        reaching this point, so a missing file here is purely a metadata
        gap, not a work-outcome gap.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="X-1", stage="4_Coding", action="Coding"))
            board.refresh(force=True)
            card = board.card_by_id("X-1")
            tracker = TaskOutcomeTracker()

            errors = process_worker_card_result(
                board, card, "coder",
                agent_result_file=str(Path(tmp) / "missing.json"),
                agent_run_id="X-1:4_Coding:attempt-1",
                outcomes=tracker,
            )
            self.assertEqual(errors, [],
                             f"synthesis fallback must not error; got {errors!r}")
            board.refresh(force=True)
            advanced = board.card_by_id("X-1")
            self.assertEqual(advanced.stage, "5_Review",
                             "coder finishing 4_Coding with synthesized "
                             "result should land in 5_Review")
            self.assertTrue(tracker.has_applied_result("X-1:4_Coding:attempt-1"),
                            "synthesized result must be recorded so repeat "
                            "attempts are idempotent")

    def test_malformed_result_content_also_synthesizes(self):
        """Agents writing the result via a heredoc sometimes embed a
        control character (backtick, newline, tab) inside
        implementation_notes that breaks the JSON. The delivery itself
        is already committed on disk by the time we reach this check, so
        discarding 30–40k tokens for a metadata-escape bug is the wrong
        trade-off. Treat malformed-but-exists the same as missing:
        synthesize and advance."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="X-2", stage="4_Coding", action="Coding"))
            board.refresh(force=True)
            card = board.card_by_id("X-2")
            tracker = TaskOutcomeTracker()

            bad_file = Path(tmp) / "bad.json"
            bad_file.write_text("{not-json", encoding="utf-8")
            errors = process_worker_card_result(
                board, card, "coder",
                agent_result_file=str(bad_file),
                agent_run_id="X-2:4_Coding:attempt-1",
                outcomes=tracker,
            )
            self.assertEqual(errors, [],
                             f"malformed-JSON fallback must not error; got {errors!r}")
            board.refresh(force=True)
            advanced = board.card_by_id("X-2")
            self.assertEqual(advanced.stage, "5_Review",
                             "coder finishing 4_Coding should still land in "
                             "5_Review even if the JSON is malformed")


if __name__ == "__main__":
    unittest.main()
