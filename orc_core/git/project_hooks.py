#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fire-and-forget project hook scripts on kanban events.

Projects place executable scripts in ``{workspace}/.orc/hooks/``.
File stem (without extension) determines the event name, e.g.
``on_move.sh`` fires on every card move, ``on_complete.sh`` on
meaningful completions.

All event data is passed via ``ORC_*`` environment variables.
Hook failures never affect ORC operation.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

_logger = logging.getLogger(__name__)


def fire_hooks(workdir: str, event: str, env_vars: dict[str, str]) -> None:
    """Discover and launch hook scripts for *event* in the project at *workdir*.

    Runs each matching script as a detached subprocess with *env_vars*
    merged into the current environment.  Any failure is silently logged.
    """
    try:
        hooks_dir = Path(workdir) / ".orc" / "hooks"
        if not hooks_dir.is_dir():
            return

        scripts: list[Path] = []
        for entry in hooks_dir.iterdir():
            if entry.stem == event and entry.is_file() and os.access(entry, os.X_OK):
                scripts.append(entry)

        if not scripts:
            return

        run_env = {**os.environ, **env_vars, "ORC_EVENT": event, "ORC_WORKSPACE": workdir}

        for script in scripts:
            try:
                subprocess.Popen(
                    [str(script)],
                    env=run_env,
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                _logger.debug("hook %s failed to launch", script, exc_info=True)
    except Exception:
        _logger.debug("fire_hooks(%s, %s) failed", event, workdir, exc_info=True)
