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


_SESSION_STOP_EVENTS: dict[str, threading.Event] = {}
_SESSION_LOCK = threading.Lock()


def request_session_stop(session_id: str) -> None:
    with _SESSION_LOCK:
        _SESSION_STOP_EVENTS.setdefault(session_id, threading.Event()).set()


def is_session_stop_requested(session_id: str) -> bool:
    with _SESSION_LOCK:
        ev = _SESSION_STOP_EVENTS.get(session_id)
    return ev.is_set() if ev else False


def clear_session_stop(session_id: str) -> None:
    with _SESSION_LOCK:
        ev = _SESSION_STOP_EVENTS.get(session_id)
    if ev:
        ev.clear()


def clear_all_session_stops() -> None:
    with _SESSION_LOCK:
        for ev in _SESSION_STOP_EVENTS.values():
            ev.clear()
        _SESSION_STOP_EVENTS.clear()
