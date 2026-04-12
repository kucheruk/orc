#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Display constants for TUI rendering — extracted from models/session_types.py."""

# ── Reasoning / events line counts ─────────────────────────────────

REASONING_LINES_FULL = 9
REASONING_LINES_MEDIUM = 5
REASONING_LINES_COMPACT = 3
EVENTS_LINES_FULL = 8
EVENTS_LINES_MEDIUM = 4
RECENT_LOG_MAX_LINES = 10
RECENT_COMMANDS_COUNT = 6
RECENT_FILES_COUNT = 6

# ── Heading / status truncation ────────────────────────────────────

HEADING_MAX_LENGTH = 120
HEADING_TRUNCATE_MEDIUM = 50
HEADING_TRUNCATE_COMPACT = 30
STATUS_TRUNCATE_FULL = 96
STATUS_TRUNCATE_MEDIUM = 60
STATUS_TRUNCATE_COMPACT = 40

# ── Token display thresholds ──────────────────────────────────────

TOKEN_THRESHOLD_MILLIONS = 1_000_000
TOKEN_THRESHOLD_THOUSANDS = 1_000

# ── Last-line truncation ──────────────────────────────────���───────

LAST_LINE_COMMAND_TRUNCATE = 30
LAST_LINE_FILE_TRUNCATE = 30
LAST_LINE_SOLO_TRUNCATE = 60

# ── Placeholders ────────────────────────────────────��─────────────

PLACEHOLDER_WAITING = "waiting..."
PLACEHOLDER_COMMANDS = "waiting for tool calls..."
PLACEHOLDER_FILES = "waiting for file operations..."
PLACEHOLDER_LAST = "waiting"

# ── Timing ──────────────────────────────────────���─────────────────

STALL_THRESHOLD_SECONDS = 60.0
