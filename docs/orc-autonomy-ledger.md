# ORC Autonomy Ledger

## Final Objective

ORC operates as an autonomous delivery system with:
- reliable card flow,
- zero false `Done` states,
- deterministic recovery from common failures,
- minimal operator intervention.

## Current Status

- Date: 2026-04-16
- ORC state (running/stopped): stopped (preparing relaunch)
- Target repository: `/Users/vetinary/work/jeeves`
- Active blockers: none (all critical issues addressed)

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
- Symptom: fresh `orc --workspace` launch exited with `Another orchestrator instance is running`.
- Impact: hidden process mutating board/worktree without operator control.
- Root cause: previous ORC process survived detached (`ppid=1`).
- Fix (code): deterministic stale-session handling via lockfile PID check + `os.killpg()` in `process.py:51-58`. Orphan sweep via token/CWD matching in `process.py:165-277`.
- Verification: lockfile guard tested; orphan sweep exercises multiple matching strategies.
- Regression test added: yes (process group tests in test suite).
- Residual risk: low — deterministic guards cover shell-death scenario.
- **Status: RESOLVED**

### 2026-04-16T08:30:00Z - High-CPU churn loop, low delivery

- Timestamp: 2026-04-16 08:30 local
- Symptom: ~7.5h at ~99% CPU, 44/66 commits were board-sync churn.
- Impact: token burn without code delivery.
- Root cause: board-sync throttle existed but the deeper issue was `has_commits_ahead_of_branch` counted card-only commits as "real delivery". Cards progressed through entire pipeline (Coding→Review→Done) with zero source code, only task/*.md changes.
- Fix (code): replaced delivery gate with `has_code_changes_ahead()` — checks `git diff --name-only branch..HEAD -- . ':!tasks/'`. Applied in both worker.py (delivery-role guard) and IntegrationManager._has_commits (finalize gate).
- Verification: 474 tests pass. Board audit confirmed 3/8 cards were false progress (UX-001 false Done, PLAT-004/EXTR-001 false Review). Remediated cards back to Coding.
- Regression test added: yes — `HasCodeChangesAheadTest` (5 cases), `test_has_commits_fails_when_only_card_changes` in integration manager.
- Residual risk: agents must still actually write code; gate prevents false completion but can't force code production.
- **Status: RESOLVED**

### 2026-04-16T11:00:00Z - False Done / false progression (3 cards)

- Timestamp: 2026-04-16 11:00 local
- Symptom: UX-001 in Done with zero code on master. PLAT-004/EXTR-001 in Review with zero branch commits.
- Impact: board showed false progress; 3 cards consumed pipeline time without delivering code.
- Root cause: same as churn incident — `has_commits_ahead_of_branch` passed on card-file-only commits.
- Fix (code/board): code gate via `has_code_changes_ahead`. Board remediated: UX-001, PLAT-004, EXTR-001 moved back to 4_Coding.
- Verification: board state corrected; new gate prevents recurrence.
- Regression test added: yes (same tests as churn fix).
- Residual risk: none for this failure mode.
- **Status: RESOLVED**

## Known Failure Signatures

- false done without integration: observed 2026-04-16 (UX-001). **Fixed**: `has_code_changes_ahead` gate.
- cherry-pick conflict loop: not observed recently.
- circular dependency deadlock: not observed recently.
- stale assignment/worktree orphan: observed 2026-04-15. **Fixed**: lockfile + orphan sweep.
- token burn without merge progress: observed 2026-04-16. **Fixed**: code-changes gate prevents card-only cycling.

## Active Hypotheses

- hypothesis: with `has_code_changes_ahead` gate, ORC will fail fast on card-only agent runs and retry with clearer escalation signal.
- expected signal: no cards in Review/Done without corresponding src/ changes in worktree branch.
- validation plan: launch ORC, monitor first 2 cycles for delivery vs churn ratio.

## Next Intervention Queue

- [x] add deterministic regression test for detached orchestrator detection/ownership handoff
- [x] add deterministic no-progress guard for card-only commit cycles
- [x] verify all `8_Done` cards map to integrated code on `master` (done: audit found 3 false, remediated)
- [ ] monitor two additional control cycles for flow/integration signal
- [ ] evaluate whether reviewer/tester roles also need code-change gates (currently only delivery roles checked)

## Autonomy Readiness Checklist

- [ ] Done always equals integrated, working code. *(gate shipped, needs runtime validation)*
- [ ] Cycles/deadlocks resolved by ORC playbooks.
- [ ] No unrecoverable branch/worktree information loss.
- [ ] Monitoring and periodic reports stable.
- [ ] At least 3 uninterrupted healthy control cycles.
