#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import unittest
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from orc_core.agents.runners.worker import KanbanWorkerRunner
from orc_core.agents.session.types import SessionSlot, SlotStatus
from orc_core.board.kanban_pull import WorkAssignment
from orc_core.git.git_dto import WorktreeSession
from orc_core.tasks.execution.request import TaskExecutionResult
from orc_core.tasks.status import TaskExecutionStatus


def _build_git_mock() -> MagicMock:
    git = MagicMock()
    git.run_with_log.return_value = (False, "", "", 1)
    git.run.return_value = (False, "", "", 1)
    git.status_porcelain.return_value = (True, "")
    git.parse_porcelain.return_value = ([], [])
    return git


class WorkerRunnerCommitGuardTest(unittest.TestCase):
    def _build_runner(self) -> KanbanWorkerRunner:
        distributor = MagicMock()
        distributor.board = MagicMock()
        publisher = MagicMock()
        outcomes = MagicMock()
        outcomes.increment_fail_count.return_value = 1
        state_manager = MagicMock()
        state_manager.make_request.return_value = MagicMock()
        engine = MagicMock()
        engine.execute.return_value = TaskExecutionResult(
            status=TaskExecutionStatus.COMPLETED,
            agent_result_file="/tmp/result.json",
            agent_run_id="TASK-1:4_Coding:attempt-1",
        )
        return KanbanWorkerRunner(
            workdir="/tmp/base",
            log_path=Path("/tmp/orc.log"),
            engine=engine,
            distributor=distributor,
            publisher=publisher,
            config=Namespace(commit_phase=True),
            main_branch="main",
            slots_lock=threading.Lock(),
            worktree_lock=threading.Lock(),
            outcomes=outcomes,
            lifecycle=MagicMock(),
            notifier=MagicMock(),
            state_manager=state_manager,
            integrator=MagicMock(),
            git_integration=_build_git_mock(),
        )

    @patch("orc_core.agents.runners.worker_assignment.check_and_block_budget", return_value=False)
    @patch("orc_core.agents.runners.worker_assignment.update_card_token_budget")
    @patch("orc_core.agents.runners.worker_assignment.accumulate_card_tokens")
    @patch("orc_core.agents.runners.worker_assignment.has_commits_ahead_of_branch", return_value=False)
    @patch("orc_core.agents.runners.worker_assignment.has_code_changes_ahead", return_value=False)
    @patch("orc_core.agents.runners.worker.build_prompt", return_value="prompt")
    @patch("orc_core.agents.runners.worker_assignment.create_task_worktree")
    @patch("orc_core.agents.runners.worker_assignment.process_completed_task")
    @patch("orc_core.agents.runners.worker_assignment.handle_task_failure")
    def test_delivery_role_without_commits_does_not_process_result(
        self,
        handle_failure_mock,
        process_completed_mock,
        create_worktree_mock,
        _build_prompt_mock,
        _code_changes_mock,
        _ahead_mock,
        *_budget_mocks,
    ) -> None:
        create_worktree_mock.return_value = WorktreeSession(
            base_workdir="/tmp/base",
            worktree_path="/tmp/base/.worktrees/TASK-1",
            branch_name="orc/TASK-1",
            task_id="TASK-1",
            reused=True,
        )
        runner = self._build_runner()
        slot = SessionSlot(session_id="s1", status=SlotStatus.RUNNING)
        card = MagicMock()
        card.id = "TASK-1"
        card.title = "Task title"
        card.stage = "4_Coding"
        card.action = "Coding"
        card.state_version = 3
        card.file_path = Path("/tmp/base/tasks/4_Coding/TASK-1.md")
        runner._distributor.board.card_by_id.side_effect = [card, card]
        assignment = WorkAssignment(card=card, role="coder", needs_worktree=True)

        runner.execute_assignment(slot, assignment)

        handle_failure_mock.assert_called_once()
        process_completed_mock.assert_not_called()
        runner._outcomes.reset_fail_count.assert_not_called()

    @patch("orc_core.agents.runners.worker_assignment.check_and_block_budget", return_value=False)
    @patch("orc_core.agents.runners.worker_assignment.update_card_token_budget")
    @patch("orc_core.agents.runners.worker_assignment.accumulate_card_tokens")
    @patch("orc_core.agents.runners.worker_assignment.has_code_changes_ahead")
    @patch("orc_core.agents.runners.worker.build_prompt", return_value="prompt")
    @patch("orc_core.agents.runners.worker_assignment.create_task_worktree")
    @patch("orc_core.agents.runners.worker_assignment.process_completed_task")
    def test_stale_result_is_discarded_after_card_state_changes(
        self,
        process_completed_mock,
        create_worktree_mock,
        _build_prompt_mock,
        code_changes_mock,
        *_budget_mocks,
    ) -> None:
        create_worktree_mock.return_value = WorktreeSession(
            base_workdir="/tmp/base",
            worktree_path="/tmp/base/.worktrees/TASK-1",
            branch_name="orc/TASK-1",
            task_id="TASK-1",
            reused=True,
        )
        runner = self._build_runner()
        slot = SessionSlot(session_id="s1", status=SlotStatus.RUNNING)
        fresh_card = SimpleNamespace(
            id="TASK-1",
            title="Task title",
            stage="4_Coding",
            action="Coding",
            state_version=2,
            file_path=Path("/tmp/base/tasks/4_Coding/TASK-1.md"),
        )
        changed_card = SimpleNamespace(
            id="TASK-1",
            title="Task title",
            stage="5_Review",
            action="Arbitration",
            state_version=3,
            file_path=Path("/tmp/base/tasks/5_Review/TASK-1.md"),
        )
        runner._distributor.board.card_by_id.side_effect = [fresh_card, changed_card, changed_card]
        assignment = WorkAssignment(card=fresh_card, role="coder", needs_worktree=True)

        runner.execute_assignment(slot, assignment)

        process_completed_mock.assert_not_called()
        code_changes_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
