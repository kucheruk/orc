#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Use case: restart a task after failure."""

from __future__ import annotations

from ..execution.engine import TaskExecutionEngine
from ..execution.request import TaskExecutionRequest, TaskExecutionResult


def restart_task(
    engine: TaskExecutionEngine,
    request: TaskExecutionRequest,
) -> TaskExecutionResult:
    """Re-execute a task after failure.

    Delegates to ``engine.execute`` which already handles resume semantics
    (session continuation, restart_count propagation via timeline).
    """
    return engine.execute(request)
