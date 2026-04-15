#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


from ..errors.exceptions import AgentNotInstalledError


class ClaudeNotInstalledError(AgentNotInstalledError):
    pass


class ClaudeBackend:

    @property
    def name(self) -> str:
        return "claude"

    @property
    def cli_binary(self) -> str:
        return "claude"

    def ensure_installed(self) -> None:
        if shutil.which("claude"):
            return
        raise ClaudeNotInstalledError(
            "\u274c claude \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0432 PATH.\n"
            "Install Claude Code: npm install -g @anthropic-ai/claude-code\n"
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439: claude --version"
        )

    def build_agent_cmd(
        self,
        *,
        model: str,
        prompt: str | None = None,
        resume_id: str | None = None,
        resume_latest: bool = False,
        resume_prompt: str | None = None,
    ) -> list[str]:
        cmd = [
            "claude",
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            model,
            "--dangerously-skip-permissions",
        ]
        if resume_id:
            cmd.extend(["-r", resume_id])
            if resume_prompt:
                cmd.append(resume_prompt)
        elif resume_latest:
            cmd.append("--continue")
            if resume_prompt:
                cmd.append(resume_prompt)
        elif prompt is not None:
            cmd.append(prompt)
        else:
            raise ValueError("prompt is required when not resuming")
        return cmd

    def setup_hooks(self, workdir: str, log_path: Path) -> None:
        pass

    def get_resume_id(self, workdir: str, log_path: Path) -> Optional[str]:
        return None

    def default_model(self) -> str:
        return "sonnet"

    def list_models_cmd(self) -> list[str] | None:
        return None
