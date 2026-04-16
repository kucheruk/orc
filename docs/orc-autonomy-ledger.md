# ORC Autonomy Ledger

## Final Objective

ORC operates as an autonomous delivery system with:
- reliable card flow,
- zero false `Done` states,
- deterministic recovery from common failures,
- minimal operator intervention.

## Current Status

- Date: 2026-04-16
- ORC state (running/stopped): stopped (contained)
- Target repository: `/Users/vetinary/work/jeeves`
- Active blockers:
  - orphan ORC process from previous run could continue unsupervised (`ppid=1`)
- token burn with low delivery: heavy board churn, weak code/output ratio
- long-running high-CPU orchestrator loop without proportional rightward flow

## Incident Log

### Incident Template

- Timestamp:
- Symptom:
- Impact:
- Root cause:
- Fix (code/prompt/both):
- Verification:
- Regression test added:
- Residual risk:

---

### 2026-04-15T20:53:00Z - Orphan orchestrator process

- Timestamp: 2026-04-15 20:53 UTC
- Symptom: fresh `orc --workspace /Users/vetinary/work/jeeves` launch exited with `Another orchestrator instance is running` while no tracked terminal owned a healthy instance.
- Impact: violated process-control invariant; hidden process could keep mutating board/worktree without active operator control.
- Root cause: previous ORC process survived detached (`pid=78531`, `ppid=1`), likely after shell/terminal lifecycle mismatch.
- Fix (code/prompt/both): operational containment this cycle (captured evidence, terminated orphan process, relaunched ORC under tracked terminal session). In parallel, continue hardening deterministic stale-session handling already in ORC runtime changes.
- Verification:
  - orphan process detected via `ps` and confirmed detached (`ppid=1`);
  - process terminated (`kill -9 78531`, then `ps -p 78531` empty);
  - ORC relaunched successfully and remained running in controlled session.
- Regression test added: pending (needs deterministic test around stale orchestrator/session ownership).
- Residual risk: if parent shell dies unexpectedly again, orphan can recur until deterministic owner/lease guard is enforced end-to-end.

### 2026-04-16T08:30:00Z - High-CPU churn loop, low delivery

- Timestamp: 2026-04-16 08:30 local
- Symptom: orchestrator process ran ~7.5h at ~99% CPU with large commit churn and limited net delivery.
- Impact: poor overnight throughput; substantial token/process spend with mostly board-state activity.
- Root cause: unresolved control-loop inefficiency (frequent board-sync churn, weak gating on "real progress" before repeated loop actions).
- Fix (code/prompt/both): operational containment for now (stopped active process to prevent further churn) + queued deterministic hardening.
- Verification:
  - process metrics showed sustained ~99% CPU (`ps` on active ORC PID);
  - overnight commits: 66 total, 44 were `chore: sync board state...`;
  - average sync-churn cadence ~2.27 minutes;
  - board remained top-heavy (`2_Estimate` still dominant) with low rightward conversion.
- Regression test added: pending (needs deterministic guard against high-frequency no-progress control loop).
- Residual risk: rerun without guardrails may reproduce the same churn pattern.

## Known Failure Signatures

- false done without integration:
- cherry-pick conflict loop:
- circular dependency deadlock:
- stale assignment/worktree orphan: observed 2026-04-15 (detached ORC process with `ppid=1`)
- token burn without merge progress:
- token burn without merge progress: observed 2026-04-16 (7h+ high-CPU loop; sync-commit dominant)

## Active Hypotheses

- hypothesis: stronger deterministic stale-session reclamation in teamlead/autounblock path reduces orphan/stall loops without manual kill/restart.
- expected signal: ORC can restart cleanly after interruption, auto-release stale worker state, and continue without `Another orchestrator instance is running`.
- validation plan: relaunch only after adding no-progress loop guards; then monitor commit mix, stage deltas, and CPU/runtime profile across at least 2 cycles.

## Next Intervention Queue

- [ ] add deterministic regression test for detached orchestrator detection/ownership handoff
- [ ] add deterministic no-progress guard (throttle/abort) for high-frequency board-sync churn loops
- [ ] verify all `8_Done` cards map to integrated code on `master` in target repo (no board-only completion)
- [ ] monitor two additional control cycles for flow/integration signal before declaring improvement

## Autonomy Readiness Checklist

- [ ] Done always equals integrated, working code.
- [ ] Cycles/deadlocks resolved by ORC playbooks.
- [ ] No unrecoverable branch/worktree information loss.
- [ ] Monitoring and periodic reports stable.
- [ ] At least 3 uninterrupted healthy control cycles.
