#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orc_core.hooks import ensure_repo_hooks, write_task_file
from orc_core.state_paths import artifacts_dir
from orc_core.task_source import Task


class PreToolUsePermissionsTest(unittest.TestCase):
    def _prepare_workspace(self, tmpdir: Path) -> tuple[Path, Path]:
        backlog = tmpdir / "BACKLOG.md"
        backlog.write_text("- [ ] TASK-001 test task\n", encoding="utf-8")
        log_path = tmpdir / ".orc" / "orc.log"
        before_path, _stop_path = ensure_repo_hooks(str(tmpdir))
        pre_tool_use_path = before_path.parent / "orc_pre_tool_use.py"
        task_path = write_task_file(
            str(tmpdir),
            Task(task_id="TASK-001", text="test task", done=False),
            backlog,
            log_path,
        )
        return pre_tool_use_path, task_path

    def _set_stage(self, task_path: Path, stage_id: str) -> None:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
        payload["sdlc_stage_id"] = stage_id
        task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _run_hook(self, script_path: Path, workspace: Path, task_path: Path, payload: dict) -> dict:
        env = os.environ.copy()
        env["ORC_BASE_WORKSPACE"] = str(workspace)
        env["ORC_TASK_FILE"] = str(task_path)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=workspace,
            env=env,
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(result.stdout.strip(), msg="Expected JSON response from preToolUse hook")
        return json.loads(result.stdout)

    def test_planning_denies_edit_outside_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            script_path, task_path = self._prepare_workspace(tmpdir)
            self._set_stage(task_path, "planning")
            src_path = tmpdir / "src" / "app.py"
            src_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(src_path)},
                "cwd": str(tmpdir),
                "workspace_roots": [str(tmpdir)],
            }
            response = self._run_hook(script_path, tmpdir, task_path, payload)
            self.assertEqual(response.get("decision"), "deny")

    def test_review_allows_artifact_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            script_path, task_path = self._prepare_workspace(tmpdir)
            self._set_stage(task_path, "review")
            artifact_path = artifacts_dir(str(tmpdir)) / "TASK-001_review.md"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(artifact_path)},
                "cwd": str(tmpdir),
                "workspace_roots": [str(tmpdir)],
            }
            response = self._run_hook(script_path, tmpdir, task_path, payload)
            self.assertEqual(response.get("decision"), "allow")

    def test_implementation_allows_source_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir_str:
            tmpdir = Path(tmpdir_str)
            script_path, task_path = self._prepare_workspace(tmpdir)
            self._set_stage(task_path, "implementation")
            src_path = tmpdir / "src" / "app.py"
            src_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "tool_name": "Edit",
                "tool_input": {"file_path": str(src_path)},
                "cwd": str(tmpdir),
                "workspace_roots": [str(tmpdir)],
            }
            response = self._run_hook(script_path, tmpdir, task_path, payload)
            self.assertEqual(response.get("decision"), "allow")


if __name__ == "__main__":
    unittest.main()
