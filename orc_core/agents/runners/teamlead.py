#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Teamlead runner: thin loop coordinator that delegates to TeamleadStep strategies."""

from __future__ import annotations

import logging
import threading
import traceback
from pathlib import Path
from typing import Optional

from ...incident.manager import IncidentManager
from ...tasks.completion.outcomes import TaskOutcomeTracker
from ..kanban_protocols import (
    DirectiveSource, EventPublisher, RunnerLifecycle, RunnerNotifier,
    RunnerStateManager, TaskExecutor, WorkDistributor,
)
from ...log import log_event
from ...quit_signal import is_quit_after_task_requested
from ..session_types import SessionSlot, SlotStatus
from ...incident.domain import Incident
from ..teamlead_steps import (
    ArbitrationStep, AutoCommitStep, DirectiveStep, HealthCheckStep, TeamleadContext,
)

_logger = logging.getLogger(__name__)


class KanbanTeamleadRunner:
    """Runs the teamlead loop: directives, incidents, health checks, arbitration."""

    def __init__(
        self,
        *,
        workdir: str,
        log_path: Path,
        engine: TaskExecutor,
        distributor: WorkDistributor,
        publisher: EventPublisher,
        incident_mgr: IncidentManager,
        slots_lock: threading.Lock,
        outcomes: TaskOutcomeTracker,
        lifecycle: RunnerLifecycle,
        notifier: RunnerNotifier,
        state_manager: RunnerStateManager,
        directives: DirectiveSource,
    ) -> None:
        self._ctx = TeamleadContext(
            workdir=workdir,
            log_path=log_path,
            engine=engine,
            distributor=distributor,
            publisher=publisher,
            lifecycle=lifecycle,
            notifier=notifier,
            state_manager=state_manager,
            outcomes=outcomes,
        )
        self._incident_mgr = incident_mgr
        self._slots_lock = slots_lock
        self._directives = directives

        self._arbitration = ArbitrationStep()
        self._directive_step = DirectiveStep()
        self._health = HealthCheckStep()
        self._auto_commit = AutoCommitStep()

    def run(self, slot: SessionSlot) -> None:
        sid = slot.session_id
        self._ctx.publisher.emit("system", "", f"{sid} teamlead started, monitoring board...")
        incident: Optional[Incident] = None
        try:
            while self._ctx.lifecycle.should_continue(slot):
                self._ctx.distributor.refresh()
                self._ctx.distributor.board._apply_deferred_moves()

                if incident is not None:
                    incident = self._incident_mgr.process_incident(slot, incident)
                    if incident is None:
                        self._ctx.publisher.emit("incident", "",
                                                 "Incident resolved, resuming normal operations")
                    self._ctx.lifecycle.sleep(2.0)
                    if is_quit_after_task_requested():
                        self._ctx.publisher.emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                        break
                    continue

                directive = self._directives.pop_directive()
                if directive:
                    self._directive_step.run_with_text(self._ctx, slot, sid, directive)
                    continue

                anomaly = self._incident_mgr.detect_anomaly()
                if anomaly is not None:
                    incident = anomaly
                    self._ctx.publisher.log_incident(
                        incident.id,
                        f"{incident.error_type} on {incident.source_task_id or incident.source_slot_id}: "
                        f"{incident.error_message[:200]}",
                    )
                    log_event(self._ctx.log_path, "WARN", "incident detected",
                              incident_id=incident.id, error_type=incident.error_type,
                              source_task=incident.source_task_id, source_slot=incident.source_slot_id)
                    continue

                if self._health.due():
                    if self._health.run(self._ctx, slot, sid):
                        continue

                self._arbitration.run(self._ctx, slot, sid)
                self._auto_commit.run(self._ctx)

                if not self._ctx.distributor.has_remaining_work():
                    self._ctx.publisher.emit("system", "", f"{sid} teamlead: no remaining work")
                    break
                self._ctx.lifecycle.sleep(5.0)
                if is_quit_after_task_requested():
                    self._ctx.publisher.emit("system", "", f"{sid} teamlead exiting (quit-after-task)")
                    break
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            slot.mark_crashed(exc, traceback.format_exc())
            log_event(self._ctx.log_path, "ERROR", "teamlead crashed",
                      session_id=sid, error=str(exc),
                      traceback=traceback.format_exc()[:2000])
        finally:
            with self._slots_lock:
                slot.status = SlotStatus.CLOSED
