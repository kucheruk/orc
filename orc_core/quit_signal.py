#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading

_STOP_EVENT = threading.Event()


def clear_stop_request() -> None:
    _STOP_EVENT.clear()


def request_stop() -> None:
    _STOP_EVENT.set()


def is_stop_requested() -> bool:
    return _STOP_EVENT.is_set()
