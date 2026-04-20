#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: pre-rendered prompts must not be re-formatted by stage_loop.

When a caller (teamlead/worker/incident triage) passes an already-rendered
prompt into make_request, stage_loop wraps it in a default-single-stage
spec. Running format_map on that wrapped string a second time caused any
surviving `{...}` pattern inside substituted card/traceback content to be
re-interpreted as a format placeholder, crashing the stage.

Observed in production: a worker_crash traceback that included the source
code line `raise RuntimeError(f"failed to remove worktree: {stderr.strip()}...")`
killed teamlead triage with "'str' object has no attribute 'strip()'".
"""

import unittest

from orc_core.tasks.execution.stage import TaskStageSpec


class TestStageSpecPreRendered(unittest.TestCase):
    def test_is_pre_rendered_defaults_false(self):
        spec = TaskStageSpec(stage_id="x", model="m", prompt_template="t")
        self.assertFalse(spec.is_pre_rendered)

    def test_can_flag_pre_rendered(self):
        spec = TaskStageSpec(stage_id="x", model="m", prompt_template="t", is_pre_rendered=True)
        self.assertTrue(spec.is_pre_rendered)


class TestPrepareStagesMarksAutoWrappedAsPreRendered(unittest.TestCase):
    """The auto-generated wrapper stage must carry is_pre_rendered=True
    so run_stage_loop skips format_map, which would otherwise re-parse
    any leftover {...} in the already-substituted caller content."""

    def test_empty_stage_specs_produces_pre_rendered_wrapper(self):
        from types import SimpleNamespace
        from orc_core.tasks.execution.stage_loop import prepare_stages

        ctx = SimpleNamespace()
        ctx.request = SimpleNamespace(
            stage_specs=(),
            models=SimpleNamespace(model="model-x"),
            templates=SimpleNamespace(
                prompt_template="already rendered: {stderr.strip()} {doc.Prop}"
            ),
            workdir="/tmp/no-such",
            enforce_stage_artifacts=False,
        )
        ctx.task_id = "T-1"

        # build_stage_artifact_bundle needs a real-ish workdir shape — the
        # prepare_stages call chain will hit it. Patch it out for this unit
        # test so we isolate the stage-spec wiring.
        import orc_core.tasks.execution.stage_loop as sl

        class _FakeBundle:
            def to_prompt_vars(self):
                return {}

        real = sl.build_stage_artifact_bundle
        sl.build_stage_artifact_bundle = lambda workdir, task_id: _FakeBundle()
        try:
            prepare_stages(ctx)
        finally:
            sl.build_stage_artifact_bundle = real

        self.assertEqual(len(ctx.stage_specs), 1)
        wrapper = ctx.stage_specs[0]
        self.assertTrue(wrapper.is_pre_rendered,
                        "Auto-wrapped default stage must be marked pre-rendered "
                        "so {stderr.strip()}-like leftovers are not re-parsed")
        self.assertEqual(wrapper.stage_id, "implementation")
        self.assertEqual(wrapper.prompt_template,
                         "already rendered: {stderr.strip()} {doc.Prop}")


if __name__ == "__main__":
    unittest.main()
