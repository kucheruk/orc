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
    # True when prompt_template is already fully rendered by the caller
    # (e.g. teamlead/worker/incident prompts). Stage loop must skip the
    # second format_map pass in that case, otherwise any `{...}` pattern
    # inside the substituted content (card bodies with C#-style `{obj.Prop}`,
    # traceback lines with `{stderr.strip()}` literals, etc.) would be
    # reinterpreted as a template placeholder and crash the stage.
    is_pre_rendered: bool = False


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
