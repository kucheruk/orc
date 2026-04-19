#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WIP limits, index file name, and tasks directory constants."""

from .stage_constants import STAGES, STAGE_TODO, STAGE_CODING, STAGE_REVIEW, STAGE_TESTING, STAGE_HANDOFF

# Stages that carry WIP limits (configured via _index.md)
WIP_STAGES: frozenset[str] = frozenset(STAGES[2:7])  # Todo..Handoff

# Default WIP limits per stage (overridden by _index.md)
DEFAULT_WIP_LIMITS: dict[str, int] = {
    STAGE_TODO: 5,
    STAGE_CODING: 3,
    STAGE_REVIEW: 3,
    STAGE_TESTING: 3,
    STAGE_HANDOFF: 2,
}

# Loop-count thresholds — used in code AND referenced in prompts
LOOP_THRESHOLD = 2            # teamlead arbitration
ESCALATION_THRESHOLD = 4      # force-block / escalation

# Effort-score thresholds
DECOMPOSITION_EFFORT_THRESHOLD = 70   # architect must split above this
DECOMPOSITION_MAX_SUB_EFFORT = 50     # sub-cards must be at or below

# Token-budget defaults (also used by teamlead/pull-time budget growth)
# 10K/effort_point leaves room for one legitimate restart per card; net of
# discarded attempts is what gates blocking, see KanbanCard.is_budget_exhausted.
TOKENS_PER_EFFORT_POINT = 10000       # token_budget = effort_score * this
MIN_TOKEN_BUDGET = 40000              # floor when effort_score <= 0

INDEX_FILENAME = "_index.md"
TASKS_DIR = "tasks"
