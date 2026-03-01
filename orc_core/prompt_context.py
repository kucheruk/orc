#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Callable


def compose_prompt_with_project_context(
    *,
    base_prompt: str,
    workspace_root: str,
    inject_agents_md: bool,
    inject_techspec_md: bool,
    agents_path: str,
    techspec_path: str,
    on_missing: Callable[[str], None],
) -> str:
    context_chunks: list[str] = []
    root = Path(workspace_root)

    def _append_file(path_text: str, *, enabled: bool) -> None:
        if not enabled:
            return
        path = (root / path_text).resolve()
        if not path.exists():
            on_missing(path_text)
            return
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            on_missing(path_text)
            return
        context_chunks.append(
            "\n".join(
                [
                    f"<project_context_file path=\"{path_text}\">",
                    content,
                    "</project_context_file>",
                ]
            )
        )

    _append_file(agents_path, enabled=inject_agents_md)
    _append_file(techspec_path, enabled=inject_techspec_md)
    if not context_chunks:
        return base_prompt

    context_block = "\n".join(
        [
            "",
            "<project_context auto_injected=\"true\">",
            *context_chunks,
            "</project_context>",
            "",
        ]
    )
    return f"{base_prompt.rstrip()}\n{context_block}"
