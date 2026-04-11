#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


from ..cli.agent_preflight import AgentNotInstalledError


class CodexNotInstalledError(AgentNotInstalledError):
    pass


class CodexBackend:

    @property
    def name(self) -> str:
        return "codex"

    @property
    def cli_binary(self) -> str:
        return "codex"

    def ensure_installed(self) -> None:
        if shutil.which("codex"):
            return
        raise CodexNotInstalledError(
            "\u274c codex \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0432 PATH.\n"
            "Install Codex: npm install -g @openai/codex\n"
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439: codex --version"
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
        if resume_id:
            cmd = ["codex", "exec", "resume", resume_id]
        elif resume_latest:
            cmd = ["codex", "exec", "resume", "--last"]
        if resume_id or resume_latest:
            if resume_prompt:
                cmd.append(resume_prompt)
            return cmd
        cmd = [
            "codex",
            "exec",
            "--full-auto",
            "--model",
            model,
            "--json",
        ]
        if prompt is not None:
            cmd.append(prompt)
        else:
            raise ValueError("prompt is required when not resuming")
        return cmd

    def setup_hooks(self, workdir: str, log_path: Path) -> None:
        pass

    def get_resume_id(self, workdir: str, log_path: Path) -> Optional[str]:
        return None

    def default_model(self) -> str:
        return "codex-mini"

    def list_models_cmd(self) -> list[str] | None:
        return None
