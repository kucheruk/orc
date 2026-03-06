#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import tempfile
import unittest

from textual.app import App

from orc_core.tui.screens.role_settings import RoleSettingsModal


class _RoleSettingsTestApp(App[None]):
    def __init__(self, screen: RoleSettingsModal) -> None:
        super().__init__()
        self._screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._screen)


class RoleSettingsModalKeyboardNavigationTest(unittest.TestCase):
    def test_up_and_down_cycle_focus_between_role_controls(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            screen = RoleSettingsModal(workdir=tmpdir, models=["gpt-5.3-codex"])
            app = _RoleSettingsTestApp(screen)

            async def _run() -> None:
                async with app.run_test() as pilot:
                    first = screen.query_one("#role_model_pick_analysis_planning")
                    screen.set_focus(first)
                    await pilot.pause()

                    await pilot.press("down")
                    await pilot.pause()
                    self.assertEqual(app.focused.id, "role_prompt_edit_analysis_planning")

                    await pilot.press("up")
                    await pilot.pause()
                    self.assertEqual(app.focused.id, "role_model_pick_analysis_planning")

            asyncio.run(_run())

    def test_modal_shows_only_sdlc_plus_coder_roles(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            screen = RoleSettingsModal(workdir=tmpdir, models=["gpt-5.3-codex"])
            app = _RoleSettingsTestApp(screen)

            async def _run() -> None:
                async with app.run_test() as pilot:
                    await pilot.pause()
                    self.assertIsNotNone(screen.query_one("#role_row_analysis_planning"))
                    self.assertIsNotNone(screen.query_one("#role_row_design"))
                    self.assertIsNotNone(screen.query_one("#role_row_coder"))
                    self.assertIsNotNone(screen.query_one("#role_row_code_review"))
                    self.assertIsNotNone(screen.query_one("#role_row_tester"))
                    self.assertIsNotNone(screen.query_one("#role_row_handoff"))
                    self.assertEqual(len(screen.query("#role_row_supervisor")), 0)
                    self.assertEqual(len(screen.query("#role_row_merge_expert")), 0)

            asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
