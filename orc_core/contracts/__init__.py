#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-cutting DTOs shared between orc_core layers.

Rule: `contracts/` must not import from any `orc_core.*` module.
Only stdlib / third-party types allowed. This keeps the package acyclic
and lets any layer depend on it without pulling in peers.
"""
