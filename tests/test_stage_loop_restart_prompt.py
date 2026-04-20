#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: restart path must never feed the agent an empty prompt.

request_builder hard-codes templates.continue_template="". Before the fix,
the restart block still called continue_template.format_map(...) and wrote
the empty result to disk as the new prompt_path. The next agent invocation
read that empty file and exited with "No prompt provided for print mode".
Each such crash counted against max_restarts, eventually flipping the card
to Blocked for a reason that was entirely internal to ORC (started by any
transient ECONNRESET/TLS hiccup from cursor-agent).

The fix leaves prompt_path alone when continue_template is empty so the
retry re-runs the original coder/reviewer/etc. prompt verbatim.
"""

import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from orc_core.tasks.execution.stage_loop import prepare_stages


def _load_restart_block_source() -> str:
    src_path = Path(__file__).resolve().parents[1] / "orc_core/tasks/execution/stage_loop.py"
    return src_path.read_text(encoding="utf-8")


class TestRestartPreservesOriginalPromptPath(unittest.TestCase):
    def test_restart_block_guards_empty_continue_template(self):
        """The restart branch must check that continue_template is non-empty
        before overwriting prompt_path — otherwise an empty prompt file is
        fed to the agent on every retry."""
        src = _load_restart_block_source()
        # Anchor on "restarting task" log followed by the guard.
        # The guard looks like: if (request.templates.continue_template or "").strip():
        pattern = re.compile(
            r'log_event\([^\n]*"restarting task".*?'
            r'if\s*\(?\s*request\.templates\.continue_template[^\n]*\)?\s*\.strip\(\)\s*:',
            re.DOTALL,
        )
        self.assertRegex(src, pattern,
                         "stage_loop must gate continue_template.format_map on a non-empty template")

    def test_empty_branch_clears_resume_prompt_and_keeps_prompt_path(self):
        src = _load_restart_block_source()
        # The else branch exists and leaves prompt_path untouched.
        self.assertIn("resume_prompt_text = None", src,
                      "empty-template branch should null out resume_prompt_text "
                      "so build_agent_cmd treats it as 'no resume nudge' and the "
                      "original prompt_path is read verbatim")


class TestPrepareStagesStillMarksAutoWrappedPreRendered(unittest.TestCase):
    """Co-regression: the double-format fix must still hold."""

    def test_empty_stage_specs_produces_pre_rendered_wrapper(self):
        ctx = SimpleNamespace()
        ctx.request = SimpleNamespace(
            stage_specs=(),
            models=SimpleNamespace(model="m"),
            templates=SimpleNamespace(prompt_template="hi {leftover.attr}"),
            workdir="/tmp/x",
            enforce_stage_artifacts=False,
        )
        ctx.task_id = "T"
        import orc_core.tasks.execution.stage_loop as sl

        class _B:
            def to_prompt_vars(self):
                return {}

        real = sl.build_stage_artifact_bundle
        sl.build_stage_artifact_bundle = lambda workdir, task_id: _B()
        try:
            prepare_stages(ctx)
        finally:
            sl.build_stage_artifact_bundle = real
        self.assertTrue(ctx.stage_specs[0].is_pre_rendered)


if __name__ == "__main__":
    unittest.main()
