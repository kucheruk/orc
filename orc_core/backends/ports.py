#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ports that `backends/` needs from the outside world.

Declaring these here lets backends stay independent of higher layers
like `tasks/`. Concrete implementations live elsewhere and are injected
from the composition root.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class RepoHooksInstaller(Protocol):
    """Installs per-repo agent hook scripts into a workspace.

    The concrete implementation writes agent-specific hook scripts and
    wires them into the backend's config file; it lives in a higher
    layer (e.g. `tasks/integration/hooks.py`) because hook content is
    driven by task lifecycle semantics.
    """

    def install(self, workdir: str, log_path: Path) -> None: ...
