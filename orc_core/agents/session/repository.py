#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kanban state persistence repository: Protocol + filesystem implementation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Protocol

from ...infra.io.atomic_io import write_json_atomic
from ...infra.io.state_paths import kanban_state_path

_logger = logging.getLogger(__name__)


class StateRepository(Protocol):
    """Port for kanban orchestration state persistence."""

    def load_state(self, workdir: str) -> tuple[dict[str, int], dict[str, int]]: ...

    def save_state(
        self, workdir: str,
        card_fail_counts: dict[str, int],
        arbitrated_at_loop: dict[str, int],
    ) -> None: ...


class FsStateRepository:
    """Filesystem-backed kanban state repository."""

    def load_state(self, workdir: str) -> tuple[dict[str, int], dict[str, int]]:
        path = kanban_state_path(workdir)
        if not path.exists():
            return {}, {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            fail_counts = {k: int(v) for k, v in data.get("card_fail_counts", {}).items()}
            arb_loop = {k: int(v) for k, v in data.get("arbitrated_at_loop", {}).items()}
            return fail_counts, arb_loop
        except Exception as exc:
            _logger.warning("Failed to load kanban state: %s", exc)
            return {}, {}

    def save_state(
        self, workdir: str,
        card_fail_counts: dict[str, int],
        arbitrated_at_loop: dict[str, int],
    ) -> None:
        path = kanban_state_path(workdir)
        write_json_atomic(path, {
            "card_fail_counts": card_fail_counts,
            "arbitrated_at_loop": arbitrated_at_loop,
        })
