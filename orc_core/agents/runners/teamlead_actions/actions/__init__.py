#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Action handlers: importing this package registers every handler.

Each submodule defines one ActionHandler class decorated with
``@register_action``. Listing them here forces import so the decorators
run before the dispatcher resolves an action type.
"""

from __future__ import annotations

from . import (  # noqa: F401
    create,
    deps,
    feedback,
    move,
    notify,
    respond,
    set_action,
    skip,
    update,
    wip,
)
