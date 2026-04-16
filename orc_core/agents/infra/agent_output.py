#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse agent output card, validate transitions, apply changes to the board."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ...board.kanban_card import PROTECTED_FIELDS, KanbanCard, validate_card
from ...board.kanban_role_registry import ROLE_ARCHITECT, ROLE_CODER, ROLE_INTEGRATOR, ROLE_REVIEWER, ROLE_TESTER
from ...board.action_constants import Action
from ...board.stage_constants import STAGE_CODING, STAGE_DONE, STAGE_ESTIMATE, STAGE_HANDOFF, STAGE_INBOX, STAGE_ORDER, STAGE_REVIEW, STAGE_TESTING, STAGE_TODO
from ...board.state_machine import FORWARD_MOVES, IDENTITY_DEFAULTS, LOOP_BACK_ACTIONS, VALID_TRANSITIONS

if TYPE_CHECKING:
    from ...board.kanban_board import KanbanBoard

_logger = logging.getLogger(__name__)

# Fields that specific roles must NOT modify (role-based restrictions).
# These are not globally protected but belong to another role's responsibility.
_ROLE_READONLY_FIELDS: dict[str, frozenset[str]] = {
    ROLE_ARCHITECT: frozenset({"value_score", "class_of_service", "cos_justification", "deadline"}),
    ROLE_CODER: frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    ROLE_REVIEWER: frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    ROLE_TESTER: frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
    ROLE_INTEGRATOR: frozenset({"value_score", "effort_score", "class_of_service", "cos_justification", "deadline"}),
}

# Derived from state_machine.py — single source of truth
_VALID_TRANSITIONS = VALID_TRANSITIONS
_LOOP_BACK_ACTIONS = LOOP_BACK_ACTIONS
_FORWARD_MOVES = FORWARD_MOVES


