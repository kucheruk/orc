#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helper functions for kanban worker execution."""

from __future__ import annotations

import json
from pathlib import Path

from ...board.limits_constants import MIN_TOKEN_BUDGET, TOKENS_PER_EFFORT_POINT
from ...tasks.ports import GitIntegrationPort

DEFAULT_TOKENS_PER_EFFORT = TOKENS_PER_EFFORT_POINT
MIN_TOKEN_BUDGET = MIN_TOKEN_BUDGET


def card_state_fingerprint(card) -> tuple[str, str, str]:
    # state_version is excluded on purpose: it is bumped by every save_card
    # (token-budget sync, teamlead feedback notes, autounblock bookkeeping)
    # even when no semantic field changed. The stage/action/file_path triple
    # already captures every transition an agent's result could be stale for.
    path = str(card.file_path) if getattr(card, "file_path", None) else ""
    return (card.stage, card.action, path)


def update_card_token_budget(card, board, log_path: Path) -> None:
    expected = (
        card.effort_score * DEFAULT_TOKENS_PER_EFFORT
        if card.effort_score > 0
        else MIN_TOKEN_BUDGET
    )
    if card.token_budget == expected:
        return
    if card.token_budget > 0 and expected < card.token_budget:
        return
    previous = card.token_budget
    card.token_budget = expected
    board.save_card(card)
    from ...log import log_event
    log_event(
        log_path,
        "INFO",
        "token budget updated",
        task_id=card.id,
        previous=previous,
        budget=card.token_budget,
        effort=card.effort_score,
    )


def accumulate_card_tokens(card, board, workdir: str) -> None:
    from ...infra.io.state_paths import stats_path

    stats_file = stats_path(workdir)
    if not stats_file.exists():
        return
    try:
        stats = json.loads(stats_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    task_tokens = stats.get("tokens_by_task", {}).get(card.id, 0)
    if task_tokens and int(task_tokens) > card.tokens_spent:
        card.tokens_spent = int(task_tokens)
        board.save_card(card)


def check_and_block_budget(card, board, publisher, log_path: Path) -> bool:
    if not card.is_budget_exhausted:
        return False
    from ...log import log_event

    reason = f"token budget exhausted: {card.tokens_spent}/{card.token_budget}"
    log_event(
        log_path,
        "WARN",
        "card blocked: token budget exhausted",
        task_id=card.id,
        tokens_spent=card.tokens_spent,
        token_budget=card.token_budget,
    )
    publisher.emit("escalate", card.id, f"{card.id} BLOCKED: {reason}")
    card.block(reason)
    board.save_card(card)
    return True


def verify_and_commit_uncommitted(
    workdir: str,
    main_branch: str,
    log_path: Path,
    task_id: str,
    task_text: str,
    *,
    git: GitIntegrationPort,
) -> None:
    ok, porcelain, _, _ = git.run_with_log(
        workdir,
        log_path,
        ["git", "status", "--porcelain"],
        label="verify:uncommitted_check",
    )
    if not ok or not porcelain:
        return
    tracked, untracked = git.parse_porcelain(porcelain)
    code_dirty = [
        path for path in tracked + untracked
        if not path.startswith("tasks/")
        and not path.startswith(".orc/")
        and not path.startswith(".cursor/")
        and "__pycache__" not in path
    ]
    if code_dirty:
        git.attempt_autocommit_fallback(workdir, log_path, task_id, task_text)


def gather_git_context(
    workdir: str,
    main_branch: str,
    log_path: Path,
    *,
    git: GitIntegrationPort,
) -> str:
    parts: list[str] = []
    ok_log, log_out, _, _ = git.run_with_log(
        workdir,
        log_path,
        ["git", "log", "--oneline", f"{main_branch}..HEAD", "--", ".", ":!tasks/"],
        label="git_context:log",
    )
    if ok_log and log_out.strip():
        parts.append(f"### Commits on this branch (vs {main_branch})\n```\n{log_out.strip()}\n```")

    ok_stat, stat_out, _, _ = git.run_with_log(
        workdir,
        log_path,
        ["git", "diff", "--stat", main_branch, "--", ".", ":!tasks/"],
        label="git_context:diff_stat",
    )
    if ok_stat and stat_out.strip():
        parts.append(f"### Changed files (vs {main_branch})\n```\n{stat_out.strip()}\n```")

    ok_status, status_out, _, _ = git.run_with_log(
        workdir,
        log_path,
        ["git", "status", "--short"],
        label="git_context:status",
    )
    if ok_status and status_out.strip():
        non_task = [line for line in status_out.strip().splitlines() if "tasks/" not in line]
        if non_task:
            parts.append(f"### Uncommitted changes\n```\n" + "\n".join(non_task) + "\n```")

    if not parts:
        return ""
    return "## Branch State (pre-gathered by orchestrator)\n\n" + "\n\n".join(parts)
