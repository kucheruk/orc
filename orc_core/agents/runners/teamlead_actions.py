#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead decision file parser and action executor.

The teamlead agent writes a YAML-frontmatter decision file at .orc/teamlead-decision.md.
This module parses it and executes actions against the board via a polymorphic
ActionHandler registry: each action type is a class that implements `execute(ctx)`
and registers itself via `@register_action("action_type")`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from ...board.action_constants import Action
from ...board.stage_constants import STAGES, STAGE_DONE, STAGE_INBOX
from ...text_parse import parse_frontmatter
from ...board.use_cases.create_card import create_expedite_card, create_inbox_card

if TYPE_CHECKING:
    from ...board.kanban_board import KanbanBoard
    from ..kanban_publisher import KanbanPublisher

_logger = logging.getLogger(__name__)

DECISION_FILENAME = "teamlead-decision.md"

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


@dataclass
class ActionContext:
    """Bundle of dependencies each ActionHandler needs to run."""
    board: "KanbanBoard"
    params: dict[str, Any]
    reason: str
    publisher: "KanbanPublisher"
    log_path: Path | None = None


class ActionHandler(Protocol):
    """Port for executing one teamlead action type."""
    def execute(self, ctx: ActionContext) -> None: ...


_REGISTRY: dict[str, ActionHandler] = {}


def register_action(name: str):
    """Register an ActionHandler class under a string action type."""
    def decorator(cls: type) -> type:
        _REGISTRY[name] = cls()
        return cls
    return decorator


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
    from ...log import log_event

    errors: list[str] = []
    if decision.summary:
        publisher.emit("teamlead", "", f"[TL] {decision.summary}")

    for action in decision.actions:
        ctx = ActionContext(
            board=board,
            params=action.params,
            reason=action.reason,
            publisher=publisher,
            log_path=log_path,
        )
        try:
            _execute_one(action, ctx)
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


def _execute_one(action: TeamleadAction, ctx: ActionContext) -> None:
    handler = _REGISTRY.get(action.type)
    if handler is None:
        raise ValueError(f"Unknown action type: {action.type}")
    handler.execute(ctx)


def _require(params: dict, key: str) -> Any:
    """Get a required parameter or raise."""
    val = params.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError(f"Missing required param: '{key}'")
    return val


# ── Action handlers ────────────────────────────────────────────


@register_action("move_card")
class MoveCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        to_stage = _require(ctx.params, "to_stage")
        if to_stage not in STAGES:
            raise ValueError(f"Invalid stage: {to_stage}")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        if card.assigned_agent:
            ctx.board.release_agent(card)
        ctx.board.move_card(
            card, to_stage, allow_backward=True,
            reason=f"teamlead: {ctx.reason}" if ctx.reason else "teamlead action",
        )
        ctx.publisher.emit("teamlead", card_id, f"Moved {card_id} → {to_stage}: {ctx.reason}")


@register_action("set_action")
class SetActionHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        action_str = _require(ctx.params, "action")
        try:
            Action(action_str)
        except ValueError:
            raise ValueError(f"Invalid action: {action_str}")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        old = card.action
        card.action = action_str
        if card.assigned_agent:
            ctx.board.release_agent(card)
        ctx.board.save_card(card, old_action=old, role="teamlead")
        from ..kanban_agent_output import _FORWARD_MOVES
        new_stage = _FORWARD_MOVES.get((card.stage, action_str))
        if new_stage and ctx.board.has_wip_room(new_stage):
            ctx.board.move_card(card, new_stage, reason=f"teamlead: {old} → {action_str}")
            ctx.publisher.emit("teamlead", card_id,
                               f"{card_id} action: {old} → {action_str}, moved → {new_stage}: {ctx.reason}")
        else:
            ctx.publisher.emit("teamlead", card_id, f"{card_id} action: {old} → {action_str}: {ctx.reason}")


@register_action("modify_deps")
class ModifyDepsHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        to_add = ctx.params.get("add", []) or []
        to_remove = ctx.params.get("remove", []) or []
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
            ctx.board.save_card(card)
            ctx.publisher.emit("teamlead", card_id,
                               f"{card_id} deps: +[{','.join(to_add)}] -[{','.join(to_remove)}]: {ctx.reason}")


