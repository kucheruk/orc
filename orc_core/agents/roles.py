#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build role-specific prompts for kanban agents by injecting card and board context."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from ..board.action_constants import COS_PRIORITY, ClassOfService
from ..board.kanban_card import SECTION_FEEDBACK
from ..board.board_summary import format_board_summary
from ..board.stage_constants import STAGES, STAGE_DONE
from ..board.kanban_role_registry import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TEAMLEAD,
    ROLE_TEAMLEAD_TRIAGE,
    ROLE_TESTER,
    TemplateLoader,
    default_template_loader,
)

if TYPE_CHECKING:
    from ..board.kanban_board import KanbanBoard
    from ..board.kanban_card import KanbanCard

# ── Shared prompt blocks (DRY) ────────────────────────────────────

_WORKTREE_CONTEXT = (
    "## Worktree Isolation\n"
    "You are working in an **isolated git worktree**, not the main repository. "
    "Your changes will be merged to main automatically at the Handoff stage. "
    "Do NOT run `git push` or try to merge to main yourself.\n\n"
    "**Sync with upstream first:** Before starting work, run "
    "`git merge {main_branch} --no-edit` "
    "to pick up changes from other completed cards. If there are merge conflicts, "
    "resolve them — you are a coding agent, this is part of your job."
)

_FEEDBACK_LOOP_BLOCK = (
    "## Feedback Loop Awareness\n\n"
    "Check `loop_count` in the card frontmatter. If > 0:\n"
    "- Read previous feedback rounds in section 4.\n"
    "- **Previous feedback may be outdated.** Always verify current state yourself "
    "— run `ls`, `find`, `cat`. Never repeat old claims without re-checking.\n"
    "- If the coder already addressed an item and it's marked [x], verify in code and move on.\n"
    "- If you're raising the same issue again, explain specifically what's still wrong "
    "— don't just re-state it.\n"
    "- If loop_count >= 2, be extra critical of your own feedback: is this REALLY a blocker, "
    "or are you and the coder going in circles over something minor?"
)

def _escape_braces(text: str) -> str:
    """Escape ``{`` / ``}`` so they survive ``str.format_map`` without being
    interpreted as format specifiers.  Required for any user-authored content
    (card bodies, directive text) that may contain literal braces."""
    return text.replace("{", "{{").replace("}", "}}")


def build_prompt(role: str, card: "KanbanCard", board: "KanbanBoard",
                 *, main_branch: str = "main",
                 loader: TemplateLoader | None = None,
                 git_context: str = "") -> str:
    """Build a complete prompt for the given role, card, and board state."""
    if loader is None:
        loader = default_template_loader()
    template = loader.load(role)
    card_content = _escape_braces(card.to_markdown())
    # Always use relative path — agent works in worktree with its own tasks/ dir
    card_path = f"tasks/{card.stage}/{card.id}.md"
    board_summary = format_board_summary(board)
    worktree_ctx = _WORKTREE_CONTEXT.format(main_branch=main_branch)
    if git_context:
        worktree_ctx += "\n\n" + _escape_braces(git_context)

    return template.format_map(_SafeDict(
        board_summary=board_summary,
        card_path=card_path,
        card_content=card_content,
        card_id=card.id,
        card_stage=card.stage,
        card_action=card.action,
        loop_count=str(card.loop_count),
        worktree_context=worktree_ctx,
        feedback_loop=_FEEDBACK_LOOP_BLOCK,
        main_branch=main_branch,
    ))



def _elapsed_str(iso_ts: str) -> str:
    """Human-readable elapsed time since an ISO timestamp."""
    if not iso_ts:
        return "—"
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        minutes = int(delta.total_seconds() / 60)
        if minutes < 1:
            return "<1m"
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        remaining = minutes % 60
        return f"{hours}h{remaining:02d}m"
    except Exception:
        return "—"


