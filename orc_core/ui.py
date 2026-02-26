#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from rich.console import Console

_CONSOLE = Console()


def ui_console() -> Console:
    return _CONSOLE


def ui_info(message: str) -> None:
    _CONSOLE.print(f"[cyan]{message}[/cyan]")


def ui_warn(message: str) -> None:
    _CONSOLE.print(f"[yellow]{message}[/yellow]")


def ui_error(message: str) -> None:
    _CONSOLE.print(f"[bold red]{message}[/bold red]")
