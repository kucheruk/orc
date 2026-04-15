#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead decision file parser and action executor.

The teamlead agent writes a YAML-frontmatter decision file at
``.orc/teamlead-decision.md``. This package parses it and executes actions
against the board via a polymorphic ActionHandler registry: each action
type is a class that implements ``execute(ctx)`` and registers itself via
``@register_action("action_type")``.
"""

from __future__ import annotations

from .decision import (
    DECISION_FILENAME,
    TeamleadAction,
    TeamleadDecision,
    decision_path,
    parse_teamlead_decision,
)
from .dispatcher import execute_teamlead_actions
from .registry import ActionContext, ActionHandler, register_action

from . import actions as _actions  # noqa: F401  # trigger handler registration

__all__ = [
    "ActionContext",
    "ActionHandler",
    "DECISION_FILENAME",
    "TeamleadAction",
    "TeamleadDecision",
    "decision_path",
    "execute_teamlead_actions",
    "parse_teamlead_decision",
    "register_action",
]
