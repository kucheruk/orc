#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage folder names and display names for the Kanban board."""

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