def format_board_detail(board: "KanbanBoard", token_stats: dict[str, int] | None = None) -> str:
    """Format full board inventory for the teamlead prompt.

    Shows every card with ID, title, action, assigned agent, deps (✓/✗),
    loop count, CoS, elapsed time in stage, and token usage.
    Done cards are listed as IDs only to save tokens.
    """
    done_ids = {c.id for c in board.cards if c.stage == STAGE_DONE}
    stats = token_stats or {}
    sections: list[str] = []

    for stage in STAGES:
        cards = sorted(board.cards_in_stage(stage), key=_card_priority_key)
        limit = board.wip_limit(stage)
        count = len(cards)

        if stage == STAGE_DONE:
            if cards:
                ids = ", ".join(c.id for c in cards)
                sections.append(f"### {STAGE_DONE} [{count} cards]\n{ids}")
            else:
                sections.append(f"### {STAGE_DONE} [0 cards]")
            continue

        wip_str = f"{count}/{limit}" if limit < 999 else str(count)
        full_mark = " FULL" if limit < 999 and count >= limit else ""
        header = f"### {stage} [{wip_str} WIP{full_mark}]"

        if not cards:
            sections.append(f"{header}\n(empty)")
            continue

        rows = ["| ID | Title | Action | Agent | Deps | Loop | CoS | Elapsed | Tokens |",
                "|------|-------|--------|-------|------|------|-----|---------|--------|"]
        for c in cards:
            title = c.title[:25] + "…" if len(c.title) > 25 else c.title
            title = _sanitize_cell(title)
            agent = c.assigned_agent or "—"
            deps = _format_deps(c.dependencies, done_ids) if c.dependencies else "—"
            elapsed = _elapsed_str(c.updated_at)
            tokens = f"{stats[c.id]:,}" if c.id in stats else "—"
            rows.append(
                f"| {c.id} | {title} | {c.action} | {agent} "
                f"| {deps} | {c.loop_count} | {c.class_of_service} | {elapsed} | {tokens} |"
            )
        sections.append(header + "\n" + "\n".join(rows))

    return "\n\n".join(sections)


def _format_deps(deps: list[str], done_ids: set[str]) -> str:
    """Format dependency list with ✓/✗ markers."""
    parts = []
    for dep in deps:
        mark = "✓" if dep in done_ids else "✗"
        parts.append(f"{_sanitize_cell(dep)}{mark}")
    return " ".join(parts)


def _sanitize_cell(text: str) -> str:
    """Escape characters that break markdown table cells."""
    return text.replace("|", "∣").replace("\n", " ").replace("\r", "")


def _card_priority_key(card) -> tuple[int, str, float]:
    """Sort key: CoS rank → deadline → -ROI (highest priority first)."""
    cos_rank = COS_PRIORITY.get(card.class_of_service, 9)
    deadline = card.deadline if card.class_of_service == ClassOfService.FIXED_DATE else "9999-12-31"
    return (cos_rank, deadline, -card.roi)


_CARD_PROMPT_MAX_CHARS = 6000  # cap card body in teamlead prompts to save tokens


def _truncate_card_for_prompt(card_md: str) -> str:
    """Truncate card markdown to a reasonable size for teamlead prompts.

    Keeps frontmatter + sections 1-3 (requirements, design, notes) and
    truncates section 4 (Feedback & Checklist) which accumulates repetitive
    arbitration history.
    """
    if len(card_md) <= _CARD_PROMPT_MAX_CHARS:
        return card_md
    # Try to find section 4 and truncate just that
    idx = card_md.find(SECTION_FEEDBACK)
    if idx != -1:
        head = card_md[:idx]
        tail = card_md[idx:]
        if len(tail) > 1500:
            # Keep last 1200 chars of feedback (most recent decisions)
            tail = tail[:200] + "\n\n[... earlier feedback truncated ...]\n\n" + tail[-1200:]
        result = head + tail
        if len(result) <= _CARD_PROMPT_MAX_CHARS:
            return result
    # Hard truncate
    return card_md[:_CARD_PROMPT_MAX_CHARS] + "\n\n[... truncated ...]"


