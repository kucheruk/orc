#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared parameter validation helpers for teamlead action handlers."""

from __future__ import annotations

from typing import Any

from ....board.action_constants import Action
from ....board.stage_constants import STAGES


def require(params: dict, key: str) -> Any:
    """Get a required parameter or raise."""
    val = params.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        raise ValueError(f"Missing required param: '{key}'")
    return val


def ensure_stage(stage: str) -> None:
    if stage not in STAGES:
        raise ValueError(f"Invalid stage: {stage}")


def ensure_action(action_str: str) -> None:
    try:
        Action(action_str)
    except ValueError:
        raise ValueError(f"Invalid action: {action_str}")
