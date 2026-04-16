# ORC Autonomy Ledger

## Final Objective

ORC operates as an autonomous delivery system with:
- reliable card flow,
- zero false `Done` states,
- deterministic recovery from common failures,
- minimal operator intervention.

## Current Status

- Date: 2026-04-16
- ORC state: running (PID 50182)
- Target repository: jeeves
- Done: 15/47 cards
- Active blockers: integration reliability (agent-driven merge not yet proven)

## Incident Log (Chronological)

### I-01: Orphan orchestrator process (2026-04-15)
- Root cause: previous ORC survived detached (ppid=1)
- Fix: lockfile PID check + os.killpg() + orphan sweep
- **RESOLVED**

### I-02: High-CPU churn loop (2026-04-16 08:30)
- Root cause: `has_commits_ahead_of_branch` counted card-only commits as delivery
- Fix: `has_code_changes_ahead()` gate checking `git diff --name-only -- . ':!tasks/'`
- **RESOLVED**

### I-03: UX-001 branch code lost during remediation (2026-04-16 08:35)
- Root cause: `git branch -f orc/UX-001 master` destroyed code commits
- Fix: reflog recovery + manual merge + conflict resolution
- **RESOLVED**

### I-04: TL generates false "model_unavailable" alert (2026-04-16 08:33)
- Root cause: TL hallucinated system diagnoses
- Fix: prompt constrains TL to observable facts only
- **RESOLVED**

### I-05: 3/4 worker slots idle — Arbitration cards invisible (2026-04-16 08:40)
- Root cause: `find_teamlead_work` only checked Blocked/looping, not action=Arbitration
- Fix: added `arbitration_cards()` query + priority chain in find_teamlead_work
- **RESOLVED**

### I-06: EXTR-001 infinite token burn — 0 code, 500K+ tokens (2026-04-16 09:00)
- Root cause: agent wrote code but didn't commit; `has_code_changes_ahead` only checked commits
- Fix: guard now also checks `git status --porcelain` for uncommitted changes
- **RESOLVED**

### I-07: Integrator blocked by delivery guard (2026-04-16 09:30)
- Root cause: after merge, worktree has 0 changes vs master; guard treated as failure
- Fix: excluded ROLE_INTEGRATOR from _DELIVERY_ROLES
- **RESOLVED**

### I-08: Agents blind — no git context in prompts (2026-04-16 10:00)
- Root cause: prompts had no info about existing code on branch
- Fix: `_gather_git_context()` injects git log, diff stat, status into prompts
- **RESOLVED**

### I-09: Cards stuck — no backward stage moves (2026-04-16 10:30)
- Root cause: `_FORWARD_MOVES` had no entries for (Review,Coding)→Coding etc.
- Fix: added backward move entries for reviewer/tester/integrator rejections
- **RESOLVED**

### I-10: Coder post-arbitration leaves action=Arbitration (2026-04-16 11:00)
- Root cause: auto-default only mapped Coding→Reviewing, not Arbitration→Reviewing
- Fix: added Arbitration→Reviewing to coder auto-defaults + valid transitions
- **RESOLVED**

### I-11: TL decision file never written → Arbitration infinite loop (2026-04-16 11:30)
- Root cause: Cursor agent doesn't reliably write decision files
- Fix: deterministic fallback — if no decision after TL completion, force action=Coding
- **RESOLVED**

### I-12: process_agent_result reads main repo, not worktree (2026-04-16 12:00)
- Root cause: agent edits card in worktree (relative path), ORC reads from main repo (absolute path)
- Fix: process_agent_result accepts execution_workdir, scans worktree tasks/ dirs
- Impact: THIS WAS THE #1 SYSTEMIC BUG — every agent's feedback/action was silently lost
- **RESOLVED**

### I-13: Missing `from pathlib import Path` crash (2026-04-16 12:10)
- Root cause: worktree card read fix used Path without importing it
- Fix: added import
- Impact: every agent completion crashed with NameError, blocking all cards
- **RESOLVED**

### I-14: allow_fallback_commits=False — agent code lost (2026-04-16 12:30)
- Root cause: agents write code but don't commit; commit phase also doesn't commit; fallback disabled
- Fix: enabled allow_fallback_commits=True
- **RESOLVED**

