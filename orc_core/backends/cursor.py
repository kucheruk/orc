#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from ..errors.exceptions import AgentNotInstalledError
from ..log import log_event

AGENT_LS_TIMEOUT_SECONDS = 15.0


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
        from ..tasks.integration.hooks import ensure_repo_hooks, ensure_repo_hooks_config
        before_path, stop_path = ensure_repo_hooks(workdir)
        ensure_repo_hooks_config(workdir, before_path, stop_path, log_path)

    def get_resume_id(self, workdir: str, log_path: Path) -> Optional[str]:
        return _get_resume_id_from_agent_ls(workdir, log_path)

    def default_model(self) -> str:
        return "gpt-5.3-codex"

    def list_models_cmd(self) -> list[str] | None:
        return ["agent", "--list-models"]


def _parse_agent_ls_output(output: str) -> Optional[str]:
    uuid_re = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
    generic_re = re.compile(r"\b[A-Za-z0-9_-]{8,}\b")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in reversed(lines):
        lower = line.lower()
        if lower.startswith(("id", "title", "name")):
            continue
        uuid_match = uuid_re.search(line)
        if uuid_match:
            return uuid_match.group(0)
        for token in generic_re.findall(line):
            token_lower = token.lower()
            if token_lower in {"id", "title", "name", "today", "yesterday"}:
                continue
            if ":" in token and all(part.isdigit() for part in token.split(":") if part):
                continue
            if not any(ch.isdigit() for ch in token):
                continue
            return token
    return None


def _get_resume_id_from_agent_ls(workdir: str, log_path: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["agent", "ls"],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=AGENT_LS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        log_event(log_path, "ERROR", "agent ls timeout", timeout_seconds=AGENT_LS_TIMEOUT_SECONDS)
        return None
    except Exception as exc:
        log_event(log_path, "ERROR", "agent ls failed", error=str(exc))
        return None
    if result.returncode != 0:
        log_event(
            log_path,
            "ERROR",
            "agent ls returned non-zero",
            returncode=result.returncode,
            stderr=result.stderr[:500],
        )
        return None
    resume_id = _parse_agent_ls_output(result.stdout)
    if resume_id:
        log_event(log_path, "INFO", "agent ls resume id", conversation_id=resume_id)
    else:
        log_event(log_path, "WARN", "agent ls returned no resume id")
    return resume_id
