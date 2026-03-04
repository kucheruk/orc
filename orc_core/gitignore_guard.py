#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

REQUIRED_ORC_IGNORE_RULES = (".orc/", "/.orc/")
REQUIRED_ORC_IGNORE_SNIPPET = "\n# ORC runtime artifacts (required)\n.orc/\n"


def validate_workspace_gitignore(workdir: str) -> tuple[bool, str]:
    gitignore_path = Path(workdir) / ".gitignore"
    if not gitignore_path.exists():
        return False, _build_error_message(str(gitignore_path))
    content = gitignore_path.read_text(encoding="utf-8", errors="replace")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line in REQUIRED_ORC_IGNORE_RULES:
            return True, ""
    return False, _build_error_message(str(gitignore_path))


def _build_error_message(gitignore_path: str) -> str:
    return (
        f"Неверный .gitignore: отсутствует правило игнора ORC runtime artifacts ({gitignore_path}).\n"
        "Добавьте в .gitignore блок ниже (copy-paste):\n"
        f"{REQUIRED_ORC_IGNORE_SNIPPET}"
    )
