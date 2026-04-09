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

STAGE_ORDER: dict[str, int] = {s: i for i, s in enumerate(STAGES)}

# Stages that carry WIP limits (configured via _index.md)
WIP_STAGES: frozenset[str] = frozenset(STAGES[2:7])  # Todo..Handoff

# Default WIP limits per stage (overridden by _index.md)
DEFAULT_WIP_LIMITS: dict[str, int] = {
    "3_Todo": 5,
    "4_Coding": 3,
    "5_Review": 3,
    "6_Testing": 3,
    "7_Handoff": 2,
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
