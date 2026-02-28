#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import shutil


class AgentNotInstalledError(RuntimeError):
    pass


def ensure_agent_installed() -> None:
    if shutil.which("agent"):
        return
    raise AgentNotInstalledError(
        "❌ agent не найден в PATH.\n"
        "Install Cursor CLI: https://cursor.com/docs/cli/introduction\n"
        "Проверьте установку командой: agent --version"
    )
