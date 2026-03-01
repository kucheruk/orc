#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# Safety default for test runs: never send real Telegram notifications.
os.environ.setdefault("ORC_TELEGRAM_DISABLE", "1")
