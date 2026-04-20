#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pin TOOL_DIGESTION_GRACE_SECONDS high enough for real project test suites.

The previous 180s allowance fired a stall mid-`dotnet test Jeeves.sln` on
the Jeeves solution (a typical multi-project .NET repo where the full
test run takes 4–5 minutes). Each stall counted against max_restarts and
parked EXTR-003-C in Blocked for a reason that was purely a watchdog
misconfiguration.

This test is a boundary guard: if someone drops this value back to the
old aggressive default, the stall feedback loop returns.
"""

import unittest

from orc_core.tasks.completion.checks import TOOL_DIGESTION_GRACE_SECONDS


class TestToolDigestionGrace(unittest.TestCase):
    def test_grace_is_generous_enough_for_real_test_suites(self):
        # A .NET/Gradle/pytest full suite can take 5+ minutes wall time.
        self.assertGreaterEqual(TOOL_DIGESTION_GRACE_SECONDS, 600.0)

    def test_grace_is_not_absurd(self):
        # Keep it bounded so genuine hangs still surface eventually.
        self.assertLessEqual(TOOL_DIGESTION_GRACE_SECONDS, 1800.0)


if __name__ == "__main__":
    unittest.main()
