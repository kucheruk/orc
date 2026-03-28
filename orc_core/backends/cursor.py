#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..agent_preflight import AgentNotInstalledError
from ..logging import log_event


class CursorBackend:

    @property
    def name(self) -> str:
        return "cursor"

    @property
    def cli_binary(self) -> str:
        return "agent"

    def ensure_installed(self) -> None:
        if shutil.which("agent"):
            return
        raise AgentNotInstalledError(
            "\u274c agent \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d \u0432 PATH.\n"
            "Install Cursor CLI: https://cursor.com/docs/cli/introduction\n"
            "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0443 \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439: agent --version"
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
            "agent",
            "-p",
            "--force",
            "--model",
            model,
            "--output-format",
            "stream-json",
            "--stream-partial-output",
        ]
        if resume_id:
            cmd.extend(["--resume", resume_id])
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
        from ..hooks import ensure_repo_hooks, ensure_repo_hooks_config
        before_path, stop_path = ensure_repo_hooks(workdir)
        ensure_repo_hooks_config(workdir, before_path, stop_path, log_path)

    def get_resume_id(self, workdir: str, log_path: Path) -> Optional[str]:
        from ..task_state import get_resume_id_from_agent_ls
        return get_resume_id_from_agent_ls(workdir, log_path)

    def default_model(self) -> str:
        return "gpt-5.3-codex"

    def list_models_cmd(self) -> list[str] | None:
        return ["agent", "--list-models"]
