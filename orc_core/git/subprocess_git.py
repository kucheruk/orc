#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Default GitRunner backed by subprocess. Production implementation."""

from __future__ import annotations

import subprocess

GIT_COMMAND_TIMEOUT_SECONDS = 30.0


class SubprocessGitRunner:
    """Runs git via subprocess. Satisfies GitRunner port."""

    def run(
        self,
        workdir: str,
        args: list[str],
        *,
        timeout: float = GIT_COMMAND_TIMEOUT_SECONDS,
    ) -> tuple[bool, str, str, int]:
        try:
            result = subprocess.run(
                args,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "", "timeout", 124
        except Exception as exc:
            return False, "", str(exc), 1
        return (
            result.returncode == 0,
            result.stdout or "",
            result.stderr or "",
            int(result.returncode),
        )
