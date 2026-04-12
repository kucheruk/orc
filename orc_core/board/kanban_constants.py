#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constants for the Kanban board system.

Split into thematic modules for focused imports (CRP):
  - stage_constants: stage names, ordering, display names
  - action_constants: Action/ClassOfService enums, COS_PRIORITY
  - limits_constants: WIP limits, INDEX_FILENAME, TASKS_DIR

This file re-exports everything for convenience.
"""

from .stage_constants import (  # noqa: F401
    STAGES,
    STAGE_INBOX,
    STAGE_ESTIMATE,
    STAGE_TODO,
    STAGE_CODING,
    STAGE_REVIEW,
    STAGE_TESTING,
    STAGE_HANDOFF,
    STAGE_DONE,
    STAGE_ORDER,
    STAGE_SHORT_NAMES,
    STAGE_ABBREV_NAMES,
)

from .action_constants import (  # noqa: F401
    Action,
    ClassOfService,
    COS_PRIORITY,
)

from .limits_constants import (  # noqa: F401
    WIP_STAGES,
    DEFAULT_WIP_LIMITS,
    INDEX_FILENAME,
    TASKS_DIR,
)
