#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Role permissions for structured card_update results."""

from __future__ import annotations

from ...board.kanban_role_registry import (
    ROLE_ARCHITECT,
    ROLE_CODER,
    ROLE_INTEGRATOR,
    ROLE_PRODUCT,
    ROLE_REVIEWER,
    ROLE_TESTER,
)

ROLE_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    ROLE_PRODUCT: frozenset({"title", "value_score", "class_of_service", "cos_justification", "deadline"}),
    ROLE_ARCHITECT: frozenset({"effort_score", "dependencies"}),
    ROLE_CODER: frozenset(),
    ROLE_REVIEWER: frozenset(),
    ROLE_TESTER: frozenset(),
    ROLE_INTEGRATOR: frozenset(),
}

ROLE_ALLOWED_SECTIONS: dict[str, frozenset[str]] = {
    ROLE_PRODUCT: frozenset({"product_requirements"}),
    ROLE_ARCHITECT: frozenset({"technical_design"}),
    ROLE_CODER: frozenset({"implementation_notes"}),
    ROLE_REVIEWER: frozenset(),
    ROLE_TESTER: frozenset(),
    ROLE_INTEGRATOR: frozenset({"implementation_notes"}),
}

ROLE_CAN_APPEND_FEEDBACK: dict[str, bool] = {
    ROLE_PRODUCT: True,
    ROLE_ARCHITECT: True,
    ROLE_CODER: True,
    ROLE_REVIEWER: True,
    ROLE_TESTER: True,
    ROLE_INTEGRATOR: True,
}


def allowed_fields(role: str) -> frozenset[str]:
    return ROLE_ALLOWED_FIELDS.get(role, frozenset())


def allowed_sections(role: str) -> frozenset[str]:
    return ROLE_ALLOWED_SECTIONS.get(role, frozenset())


def can_append_feedback(role: str) -> bool:
    return ROLE_CAN_APPEND_FEEDBACK.get(role, False)
