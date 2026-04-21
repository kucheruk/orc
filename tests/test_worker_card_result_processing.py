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
            recorded = [rid for rid in tracker.state_snapshot()["applied_result_runs"]
                        if rid.startswith("X-1:4_Coding:attempt-1")]
            self.assertEqual(len(recorded), 1,
                             "synthesized result must be recorded so repeat "
                             "attempts within the same entry are idempotent; "
                             f"got {recorded!r}")
            self.assertIn(":fp-sv", recorded[0],
                          "dedup key must carry a state_version suffix from "
                          "launch_fingerprint so repeat entries into the "
                          "same stage are not shadowed by idempotence")

    def test_reentry_to_same_stage_advances_under_synthesis(self):
        """A card that re-enters 6_Testing after a tester->coder loopback
        gets a fresh tester attempt. cursor-agent's gpt-5.3-codex still
        omits the result file; ORC's synthesis fallback must advance the
        card even though `TASK:6_Testing:attempt-1` was already applied
        on the original entry. Without the state_version-derived nonce on
        the synthesized run_id the idempotence guard no-ops the advance
        and the card sits at 6_Testing/Testing forever, burning one full
        tester invocation per tick (observed 2026-04-20 on jeeves for
        ASSIST-002-C, ASSIST-003-C, NOTIF-003-B)."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="X-R", stage="6_Testing", action="Testing"))
            board.refresh(force=True)
            card = board.card_by_id("X-R")
            tracker = TaskOutcomeTracker()

            # First entry — tester synthesises, card advances to Handoff.
            errors = process_worker_card_result(
                board, card, "tester",
                agent_result_file=str(Path(tmp) / "missing-1.json"),
                agent_run_id="X-R:6_Testing:attempt-1",
                outcomes=tracker,
            )
            self.assertEqual(errors, [])
            board.refresh(force=True)
            self.assertEqual(board.card_by_id("X-R").stage, "7_Handoff")

            # Simulate full round-trip: integrator loops back to reviewer,
            # reviewer loops back to coder, coder loops back to tester,
            # card re-enters 6_Testing/Testing with bumped state_version.
            re_card = board.card_by_id("X-R")
            re_card.stage = "6_Testing"
            re_card.action = "Testing"
            board.save_card(re_card)
            board.refresh(force=True)
            re_card = board.card_by_id("X-R")

            # Second entry, same "attempt-1" run_id because restart_count
            # resets to 0 on each fresh stage session.
            errors = process_worker_card_result(
                board, re_card, "tester",
                agent_result_file=str(Path(tmp) / "missing-2.json"),
                agent_run_id="X-R:6_Testing:attempt-1",
                outcomes=tracker,
            )
            self.assertEqual(errors, [],
                             f"re-entry synthesis must not error; got {errors!r}")
            board.refresh(force=True)
            re_advanced = board.card_by_id("X-R")
            self.assertEqual(re_advanced.stage, "7_Handoff",
                             "re-entry with synthesis must advance again — "
                             "otherwise the card is pinned at Testing and "
                             "every tick burns a full tester invocation")

    def test_apply_preserves_orig_reference_across_refresh(self):
        """Regression for the apply→refresh→stale-save chain that wiped
        tester-to-coder transitions on jeeves. worker_assignment captures
        `card` at assignment time and keeps calling save_card on that same
        reference after apply_card_update_result returns. If refresh
        replaces the in-memory card instance, the captured reference turns
        into an orphan frozen at the pre-apply (stage, action, file_path),
        and the subsequent accumulate_card_tokens save writes that stale
        state back onto disk — recreating the old stage directory's copy
        with a newer updated_at, which then wins _dedup_cards and deletes
        the post-apply copy. This test exercises exactly that sequence:
        the orig `card` reference must reflect the post-apply stage, so
        any save on it targets the correct file_path."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="O-1", stage="6_Testing", action="Testing"))
            board.refresh(force=True)
            orig_card = board.card_by_id("O-1")  # captured like worker_assignment does

            result_file, run_id = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "tester",
                "run_id": build_result_run_id(task_id="O-1", stage_id="6_Testing", attempt=1),
                "summary": "bounce",
                "payload": {
                    "task_id": "O-1",
                    "launch_fingerprint": {
                        "stage": orig_card.stage,
                        "action": orig_card.action,
                        "file_path": str(orig_card.file_path),
                        "state_version": orig_card.state_version,
                    },
                    "next_action": "Coding",
                    "field_updates": {},
                    "section_updates": {},
                    "feedback_append": "- [ ] feedback",
                },
            })

            errors = process_worker_card_result(
                board, orig_card, "tester",
                agent_result_file=result_file, agent_run_id=run_id,
                outcomes=TaskOutcomeTracker(),
            )
            self.assertEqual(errors, [])

            # orig_card must reflect the post-apply state — this is what
            # worker_assignment sees when it calls save_card on it from
            # _sync_tokens_and_budget.
            self.assertEqual(orig_card.stage, "4_Coding",
                             "orig reference must see the post-apply stage")
            self.assertEqual(orig_card.action, "Coding")
            self.assertEqual(orig_card.file_path,
                             tasks_dir / "4_Coding" / "O-1.md",
                             "orig reference's file_path must track the move")

            # Simulating the post-apply save that used to wipe the move:
            # accumulate_card_tokens bumps tokens_spent and calls save_card.
            # With the in-place refresh this writes to the NEW path.
            orig_card.tokens_spent = 12345
            board.save_card(orig_card)
            self.assertTrue((tasks_dir / "4_Coding" / "O-1.md").exists(),
                            "save on orig reference must target 4_Coding, "
                            "not recreate the stale 6_Testing copy")
            self.assertFalse((tasks_dir / "6_Testing" / "O-1.md").exists(),
                             "the stale 6_Testing path must stay empty — "
                             "recreating it would trigger _dedup_cards on "
                             "the next refresh and wipe the post-apply copy")

    def test_unsubstituted_env_run_id_is_normalized(self):
        """Agents sometimes ship the literal "$ORC_AGENT_RUN_ID" when the
        heredoc terminator was quoted or they wrote the file through a
        tool that bypasses the shell. Before the fix this dropped the
        entire delivery (seen on NOTIF-002-C-C 2026-04-20, NOTIF-003-C
        2026-04-21), burning 30–40k tokens per occurrence. ORC knows the
        real run_id, so the delivery is accepted and normalized."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="U-1", stage="5_Review", action="Reviewing"))
            board.refresh(force=True)
            card = board.card_by_id("U-1")
            real_run_id = build_result_run_id(
                task_id="U-1", stage_id="5_Review", attempt=1,
            )
            result_file, _ = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "reviewer",
                "run_id": "$ORC_AGENT_RUN_ID",  # unsubstituted literal
                "summary": "approved",
                "payload": {
                    "task_id": "U-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "",
                    "field_updates": {},
                    "section_updates": {},
                    "feedback_append": "",
                },
            })
            tracker = TaskOutcomeTracker()

            errors = process_worker_card_result(
                board, card, "reviewer",
                agent_result_file=result_file,
                agent_run_id=real_run_id,
                outcomes=tracker,
            )

            self.assertEqual(errors, [],
                             f"unsubstituted run_id must not discard the "
                             f"delivery; got {errors!r}")
            board.refresh(force=True)
            advanced = board.card_by_id("U-1")
            self.assertEqual(advanced.stage, "6_Testing",
                             "reviewer approving in 5_Review should advance to "
                             "6_Testing even when the run_id field was not "
                             "substituted by the agent's shell")
            recorded = tracker.state_snapshot()["applied_result_runs"]
            self.assertTrue(any(r.startswith(real_run_id) for r in recorded),
                            "dedup must be recorded under the normalized "
                            f"run_id, not the literal; got {recorded!r}")

    def test_braced_env_run_id_also_normalized(self):
        """"${ORC_AGENT_RUN_ID}" is the other broken-heredoc form. Same
        fix path: accept and normalize to ORC's real run_id."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="U-2", stage="5_Review", action="Reviewing"))
            board.refresh(force=True)
            card = board.card_by_id("U-2")
            real_run_id = build_result_run_id(
                task_id="U-2", stage_id="5_Review", attempt=2,
            )
            result_file, _ = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "reviewer",
                "run_id": "${ORC_AGENT_RUN_ID}",
                "summary": "approved",
                "payload": {
                    "task_id": "U-2",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "",
                    "field_updates": {},
                    "section_updates": {},
                    "feedback_append": "",
                },
            })

            errors = process_worker_card_result(
                board, card, "reviewer",
                agent_result_file=result_file,
                agent_run_id=real_run_id,
                outcomes=TaskOutcomeTracker(),
            )
            self.assertEqual(errors, [])
            board.refresh(force=True)
            self.assertEqual(board.card_by_id("U-2").stage, "6_Testing")

    def test_genuine_run_id_mismatch_still_rejected(self):
        """The unsubstituted-literal accommodation must NOT leak into
        genuine mismatches where the agent wrote a result for a different
        task or stage — that's a real wiring bug, not a heredoc mistake."""
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="M-1", stage="5_Review", action="Reviewing"))
            board.refresh(force=True)
            card = board.card_by_id("M-1")
            result_file, _ = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "reviewer",
                "run_id": "OTHER-TASK:5_Review:attempt-1",
                "summary": "wrong card",
                "payload": {
                    "task_id": "M-1",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "",
                    "field_updates": {},
                    "section_updates": {},
                    "feedback_append": "",
                },
            })
            errors = process_worker_card_result(
                board, card, "reviewer",
                agent_result_file=result_file,
                agent_run_id=build_result_run_id(
                    task_id="M-1", stage_id="5_Review", attempt=1,
                ),
                outcomes=TaskOutcomeTracker(),
            )
            self.assertTrue(any("does not match task/stage" in e for e in errors),
                            f"genuine mismatch must still be rejected; got {errors!r}")

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

    def test_agent_cannot_block_card_with_unmet_dependencies(self):
        """Deps-gated cards are system-gated, not human-gated. An agent
        returning next_action=Blocked on a card with unmet deps would
        manufacture a false escalation (jeeves 2026-04-20: NOTIF-004-B
        and QA-003-A both sat in Blocked/Inbox/Estimate with no human-
        actionable issue, only a system waiting on upstream cards).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tasks_dir, board = _make_board(tmp)
            _add_card(tasks_dir, KanbanCard(id="DEP-UPSTREAM", stage="3_Todo", action="Coding"))
            _add_card(tasks_dir, KanbanCard(
                id="DEPS-GATED", stage="1_Inbox", action="Product",
                dependencies=["DEP-UPSTREAM"],
            ))
            board.refresh(force=True)
            card = board.card_by_id("DEPS-GATED")
            result_file, run_id = _write_result(Path(tmp), {
                "schema_version": 1,
                "payload_kind": "card_update",
                "role": "product",
                "run_id": build_result_run_id(task_id="DEPS-GATED", stage_id="1_Inbox", attempt=1),
                "summary": "trying to block",
                "payload": {
                    "task_id": "DEPS-GATED",
                    "launch_fingerprint": {
                        "stage": card.stage,
                        "action": card.action,
                        "file_path": str(card.file_path),
                        "state_version": card.state_version,
                    },
                    "next_action": "Blocked",
                    "field_updates": {},
                    "section_updates": {},
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

            # Expect the update to be rejected with a deps-gated error
            # and the card's action to remain untouched.
            self.assertTrue(errors, "deps-gated Blocked transition must raise an error")
            self.assertTrue(any("unmet dependencies" in e for e in errors), f"expected deps-gated rejection, got: {errors!r}")
            board.refresh(force=True)
            unchanged = board.card_by_id("DEPS-GATED")
            self.assertEqual(unchanged.action, "Product",
                             "card with unmet deps must not be flipped to Blocked by an agent")

if __name__ == "__main__":
    unittest.main()
