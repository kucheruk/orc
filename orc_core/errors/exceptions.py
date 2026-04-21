#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Domain exception hierarchy for ORC orchestrator."""


class OrcError(Exception):
    """Base for all ORC domain exceptions."""


class GitOperationError(OrcError):
    """Git command failed (status, checkout, merge, etc.)."""


class IntegrationError(OrcError):
    """Errors during git integration (squash-merge, preflight)."""


class WorktreeError(OrcError):
    """Errors creating/managing git worktrees."""


class TaskExecutionError(OrcError):
    """Errors during task execution lifecycle."""


class AgentProcessError(OrcError):
    """Agent process failed unexpectedly."""


class BacklogError(OrcError):
    """Errors reading/writing backlog state."""


class ConfigError(OrcError):
    """Invalid configuration."""


class AgentNotInstalledError(RuntimeError):
    """Required AI agent CLI tool is not installed."""
