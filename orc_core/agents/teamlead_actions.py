#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead decision file parser and action executor.

The teamlead agent writes a YAML-frontmatter decision file at .orc/teamlead-decision.md.
This module parses it and executes the actions against the board.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..board.kanban_constants import STAGE_DONE, STAGE_INBOX, STAGES, Action
from ..infra.io.text_parse import parse_frontmatter

if TYPE_CHECKING:
    from ..board.kanban_board import KanbanBoard
    from .kanban_publisher import KanbanPublisher

_logger = logging.getLogger(__name__)

DECISION_FILENAME = "teamlead-decision.md"

# Fields the teamlead can update via update_card action
_UPDATABLE_FIELDS = frozenset({
    "value_score", "effort_score", "class_of_service",
    "cos_justification", "deadline", "loop_count", "title",
})


@dataclass
class TeamleadAction:
    type: str
    params: dict[str, Any]
    reason: str = ""


@dataclass
class TeamleadDecision:
    actions: list[TeamleadAction] = field(default_factory=list)
    summary: str = ""


def decision_path(workdir: str) -> Path:
    """Return the standard decision file path for a workdir."""
    p = Path(workdir) / ".orc"
    p.mkdir(parents=True, exist_ok=True)
    return p / DECISION_FILENAME


def parse_teamlead_decision(path: Path) -> TeamleadDecision:
    """Parse a teamlead decision file. Raises ValueError on bad format."""
    text = path.read_text(encoding="utf-8")
    data, _ = parse_frontmatter(text, str(path))

    summary = str(data.get("summary", "")).strip()
    raw_actions = data.get("actions", [])
    if not isinstance(raw_actions, list):
        raise ValueError(f"'actions' must be a list, got {type(raw_actions).__name__}")

    actions: list[TeamleadAction] = []
    for i, raw in enumerate(raw_actions):
        if not isinstance(raw, dict):
            raise ValueError(f"Action #{i} is not a dict")
        action_type = str(raw.get("type", "")).strip()
        if not action_type:
            raise ValueError(f"Action #{i} missing 'type'")
        reason = str(raw.get("reason", "")).strip()
        params = {k: v for k, v in raw.items() if k not in ("type", "reason")}
        actions.append(TeamleadAction(type=action_type, params=params, reason=reason))

    return TeamleadDecision(actions=actions, summary=summary)


def execute_teamlead_actions(
    board: "KanbanBoard",
    decision: TeamleadDecision,
    publisher: "KanbanPublisher",
    log_path: Path,
) -> list[str]:
    """Execute parsed actions against the board. Returns list of error strings."""
    from ..infra.io.logging import log_event

    errors: list[str] = []
    if decision.summary:
        publisher._emit("teamlead", "", f"[TL] {decision.summary}")

    for action in decision.actions:
        try:
            _execute_one(board, action, publisher, log_path)
            log_event(log_path, "INFO", "teamlead action executed",
                      action_type=action.type, reason=action.reason,
                      params={k: str(v)[:200] for k, v in action.params.items()})
        except Exception as exc:
            msg = f"{action.type}: {exc}"
            errors.append(msg)
            _logger.warning("Teamlead action failed: %s", msg)
            log_event(log_path, "WARN", "teamlead action failed",
                      action_type=action.type, error=str(exc))

    return errors


# ── Action implementations ─────────────────────────────────────


