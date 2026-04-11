#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Constants for the Kanban board system."""

from enum import StrEnum

# ── Stage folder names (ordered left-to-right) ─────────────────

STAGES: tuple[str, ...] = (
    "1_Inbox",
    "2_Estimate",
    "3_Todo",
    "4_Coding",
    "5_Review",
    "6_Testing",
    "7_Handoff",
    "8_Done",
)

STAGE_INBOX    = STAGES[0]   # "1_Inbox"
STAGE_ESTIMATE = STAGES[1]   # "2_Estimate"
STAGE_TODO     = STAGES[2]   # "3_Todo"
STAGE_CODING   = STAGES[3]   # "4_Coding"
STAGE_REVIEW   = STAGES[4]   # "5_Review"
STAGE_TESTING  = STAGES[5]   # "6_Testing"
STAGE_HANDOFF  = STAGES[6]   # "7_Handoff"
STAGE_DONE     = STAGES[7]   # "8_Done"

STAGE_ORDER: dict[str, int] = {s: i for i, s in enumerate(STAGES)}

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

# Short display names — full words (for log messages, notifications)
STAGE_SHORT_NAMES: dict[str, str] = {
    STAGE_INBOX: "Inbox", STAGE_ESTIMATE: "Estimate", STAGE_TODO: "Todo",
    STAGE_CODING: "Coding", STAGE_REVIEW: "Review", STAGE_TESTING: "Testing",
    STAGE_HANDOFF: "Handoff", STAGE_DONE: "Done",
}

# Abbreviated display names — compact (for TUI column headers)
STAGE_ABBREV_NAMES: dict[str, str] = {
    STAGE_INBOX: "Inbox", STAGE_ESTIMATE: "Estim", STAGE_TODO: "Todo",
    STAGE_CODING: "Code", STAGE_REVIEW: "Review", STAGE_TESTING: "Test",
    STAGE_HANDOFF: "Hand", STAGE_DONE: "Done",
}


class Action(StrEnum):
    PRODUCT = "Product"
    ARCHITECT = "Architect"
    CODING = "Coding"
    REVIEWING = "Reviewing"
    TESTING = "Testing"
    INTEGRATING = "Integrating"
    ARBITRATION = "Arbitration"
    BLOCKED = "Blocked"
    DONE = "Done"


class ClassOfService(StrEnum):
    EXPEDITE = "expedite"
    FIXED_DATE = "fixed-date"
    STANDARD = "standard"
    INTANGIBLE = "intangible"


# Priority order for sorting (lower = higher priority)
COS_PRIORITY: dict[str, int] = {
    ClassOfService.EXPEDITE: 0,
    ClassOfService.FIXED_DATE: 1,
    ClassOfService.STANDARD: 2,
    ClassOfService.INTANGIBLE: 3,
}

INDEX_FILENAME = "_index.md"
TASKS_DIR = "tasks"
