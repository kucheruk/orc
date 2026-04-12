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

INDEX_FILENAME = "_index.md"
TASKS_DIR = "tasks"
