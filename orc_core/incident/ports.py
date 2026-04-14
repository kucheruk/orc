#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports for the incident subsystem — structural types it depends on."""

from __future__ import annotations

from typing import Protocol


class FailedTasksSource(Protocol):
    """Read-only source of failed task ids.

    IncidentManager queries this to decide whether an injected fix is itself
    failing. Any object exposing a ``failed_tasks`` list satisfies the port.
    """

    @property
    def failed_tasks(self) -> list[str]: ...
