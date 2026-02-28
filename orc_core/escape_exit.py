#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import select
import sys
import termios
import tty
from dataclasses import dataclass
from typing import Optional
from prompt_toolkit.shortcuts import yes_no_dialog


@dataclass
class _TerminalState:
    attrs: list[int]
    blocking: bool


class EscapeExitWatcher:
    """
    Non-blocking ESC watcher for interactive TTY sessions.
    """

    def __init__(self) -> None:
        self._fd: Optional[int] = None
        self._state: Optional[_TerminalState] = None

    def __enter__(self) -> "EscapeExitWatcher":
        if not sys.stdin.isatty():
            return self
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            blocking = os.get_blocking(fd)
            tty.setcbreak(fd)
            os.set_blocking(fd, False)
        except Exception:
            self._fd = None
            self._state = None
            return self
        self._fd = fd
        self._state = _TerminalState(attrs=attrs, blocking=blocking)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._restore_terminal()

    def is_enabled(self) -> bool:
        return self._fd is not None and self._state is not None

    def poll_escape(self) -> bool:
        if self._fd is None:
            return False
        try:
            ready, _, _ = select.select([self._fd], [], [], 0.0)
            if not ready:
                return False
            chunk = os.read(self._fd, 64)
        except Exception:
            return False
        if not chunk:
            return False
        return b"\x1b" in chunk

    def confirm_exit(self) -> bool:
        if not self.is_enabled():
            return False
        self._restore_terminal()
        try:
            confirmed = bool(
                yes_no_dialog(
                    title="Подтверждение выхода",
                    text="Остановить ORC и выйти из приложения?",
                ).run()
            )
        finally:
            self._enable_terminal()
        return confirmed

    def _restore_terminal(self) -> None:
        if self._fd is None or self._state is None:
            return
        try:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._state.attrs)
            os.set_blocking(self._fd, self._state.blocking)
        except Exception:
            pass

    def _enable_terminal(self) -> None:
        if self._fd is None or self._state is None:
            return
        try:
            tty.setcbreak(self._fd)
            os.set_blocking(self._fd, False)
        except Exception:
            pass
