#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consistency tests for the unified state machine.

Validates that TRANSITIONS, FORWARD_MOVES, IDENTITY_DEFAULTS, and
VALID_TRANSITIONS are complete, consistent, and non-contradictory.
"""

import unittest

from orc_core.board.action_constants import Action
from orc_core.board.stage_constants import (
    STAGE_CODING,
    STAGE_DONE,
    STAGE_ESTIMATE,
    STAGE_HANDOFF,
    STAGE_INBOX,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_TODO,
)
from orc_core.board.state_machine import (
    FORWARD_MOVES,
    IDENTITY_DEFAULTS,
    LOOP_BACK_ACTIONS,
    TRANSITIONS,
    VALID_TRANSITIONS,
)


class StateMachineConsistencyTest(unittest.TestCase):

    def test_every_auto_default_has_a_valid_transition(self) -> None:
        """Every auto-default must be in the valid transitions for that role."""
        for role, defaults in IDENTITY_DEFAULTS.items():
            valid = VALID_TRANSITIONS.get(role, {})
            for from_action, to_action in defaults.items():
                valid_targets = valid.get(from_action, set())
                self.assertIn(
                    to_action,
                    valid_targets,
                    f"Auto-default {role}: {from_action}→{to_action} is not a valid transition. "
                    f"Valid: {valid_targets}",
                )

    def test_every_forward_move_has_valid_transition(self) -> None:
        """Every forward move must correspond to at least one valid transition."""
        all_to_actions = {t.to_action for t in TRANSITIONS}
        for (stage, action), target_stage in FORWARD_MOVES.items():
            self.assertIn(
                action,
                all_to_actions,
                f"Forward move ({stage}, {action})→{target_stage} uses action "
                f"'{action}' which is not a to_action in any transition.",
            )

    def test_loop_back_actions_are_subset_of_valid_transitions(self) -> None:
        """Loop-back actions must appear as to_action in some transition."""
        all_to_actions = {t.to_action for t in TRANSITIONS}
        for action in LOOP_BACK_ACTIONS:
            self.assertIn(action, all_to_actions,
                          f"Loop-back action '{action}' is not a to_action in any transition.")

    def test_no_duplicate_transitions(self) -> None:
        """No two transitions should have the same (from_stage, from_action, to_action, role)."""
        seen: set[tuple] = set()
        for t in TRANSITIONS:
            key = (t.from_stage, t.from_action, t.to_action, t.role)
            self.assertNotIn(key, seen,
                             f"Duplicate transition: {key}")
            seen.add(key)

    def test_every_delivery_role_has_auto_default(self) -> None:
        """Coder, reviewer, tester, integrator must each have at least one auto-default."""
        for role in ("coder", "reviewer", "tester", "integrator"):
            self.assertIn(role, IDENTITY_DEFAULTS,
                          f"Delivery role '{role}' has no auto-default. "
                          f"This will cause stuck cards when agent doesn't change action.")

    def test_handoff_done_transition_exists(self) -> None:
        """Handoff+Done must be a declared transition, but must NOT auto-move.

        Card stays in STAGE_HANDOFF when the integrator sets action=Done.
        The actual move to STAGE_DONE happens in finalize_completed_worktree
        after a successful squash merge — this prevents a card from reaching
        8_Done before its code lands on the main branch.
        """
        # Transition declared — integrator is allowed to set action=Done.
        integrator_transitions = VALID_TRANSITIONS.get("integrator", {})
        self.assertIn(Action.DONE, integrator_transitions.get(Action.INTEGRATING, set()),
                      "Integrator must be able to set action=Done from Integrating.")
        # But the transition MUST NOT appear in FORWARD_MOVES — otherwise
        # state machine would auto-move the card to STAGE_DONE before the
        # squash merge runs. finalize_completed_worktree owns that move.
        self.assertNotIn(
            (STAGE_HANDOFF, Action.DONE),
            FORWARD_MOVES,
            "Handoff+Done must NOT auto-move to STAGE_DONE; finalize owns that step.",
        )

    def test_reject_paths_exist_for_review_and_testing(self) -> None:
        """Reviewer and tester must be able to send cards back to Coding."""
        self.assertIn(
            (STAGE_REVIEW, Action.CODING),
            FORWARD_MOVES,
            "Missing reject path: Review + Coding → Coding",
        )
        self.assertIn(
            (STAGE_TESTING, Action.CODING),
            FORWARD_MOVES,
            "Missing reject path: Testing + Coding → Coding",
        )

    def test_full_pipeline_path_exists(self) -> None:
        """Verify forward path through state_machine up to Handoff.

        The last hop (Handoff→Done) is deliberately NOT in FORWARD_MOVES:
        the card stays in STAGE_HANDOFF when the integrator sets action=Done,
        and finalize_completed_worktree moves it to STAGE_DONE only after the
        squash merge succeeds. See test_handoff_done_transition_exists.
        """
        expected_path = [
            ((STAGE_INBOX, Action.ARCHITECT), STAGE_ESTIMATE),
            ((STAGE_CODING, Action.REVIEWING), STAGE_REVIEW),
            ((STAGE_REVIEW, Action.TESTING), STAGE_TESTING),
            ((STAGE_TESTING, Action.INTEGRATING), STAGE_HANDOFF),
        ]
        for key, expected_target in expected_path:
            self.assertEqual(
                FORWARD_MOVES.get(key),
                expected_target,
                f"Pipeline break at {key}: expected {expected_target}, "
                f"got {FORWARD_MOVES.get(key)}",
            )

    def test_architect_can_send_to_todo(self) -> None:
        """Architect must be able to move card from Estimate to Todo."""
        self.assertIn(
            (STAGE_ESTIMATE, Action.CODING),
            FORWARD_MOVES,
        )


if __name__ == "__main__":
    unittest.main()
