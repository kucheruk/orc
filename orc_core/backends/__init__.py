#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backend registry and implementations (cursor, claude, codex)."""

from .backend import Backend, SUPPORTED_BACKENDS, get_backend

__all__ = ["Backend", "SUPPORTED_BACKENDS", "get_backend"]
