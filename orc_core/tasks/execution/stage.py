#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage specifications for a multi-phase task run."""

from __future__ import annotations

from dataclasses import dataclass


SDLC_FEEDBACK_MAX_ITERATIONS = 3


@dataclass(frozen=True)
class TaskStageSpec:
    stage_id: str
    model: str
    prompt_template: str


@dataclass(frozen=True)
class AgentPhaseSpec:
    """Describes how to run a sub-phase (commit, merge expert, etc.)."""
    step_name: str
    label: str
    model: str
    template: str
    workdir: str
    tag_suffix: str
    task_id_suffix: str
    stall_timeout: float
    ttl: float
