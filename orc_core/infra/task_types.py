#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    task_id: str
    text: str
    done: bool