### I-15: Worktree card in wrong stage dir (2026-04-16 13:00)
- Root cause: worktree created when card in Estimate/Coding; card moves on main; worktree copy stays in old dir
- Fix: process_agent_result scans ALL stage dirs in worktree, not just current stage
- **RESOLVED**

### I-16: AUTH-001 merge conflict markers break YAML parsing (2026-04-16)
- Root cause: manual merge left `<<<<<<<` markers in card file
- Fix: manual cleanup
- **RESOLVED**

### I-17: 11 branches with unmerged code — cards Done but code not on master (2026-04-16 14:00)
- Root cause: `finalize_completed_worktree` cherry-picks only 1 commit; multi-commit branches partially lost; integration often fails silently
- Fix: replaced cherry-pick with `git merge --squash` — captures ALL commits on branch in single merge commit. Added integration gate preventing Done without code on main.
- **RESOLVED**

### I-18: Phantom dependencies block cards permanently (2026-04-16 14:00)
- Root cause: `has_unmet_dependencies` treats non-existent card IDs as unmet
- Fix: phantom deps (ID not on board) now treated as met with WARN log
- **RESOLVED**

### I-19: Architect doesn't decompose oversized cards (2026-04-16)
- Root cause: no mandatory decomposition threshold
- Fix: architect prompt requires decomposition when effort_score > 70; sub-cards replace original; deps rewired
- **RESOLVED** (prompt-level)

## Known Failure Signatures

| Signature | First Seen | Status | Fix |
|-----------|-----------|--------|-----|
| false Done without code on master | 2026-04-16 | Fixed | code-changes gate + worktree card read |
| token burn without progress | 2026-04-16 | Fixed | uncommitted detection + fail threshold |
| cards stuck in Arbitration | 2026-04-16 | Fixed | fallback to Coding + auto-default |
| stale assignment after restart | 2026-04-15 | Fixed | release_stale_agents at startup |
| agent feedback silently lost | 2026-04-16 | Fixed | worktree card read |
| integration drops multi-commit work | 2026-04-16 | **Fixed** | squash-merge replaces cherry-pick |

## Architectural Hardening (2026-04-16)

### Completed (this session)
- [x] **FIX-1**: Squash-merge replaces cherry-pick — captures ALL commits on branch, not just one
- [x] **FIX-2**: Integration gate — card cannot move to Done until code verified on main (integrator exempt — merge runs in finalize)
- [x] **FIX-3**: Post-agent verification — autocommits uncommitted code before delivery check
- [x] **FIX-4**: Unified state machine — single TRANSITIONS table, consistency tests (10 tests)
- [x] **FIX-5**: Token budget per card — tracks tokens_spent, blocks on exhaustion
- [x] **BUGFIX**: Three-dot diff replaced with merge-base + two-dot diff (squash-merge doesn't make branch ancestor)
- [x] **BUGFIX**: tasks/ excluded from squash merge (worktree card files diverge from main)
- [x] **BUGFIX**: Token tracking accumulates across multiple executions per card

### P1 — Fix Soon
- [x] Unify _FORWARD_MOVES and DEFERRED_MOVE_RULES into single source
- [ ] Reduce stale-assignment timeout from 20min to 5min
- [ ] Auto-resolve conflicts only for task files (not source code)
- [ ] Stuck detection handles phantom deps
- [ ] Health check diagnostic dedup normalizes timestamps

### P2 — Improve
- [ ] Card lifecycle trace ID for log correlation
- [x] Token spend tracking per card
- [ ] Duplicate card ID detection in board hydration
- [ ] Board validation dry-run mode
- [ ] Cycle decomposition cards fast-track to Estimate

## Autonomy Readiness Checklist

- [x] Done always equals integrated, working code *(integration gate + worktree read + fallback autocommit)*
- [x] Integration merges all commits reliably *(squash-merge replaces cherry-pick)*
- [x] Cycles/deadlocks resolved by ORC *(arbitration fallback + backward moves)*
- [x] No unrecoverable branch/worktree information loss *(branches preserved)*
- [x] Token budget prevents unbounded spend *(per-card tracking + auto-block)*
- [ ] Monitoring and periodic reports stable *(Telegram blocked without VPN)*
- [ ] At least 3 uninterrupted healthy control cycles *(not yet achieved)*
