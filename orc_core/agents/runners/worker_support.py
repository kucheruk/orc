#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helper functions for kanban worker execution."""

from __future__ import annotations

import json
from pathlib import Path

from ...board.limits_constants import TOKENS_PER_EFFORT_POINT
from ...tasks.ports import GitIntegrationPort

DEFAULT_TOKENS_PER_EFFORT = TOKENS_PER_EFFORT_POINT


def card_state_fingerprint(card) -> tuple[str, str, str]:
    # state_version is excluded on purpose: it is bumped by every save_card
    # (token-budget sync, teamlead feedback notes, autounblock bookkeeping)
    # even when no semantic field changed. The stage/action/file_path triple
    # already captures every transition an agent's result could be stale for.
    path = str(card.file_path) if getattr(card, "file_path", None) else ""
    return (card.stage, card.action, path)


def update_card_token_budget(card, board, log_path: Path) -> None:
    # An unestimated card (effort_score <= 0) has no sizing signal, so any
    # floor-based token budget is a guess that cuts real work off. Keep
    # its budget at 0 (== no cap) until the architect assigns a real
    # effort_score; at that point the enforced budget kicks in. The old
    # MIN_TOKEN_BUDGET=40000 floor routinely cut off coders mid-attempt
    # on zero-effort cards and parked them in Blocked even though the
    # attempt had produced a live commit (see AUDIT-001-C burn: 184548
    # tokens on a 40000 floor before teamlead arbitration recovered it).
    expected = (
        card.effort_score * DEFAULT_TOKENS_PER_EFFORT
        if card.effort_score > 0
        else 0
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


#: Hard ceiling on auto-growth — budget can grow up to this multiple of
#: the effort-based baseline before the card is considered truly runaway.
#: Budget exhaustion should be a silent auto-recovery (just grow and keep
#: working) until this cap, only then is it a real incident the operator
#: needs to see.
MAX_BUDGET_GROWTH_MULTIPLIER = 3


def check_and_block_budget(card, board, publisher, log_path: Path, notifier=None) -> bool:
    if not card.is_budget_exhausted:
        return False

    from ...log import log_event
    from ...signals import SignalKind, emit_signal

    effort = int(getattr(card, "effort_score", 0) or 0)
    baseline = max(effort * DEFAULT_TOKENS_PER_EFFORT, DEFAULT_TOKENS_PER_EFFORT)
    hard_cap = baseline * MAX_BUDGET_GROWTH_MULTIPLIER
    tokens_net = int(getattr(card, "tokens_spent_net", 0) or 0)

    if tokens_net < hard_cap:
        # Soft-growth path: the card spent more than its current budget
        # but is still within the reasonable envelope for its effort
        # estimate. Treat budget exhaustion as "needs more runway", not
        # "emergency block". Grow the budget in place and keep working.
        extra = max(baseline, card.token_budget)
        previous = card.token_budget
        card.token_budget = int(max(previous + extra, tokens_net + extra))
        board.save_card(card)
        log_event(
            log_path,
            "INFO",
            "token budget grown in place to avoid block",
            task_id=card.id,
            previous=previous,
            budget=card.token_budget,
            tokens_spent_net=tokens_net,
            hard_cap=hard_cap,
        )
        return False

    # Beyond the hard cap — genuine runaway. Block and surface to the operator.
    reason = f"token budget exhausted: net={tokens_net} exceeded hard cap {hard_cap}"
    log_event(
        log_path,
        "WARN",
        "card blocked: token budget exhausted beyond hard cap",
        task_id=card.id,
        tokens_spent=card.tokens_spent,
        tokens_spent_net=tokens_net,
        token_budget=card.token_budget,
        hard_cap=hard_cap,
    )
    emit_signal(
        SignalKind.CARD_BLOCKED,
        "token_budget_exhausted",
        task_id=card.id,
        context={
            "tokens_spent": card.tokens_spent,
            "tokens_discarded": int(getattr(card, "tokens_discarded", 0) or 0),
            "token_budget": card.token_budget,
            "stage": card.stage,
            "hard_cap": hard_cap,
        },
    )
    publisher.emit("escalate", card.id, f"{card.id} BLOCKED: {reason}")
    card.block(reason)
    board.save_card(card)
    if notifier is not None:
        try:
            notifier.notify_card_blocked(card.id, 1, reason)
        except Exception:
            pass
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