def _do_move_card(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    to_stage = _require(p, "to_stage")
    if to_stage not in STAGES:
        raise ValueError(f"Invalid stage: {to_stage}")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    # Release agent before moving — the assigned agent's worktree is stage-specific
    if card.assigned_agent:
        board.release_agent(card)
    board.move_card(card, to_stage, allow_backward=True,
                    reason=f"teamlead: {reason}" if reason else "teamlead action")
    publisher._emit("teamlead", card_id, f"Moved {card_id} → {to_stage}: {reason}")


def _do_set_action(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    action_str = _require(p, "action")
    try:
        Action(action_str)
    except ValueError:
        raise ValueError(f"Invalid action: {action_str}")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    old = card.action
    card.action = action_str
    if card.assigned_agent:
        board.release_agent(card)
    board.save_card(card, old_action=old, role="teamlead")
    # Apply automatic stage transition if the action change implies one
    from .kanban_agent_output import _FORWARD_MOVES
    new_stage = _FORWARD_MOVES.get((card.stage, action_str))
    if new_stage and board.has_wip_room(new_stage):
        board.move_card(card, new_stage, reason=f"teamlead: {old} → {action_str}")
        publisher._emit("teamlead", card_id,
                        f"{card_id} action: {old} → {action_str}, moved → {new_stage}: {reason}")
    else:
        publisher._emit("teamlead", card_id, f"{card_id} action: {old} → {action_str}: {reason}")


def _do_modify_deps(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    to_add = p.get("add", []) or []
    to_remove = p.get("remove", []) or []
    if not isinstance(to_add, list):
        to_add = [to_add]
    if not isinstance(to_remove, list):
        to_remove = [to_remove]
    to_add = [str(d) for d in to_add]
    to_remove = [str(d) for d in to_remove]
    changed = False
    for dep in to_remove:
        if dep in card.dependencies:
            card.dependencies.remove(dep)
            changed = True
    for dep in to_add:
        if dep not in card.dependencies:
            card.dependencies.append(dep)
            changed = True
    if changed:
        board.save_card(card)
        publisher._emit("teamlead", card_id,
                        f"{card_id} deps: +[{','.join(to_add)}] -[{','.join(to_remove)}]: {reason}")


def _do_create_card(board, p, reason, publisher, log_path=None):
    title = _require(p, "title")
    stage = str(p.get("stage", STAGE_INBOX))
    action_str = str(p.get("action", "Product"))
    body = str(p.get("body", ""))
    if stage not in STAGES:
        raise ValueError(f"Invalid stage: {stage}")
    try:
        Action(action_str)
    except ValueError:
        raise ValueError(f"Invalid action: {action_str}")
    if stage == STAGE_INBOX:
        card = board.create_inbox_card(board.next_card_id(), title)
    else:
        card = board.create_expedite_card(
            board.next_card_id(), title, body or "",
            stage=stage, action=action_str, cos_justification=reason,
        )
    publisher._emit("teamlead", card.id, f"Created {card.id}: {title}: {reason}")


def _do_set_wip_limit(board, p, reason, publisher, log_path=None):
    stage = _require(p, "stage")
    limit = int(_require(p, "limit"))
    if stage not in STAGES:
        raise ValueError(f"Invalid stage: {stage}")
    if limit < 1:
        raise ValueError(f"WIP limit must be >= 1, got {limit}")
    board.set_wip_limit(stage, limit)
    publisher._emit("teamlead", "", f"WIP {stage}: → {limit}: {reason}")


def _do_update_card(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    field_name = _require(p, "field")
    value = _require(p, "value")
    if field_name not in _UPDATABLE_FIELDS:
        raise ValueError(f"Field '{field_name}' not updatable (allowed: {', '.join(sorted(_UPDATABLE_FIELDS))})")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    old_val = getattr(card, field_name, None)
    # Type coercion for numeric fields
    if field_name in ("value_score", "effort_score", "loop_count"):
        if not isinstance(value, (int, float, str)):
            raise ValueError(f"Expected number for {field_name}, got {type(value).__name__}")
        value = int(value)
    setattr(card, field_name, value)
    card.refresh_roi()
    board.save_card(card)
    publisher._emit("teamlead", card_id, f"{card_id}.{field_name}: {old_val} → {value}: {reason}")


def _do_notify(board, p, reason, publisher, log_path=None):
    from ..notifications.notify import send_telegram_message
    message = str(p.get("message", "")).strip()
    if not message:
        raise ValueError("Missing required param: 'message'")
    if log_path is None:
        raise ValueError("notify action requires log_path (internal error)")
    send_telegram_message(message, log_path)
    publisher._emit("teamlead", "", f"[TL] Telegram sent: {message[:100]}")


def _do_skip_card(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    if card.assigned_agent:
        board.release_agent(card)
    # Move directly to Done, bypassing the pipeline
    card.action = Action.DONE.value
    board.save_card(card)
    board.move_card(card, STAGE_DONE, allow_backward=True,
                    reason=f"teamlead skip: {reason}" if reason else "teamlead skip")
    publisher._emit("teamlead", card_id, f"Skipped {card_id} → {STAGE_DONE}: {reason}")


def _do_write_feedback(board, p, reason, publisher, log_path=None):
    card_id = _require(p, "card_id")
    text = str(p.get("text", "")).strip()
    if not text:
        raise ValueError("Missing required param: 'text'")
    card = board.card_by_id(card_id)
    if card is None:
        raise ValueError(f"Card not found: {card_id}")
    # Append feedback to section 4 of the card body
    marker = "# 4. Feedback & Checklist"
    body = card.body or ""
    if marker in body:
        body = body.rstrip() + "\n\n" + text + "\n"
    else:
        body = body.rstrip() + f"\n\n{marker}\n\n{text}\n"
    card.body = body
    board.save_card(card)
    publisher._emit("teamlead", card_id, f"{card_id} feedback updated: {reason}")


def _require(params: dict, key: str) -> Any:
    """Get a required parameter or raise."""
    val = params.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError(f"Missing required param: '{key}'")
    return val


# ── Action dispatch registry ────────────────────────────────────


def _do_respond(board, p, reason, publisher, log_path=None):
    msg = str(p.get("message", ""))
    if msg:
        publisher._emit("teamlead", "", msg)


_ACTION_HANDLERS: dict[str, Callable] = {
    "move_card": _do_move_card,
    "set_action": _do_set_action,
    "modify_deps": _do_modify_deps,
    "create_card": _do_create_card,
    "set_wip_limit": _do_set_wip_limit,
    "update_card": _do_update_card,
    "notify": _do_notify,
    "skip_card": _do_skip_card,
    "write_feedback": _do_write_feedback,
    "respond": _do_respond,
}


def _execute_one(
    board: "KanbanBoard",
    action: TeamleadAction,
    publisher: "KanbanPublisher",
    log_path: "Path | None" = None,
) -> None:
    """Execute a single teamlead action."""
    handler = _ACTION_HANDLERS.get(action.type)
    if handler is None:
        raise ValueError(f"Unknown action type: {action.type}")
    handler(board, action.params, action.reason, publisher, log_path)