def _is_branch_integrated(base_workdir: str, card_id: str, main_branch: str) -> bool:
    """Check if task branch orc/{id} code is fully merged into main.

    Uses merge-base comparison: finds files the branch changed relative to
    the fork point, then checks if main has identical content for those files.
    Three-dot diff (main...branch) does NOT work here because squash-merge
    doesn't make the branch an ancestor of main.
    """
    from ...git.worktree_flow import run_git, task_branch_name
    branch_name = task_branch_name(card_id)
    # Check if branch exists; if not, it was never created (non-code card) → OK
    ok, _, _, _ = run_git(base_workdir, ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"])
    if not ok:
        _logger.info("Integration check: no branch %s for %s — treating as integrated (non-code card)",
                      branch_name, card_id)
        return True

    # Step 1: find merge-base
    ok_mb, mb_out, _, _ = run_git(
        base_workdir, ["git", "merge-base", main_branch, branch_name],
    )
    if not ok_mb:
        _logger.warning("Integration check: merge-base failed for %s — assuming not integrated", card_id)
        return False
    merge_base = mb_out.strip()

    # Step 2: find code files changed on the branch since fork point
    ok_files, files_out, _, _ = run_git(
        base_workdir,
        ["git", "diff", "--name-only", merge_base, branch_name, "--", ".", ":!tasks/"],
    )
    if not ok_files:
        _logger.warning("Integration check: diff vs merge-base failed for %s", card_id)
        return False
    branch_files = [f.strip() for f in files_out.splitlines() if f.strip()]
    if not branch_files:
        _logger.info("Integration check: %s branch %s has no code changes — treating as integrated",
                      card_id, branch_name)
        return True

    # Step 3: check if main has identical content for those files
    diff_cmd = ["git", "diff", branch_name, main_branch, "--"] + branch_files
    ok_diff, diff_out, _, _ = run_git(base_workdir, diff_cmd)
    if not ok_diff:
        _logger.warning("Integration check: content diff failed for %s", card_id)
        return False

    if diff_out.strip():
        _logger.info("Integration check: %s has %d files not yet on %s: %s",
                      card_id, len(branch_files), main_branch, branch_files[:5])
        return False

    _logger.info("Integration check: %s branch %s code verified identical on %s",
                  card_id, branch_name, main_branch)
    return True


def process_agent_result(
    board: "KanbanBoard",
    card: KanbanCard,
    role: str,
    *,
    execution_workdir: str = "",
    main_branch: str = "",
) -> list[str]:
    """Re-read card from disk (agent modified it), validate and apply transitions.

    When execution_workdir is set (agent ran in a worktree), reads the card
    from the worktree first — the agent edits its local copy, not the main
    repo. Falls back to main repo if worktree copy is missing.

    Returns list of validation errors (empty = success).
    """
    with board.locked_card(card.id):
        file_path = card.file_path

        # Prefer worktree copy — agent edits relative to its CWD
        worktree_card_path = None
        if execution_workdir:
            # Card may be in any stage dir in the worktree (worktree branch
            # was created when card was in an earlier stage)
            wt_tasks = Path(execution_workdir) / "tasks"
            card_filename = f"{card.id}.md"
            for stage_dir in sorted(wt_tasks.iterdir()) if wt_tasks.exists() else []:
                candidate = stage_dir / card_filename
                if candidate.is_file():
                    worktree_card_path = candidate
                    break

        if worktree_card_path is None:
            if file_path is None or not file_path.exists():
                found = board.find_card_file(card.id)
                if found is None:
                    return [f"Card file not found (checked all stages): {card.id}"]
                _logger.info("Card %s moved during execution: %s → %s", card.id, file_path, found)
                file_path = found
                card.file_path = found
        else:
            file_path = worktree_card_path
            _logger.info("Reading card %s from worktree: %s", card.id, worktree_card_path)

        try:
            updated = board.repo.read_card(file_path)
        except Exception as exc:
            _logger.error("Failed to parse agent output card %s from %s: %s", card.id, file_path, exc)
            # Revert card file to original content so board doesn't read corrupt data
            try:
                board.repo.write_card_text(card.file_path, card.to_markdown())
            except Exception:
                pass
            return [f"Failed to parse card file after agent edit: {exc}"]

        errors = _validate_agent_changes(card, updated, role)
        if errors:
            _logger.warning("Agent output validation errors for %s: %s", card.id, errors)
            # Revert card file to original content
            try:
                board.repo.write_card_text(card.file_path, card.to_markdown())
            except Exception:
                pass
            return errors

        card_errors = validate_card(updated)
        if card_errors:
            # Log but don't block — validation errors on fields the agent can't
            # change (e.g. cos_justification set by product) should not prevent
            # coder/reviewer/tester from progressing.
            _logger.warning("Card validation warnings for %s (non-blocking): %s", card.id, card_errors)

        # Auto-default: if the agent didn't change the action, apply the most
        # common "done" transition for that role so work keeps flowing.
        if updated.action == card.action:
            defaults = IDENTITY_DEFAULTS.get(role, {})
            default_next = defaults.get(card.action)
            if default_next:
                _logger.info(
                    "Agent %s left action unchanged (%s); auto-defaulting to %s for %s",
                    role, card.action, default_next, card.id,
                )
                updated.action = default_next

        # Apply valid changes
        new_action = updated.action
        old_action = card.action

        # Detect loop-back (reviewer/tester sending back to coder)
        if new_action in _LOOP_BACK_ACTIONS and old_action != Action.CODING:
            updated.loop_count = card.loop_count + 1

        # Restore protected fields from original.
        # file_path MUST point to main repo (not worktree) so save_card
        # writes to the canonical location.  The worktree copy was only
        # used to READ the agent's changes.
        updated.stage = card.stage
        updated.file_path = card.file_path
        updated.roi = card.roi
        updated.assigned_agent = card.assigned_agent
        updated.created_at = card.created_at
        updated.tokens_spent = card.tokens_spent
        updated.token_budget = card.token_budget

        # Recompute ROI in case value/effort changed
        updated.refresh_roi()
        updated.touch()
        board.save_card(updated, old_action=old_action, role=role)

        # Move card if this transition requires a stage change
        move_key = (card.stage, new_action)
        new_stage = _FORWARD_MOVES.get(move_key)
        # Block promotion to Todo/Coding if dependencies are unmet
        if new_stage in (STAGE_TODO, STAGE_CODING) and board.has_unmet_dependencies(updated):
            _logger.info("Cannot move %s to %s: unmet dependencies, staying in %s",
                          updated.id, new_stage, card.stage)
        # Integration gate: Done only after code is verified on main.
        # Integrator role is EXEMPT — its job is to trigger the merge, which
        # happens AFTER process_agent_result in finalize_completed_worktree.
        elif new_stage == STAGE_DONE:
            if role == ROLE_INTEGRATOR:
                _logger.info(
                    "Integration gate: %s — integrator role exempt, moving to Done "
                    "(merge will run in finalize).",
                    updated.id,
                )
                board.move_card(updated, new_stage, allow_backward=False,
                                reason=f"{role}: {old_action} -> {new_action}")
                if updated.action != Action.DONE:
                    updated.action = Action.DONE
                    board.save_card(updated)
            else:
                base_workdir = str(board.tasks_dir.parent) if board.tasks_dir else ""
                gate_branch = main_branch
                if not gate_branch:
                    from ...git.worktree_flow import detect_base_branch
                    gate_branch = detect_base_branch(base_workdir) if base_workdir else "main"
                    _logger.info("Integration gate: main_branch not passed, detected '%s'", gate_branch)
                if not _is_branch_integrated(base_workdir, updated.id, gate_branch):
                    _logger.warning(
                        "Integration gate: blocking %s from Done — code not yet on %s. "
                        "Keeping in %s with action=Integrating. (role=%s)",
                        updated.id, gate_branch, card.stage, role,
                    )
                    updated.action = Action.INTEGRATING
                    board.save_card(updated)
                else:
                    _logger.info(
                        "Integration gate: %s passed — branch code verified on %s, "
                        "moving to Done. (role=%s)",
                        updated.id, gate_branch, role,
                    )
                    board.move_card(updated, new_stage, allow_backward=False,
                                    reason=f"{role}: {old_action} -> {new_action}")
                    if updated.action != Action.DONE:
                        updated.action = Action.DONE
                        board.save_card(updated)
        elif new_stage and board.has_wip_room(new_stage):
            is_backward = STAGE_ORDER.get(new_stage, 0) < STAGE_ORDER.get(card.stage, 0)
            board.move_card(updated, new_stage, allow_backward=is_backward,
                            reason=f"{role}: {old_action} -> {new_action}")
        elif new_stage and not board.has_wip_room(new_stage):
            _logger.info("Cannot move %s to %s: WIP limit reached, will retry later", card.id, new_stage)

        # Sync the original card object and refresh board state
        _sync_card(card, updated)
        board.refresh()
        return []


def _validate_agent_changes(
    original: KanbanCard,
    updated: KanbanCard,
    role: str,
) -> list[str]:
    errors: list[str] = []

    # Check protected fields
    if updated.id != original.id:
        errors.append(f"Agent changed id from {original.id} to {updated.id}")

    # Check role-based readonly fields — revert silently (same as protected fields)
    readonly = _ROLE_READONLY_FIELDS.get(role, frozenset())
    for field in readonly:
        orig_val = getattr(original, field)
        new_val = getattr(updated, field)
        if new_val != orig_val:
            _logger.info("Agent %s changed readonly field %s for %s (reverting)", role, field, original.id)
            setattr(updated, field, orig_val)

    # Validate action transition (identity = agent didn't change action, allowed)
    if updated.action != original.action:
        role_transitions = _VALID_TRANSITIONS.get(role, {})
        valid_actions = role_transitions.get(original.action, set())
        if valid_actions and updated.action not in valid_actions:
            errors.append(
                f"Invalid transition for {role}: {original.action} → {updated.action}. "
                f"Valid: {valid_actions}"
            )

    # Stage must not be changed by agent
    if updated.stage != original.stage:
        _logger.info("Agent changed stage for %s (will be overridden)", original.id)

    return errors


def _sync_card(target: KanbanCard, source: KanbanCard) -> None:
    for field in (
        "title", "action", "class_of_service", "cos_justification",
        "deadline", "value_score", "effort_score", "roi",
        "dependencies", "loop_count", "assigned_agent",
        "created_at", "updated_at", "body", "stage", "file_path",
        "tokens_spent", "token_budget",
    ):
        setattr(target, field, getattr(source, field))
