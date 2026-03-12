#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

def validate_workspace_gitignore(workdir: str) -> tuple[bool, str]:
    _ = Path(workdir)
    return True, ""
