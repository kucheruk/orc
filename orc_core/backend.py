#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Backend(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def cli_binary(self) -> str: ...

    def ensure_installed(self) -> None: ...

    def build_agent_cmd(
        self,
        *,
        model: str,
        prompt: str | None = None,
        resume_id: str | None = None,
        resume_latest: bool = False,
        resume_prompt: str | None = None,
    ) -> list[str]: ...

    def setup_hooks(self, workdir: str, log_path: Path) -> None: ...

    def get_resume_id(self, workdir: str, log_path: Path) -> str | None: ...

    def default_model(self) -> str: ...

    def list_models_cmd(self) -> list[str] | None: ...


SUPPORTED_BACKENDS: tuple[str, ...] = ("cursor", "claude", "codex")


def get_backend(name: str = "cursor") -> Backend:
    if name == "cursor":
        from .backends.cursor import CursorBackend
        return CursorBackend()
    if name == "claude":
        from .backends.claude import ClaudeBackend
        return ClaudeBackend()
    if name == "codex":
        from .backends.codex import CodexBackend
        return CodexBackend()
    raise ValueError(f"Unknown backend: {name!r}. Supported: {', '.join(SUPPORTED_BACKENDS)}")