@register_action("create_card")
class CreateCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        title = _require(ctx.params, "title")
        stage = str(ctx.params.get("stage", STAGE_INBOX))
        action_str = str(ctx.params.get("action", "Product"))
        body = str(ctx.params.get("body", ""))
        if stage not in STAGES:
            raise ValueError(f"Invalid stage: {stage}")
        try:
            Action(action_str)
        except ValueError:
            raise ValueError(f"Invalid action: {action_str}")
        if stage == STAGE_INBOX:
            card = create_inbox_card(ctx.board, title)
        else:
            card = create_expedite_card(
                ctx.board, title, body or "",
                stage=stage, action=action_str, cos_justification=ctx.reason,
            )
        ctx.publisher.emit("teamlead", card.id, f"Created {card.id}: {title}: {ctx.reason}")


@register_action("set_wip_limit")
class SetWipLimitHandler:
    def execute(self, ctx: ActionContext) -> None:
        stage = _require(ctx.params, "stage")
        limit = int(_require(ctx.params, "limit"))
        if stage not in STAGES:
            raise ValueError(f"Invalid stage: {stage}")
        if limit < 1:
            raise ValueError(f"WIP limit must be >= 1, got {limit}")
        ctx.board.set_wip_limit(stage, limit)
        ctx.publisher.emit("teamlead", "", f"WIP {stage}: → {limit}: {ctx.reason}")


@register_action("update_card")
class UpdateCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        field_name = _require(ctx.params, "field")
        value = _require(ctx.params, "value")
        if field_name not in _UPDATABLE_FIELDS:
            raise ValueError(f"Field '{field_name}' not updatable (allowed: {', '.join(sorted(_UPDATABLE_FIELDS))})")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        old_val = getattr(card, field_name, None)
        if field_name in ("value_score", "effort_score", "loop_count"):
            if not isinstance(value, (int, float, str)):
                raise ValueError(f"Expected number for {field_name}, got {type(value).__name__}")
            value = int(value)
        setattr(card, field_name, value)
        card.refresh_roi()
        ctx.board.save_card(card)
        ctx.publisher.emit("teamlead", card_id, f"{card_id}.{field_name}: {old_val} → {value}: {ctx.reason}")


@register_action("notify")
class NotifyHandler:
    def execute(self, ctx: ActionContext) -> None:
        from ...notifications.notify import send_telegram_message
        message = str(ctx.params.get("message", "")).strip()
        if not message:
            raise ValueError("Missing required param: 'message'")
        if ctx.log_path is None:
            raise ValueError("notify action requires log_path (internal error)")
        send_telegram_message(message, ctx.log_path)
        ctx.publisher.emit("teamlead", "", f"[TL] Telegram sent: {message[:100]}")


@register_action("skip_card")
class SkipCardHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        if card.assigned_agent:
            ctx.board.release_agent(card)
        card.action = Action.DONE.value
        ctx.board.save_card(card)
        ctx.board.move_card(
            card, STAGE_DONE, allow_backward=True,
            reason=f"teamlead skip: {ctx.reason}" if ctx.reason else "teamlead skip",
        )
        ctx.publisher.emit("teamlead", card_id, f"Skipped {card_id} → {STAGE_DONE}: {ctx.reason}")


@register_action("write_feedback")
class WriteFeedbackHandler:
    def execute(self, ctx: ActionContext) -> None:
        card_id = _require(ctx.params, "card_id")
        text = str(ctx.params.get("text", "")).strip()
        if not text:
            raise ValueError("Missing required param: 'text'")
        card = ctx.board.card_by_id(card_id)
        if card is None:
            raise ValueError(f"Card not found: {card_id}")
        marker = "# 4. Feedback & Checklist"
        body = card.body or ""
        if marker in body:
            body = body.rstrip() + "\n\n" + text + "\n"
        else:
            body = body.rstrip() + f"\n\n{marker}\n\n{text}\n"
        card.body = body
        ctx.board.save_card(card)
        ctx.publisher.emit("teamlead", card_id, f"{card_id} feedback updated: {ctx.reason}")


@register_action("respond")
class RespondHandler:
    def execute(self, ctx: ActionContext) -> None:
        msg = str(ctx.params.get("message", ""))
        if msg:
            ctx.publisher.emit("teamlead", "", msg)