def _mode_arbitration(card, agent_log_path, **_kw) -> tuple[str, str]:
    if not card:
        return "", ""
    card_content = _escape_braces(_truncate_card_for_prompt(card.to_markdown()))
    card_path = str(card.file_path) if card.file_path else f"tasks/{card.stage}/{card.id}.md"
    log_hint = ""
    if agent_log_path:
        log_hint = (
            f"\n\n### Last Agent Session Log\n"
            f"The most recent agent session log for this card is at:\n"
            f"`{agent_log_path}`\n"
            f"**Read this file** to understand what the agent actually did — "
            f"tool calls, errors, commands run. Don't trust the card's claims alone."
        )
    context = (
        f"## Problem Card\n"
        f"This card has bounced **{card.loop_count}** times between roles.\n"
        f"File: `{card_path}`\n"
        f"````\n{card_content}\n````\n\n"
        f"Read feedback in section \"{SECTION_FEEDBACK}\", analyze the conflict.\n"
        f"Use `set_action` + `write_feedback` in the decision file to resolve — "
        f"do NOT edit the card file directly."
        f"{log_hint}"
    )
    return card_path, context


def _mode_directive(directive_text, **_kw) -> tuple[str, str]:
    return "", (
        f"## User Directive\n"
        f"The user sent this command:\n"
        f"> {_escape_braces(directive_text)}\n\n"
        f"Interpret this directive. It could be:\n"
        f"- A new task to create (→ create_card action)\n"
        f"- An instruction about existing cards (→ move/set_action/modify_deps/etc.)\n"
        f"- A question about the board (→ respond with answer)\n"
        f"- A problem report (→ investigate card files and act)\n\n"
        f"Read relevant card files in `tasks/` if needed to understand context."
    )


def _mode_health(diagnostic_info, **_kw) -> tuple[str, str]:
    return "", (
        f"## Board Health Alert\n"
        f"The system detected a problem:\n"
        f"{diagnostic_info}\n\n"
        f"Diagnose the root cause and take corrective action.\n"
        f"Common patterns:\n"
        f"- WIP deadlock: move dep-blocked cards back, remove non-critical deps, adjust WIP limits\n"
        f"- Starvation: promote cards from earlier stages, reduce blockers\n"
        f"- Single-card thrashing: reset loop_count, split large cards"
    )


_MODE_HANDLERS: dict[str, Callable[..., tuple[str, str]]] = {
    "arbitration": _mode_arbitration,
    "directive": _mode_directive,
    "health": _mode_health,
}


def _build_mode_context(mode: str, **kwargs) -> tuple[str, str]:
    handler = _MODE_HANDLERS.get(mode)
    if handler:
        return handler(**kwargs)
    return "", ""


def build_teamlead_prompt(
    *,
    mode: str,
    board: "KanbanBoard",
    card: "KanbanCard | None" = None,
    directive_text: str = "",
    diagnostic_info: str = "",
    decision_path: str = "",
    agent_log_path: str = "",
    token_stats: dict[str, int] | None = None,
    loader: TemplateLoader | None = None,
    main_branch: str = "",
) -> str:
    """Build a teamlead prompt for any invocation mode.

    Modes: 'arbitration', 'directive', 'health'.
    """
    if loader is None:
        loader = default_template_loader()
    template = loader.load(ROLE_TEAMLEAD)
    board_detail = _escape_braces(format_board_detail(board, token_stats=token_stats))
    board_summary = format_board_summary(board)

    # Build mode-specific context via dispatch
    card_path, mode_context = _build_mode_context(
        mode, card=card, directive_text=directive_text,
        diagnostic_info=diagnostic_info, agent_log_path=agent_log_path,
    )

    return template.format_map(_SafeDict(
        board_summary=board_summary,
        board_detail=board_detail,
        mode_context=mode_context,
        card_path=card_path,
        card_content=_escape_braces(card.to_markdown()) if card else "",
        card_id=card.id if card else "",
        card_stage=card.stage if card else "",
        card_action=card.action if card else "",
        loop_count=str(card.loop_count) if card else "0",
        decision_path=decision_path,
        main_branch=main_branch,
    ))


from ..text_parse import SafeDict as _SafeDict
