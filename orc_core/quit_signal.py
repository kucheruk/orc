#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

_STOP_EVENT = threading.Event()
_QUIT_AFTER_TASK_EVENT = threading.Event()


def clear_stop_request() -> None:
    _STOP_EVENT.clear()
    _QUIT_AFTER_TASK_EVENT.clear()


def request_stop() -> None:
    _STOP_EVENT.set()


def is_stop_requested() -> bool:
    return _STOP_EVENT.is_set()


def request_quit_after_task() -> None:
    _QUIT_AFTER_TASK_EVENT.set()


def toggle_quit_after_task() -> bool:
    if _QUIT_AFTER_TASK_EVENT.is_set():
        _QUIT_AFTER_TASK_EVENT.clear()
        return False
    _QUIT_AFTER_TASK_EVENT.set()
    return True


def is_quit_after_task_requested() -> bool:
    return _QUIT_AFTER_TASK_EVENT.is_set()
