#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import unittest
from unittest.mock import MagicMock

from textual.app import App

from orc_core.tui.screens.post_mortem import PostMortemScreen


class _PostMortemTestApp(App[None]):
    def __init__(self, screen: PostMortemScreen) -> None:
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


class PostMortemScreenTest(unittest.TestCase):
    def test_screen_renders_banner_and_logs(self) -> None:
        screen = PostMortemScreen(
            task_id="TASK-1",
            exit_code=1,
            failure_reason="max_restarts_exceeded",
            reasoning_lines=["check hooks", "retry loop exhausted"],
            recent_events=["result:error", "agent:stalled"],
            debug_log_path="/tmp/orc/orc-debug-1.jsonl",
        )
        app = _PostMortemTestApp(screen)

        async def _run() -> None:
            async with app.run_test() as pilot:
                _ = pilot
                banner = screen.query_one("#postmortem_banner")
                details = screen.query_one("#postmortem_details")
                reasoning = screen.query_one("#postmortem_reasoning")
                events = screen.query_one("#postmortem_events")
                self.assertIn("max_restarts_exceeded", str(banner.render()))
                self.assertIn("TASK-1", str(details.render()))
                self.assertIn("/tmp/orc/orc-debug-1.jsonl", str(details.render()))
                self.assertGreaterEqual(len(reasoning.lines), 1)
                self.assertGreaterEqual(len(events.lines), 1)

        asyncio.run(_run())

    def test_escape_exits_app_with_failure_code(self) -> None:
        screen = PostMortemScreen(
            task_id="TASK-2",
            exit_code=1,
            failure_reason="commit_phase_failed",
            reasoning_lines=["commit started"],
            recent_events=["commit:failed"],
        )
        app = _PostMortemTestApp(screen)
        app.exit = MagicMock()

        async def _run() -> None:
            async with app.run_test() as pilot:
                await pilot.press("escape")
                await pilot.pause()

        asyncio.run(_run())
        app.exit.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
