#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Supervision bounded context: completion checks, lifecycle, outcomes.

Collects cross-cutting orchestration concerns that supervise worker tasks:
per-task completion checks, lifecycle waits for process exit, and the
thread-safe tracker for outcomes (completions, failures, arbitration).
"""
