#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Action and ClassOfService enums for the Kanban board."""

from enum import StrEnum


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
