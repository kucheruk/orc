# Telegram notifications — policy and plan

## Current call sites (before this plan)

| Trigger | Site | Severity | Issue |
|---------|------|----------|-------|
| Every stage transition (coder→reviewer etc.) | `process_completed_task` | chatty | Floods: 4+ messages per card life |
| Card blocked after N failures | `escalate_if_threshold_reached` | normal | Keep |
| Card blocked by token-budget | `check_and_block_budget` (fix 5a3ac2e) | normal | Keep |
| Escalation at loop_count ≥ threshold | `teamlead_steps.CompletedEscalationStep` | normal | Keep |
| Auto-unblock cycle rewrite | `teamlead_autounblock.resolve_cycle_with_decomposition` | info | Demote to debug |
| Stale assignments released | `teamlead_autounblock.release_stale_assignments` | info | Demote to debug |
| Aggregated blocked cards sweep | `BlockedSweepStep` | normal | Keep |
| Teamlead `notify` action | `teamlead_actions/actions/notify.py` | normal | Keep, prefix "Teamlead" |
| Incident manager start/shutdown | `incident/manager.py` | normal | Keep |

## Two notification modes

Env var `ORC_NOTIFY_MODE`:

- `normal` (default): only "actionable" events. Oprator wakes up / stops the channel turning yellow.
  - Card reaching **8_Done** (final only, not every stage).
  - Card blocked (budget or failure threshold).
  - Escalation (loop_count ≥ threshold).
  - `skip_card` by teamlead.
  - Aggregated blocked-sweep.
  - Teamlead `notify` action.
  - ORC startup / clean shutdown.
- `debug`: everything above PLUS:
  - Every intermediate stage transition.
  - Cycle autounblock.
  - Stale-assignments release.
  - Health-check diagnostic summary.

## Plan

### Phase 1 — severity + mode (this PR)
1. Add `Severity = Enum("info", "normal")` to `notifications/messages.py`; every formatter returns `(severity, text)`.
2. `NotificationService` reads `ORC_NOTIFY_MODE`; `send_telegram(sev, msg)` drops `info` in normal mode.
3. `format_completion_message` returns `info` for non-Done transitions, `normal` when card lands in 8_Done.
4. `format_card_blocked`, `format_escalation`, `format_blocked_accumulation` → `normal`.
5. `format_cycle_autounblock`, `format_stale_assignments_released` → `info`.
6. Add `format_card_done`, `format_card_skipped`, `format_orc_startup`, `format_orc_shutdown`.

### Phase 2 — teamlead signature
7. Prefix `**Teamlead**: ` to every message originating from a teamlead path (`notify` action, escalations fired by `CompletedEscalationStep`).

### Phase 3 — missing notify sites
8. `skip_card` action emits `format_card_skipped` (currently only TUI emit).
9. CLI startup emits `format_orc_startup`; atexit handler emits `format_orc_shutdown` — both `normal`.

### Phase 4 — tl-health cost
10. Health prompt: drop the full `Kanban System Rules` + `Guidelines` (11 bullets) from every tick; keep only the Decision Protocol + Action Types. Static rules live in `AGENTS.md`.
11. Compact board detail in health mode: show only stuck / blocked / over-budget cards, not all 90+.
12. Skip health invocation entirely when board hash equals last tick's hash (no state change since last run) even if diagnostic is "new".

Target: `tl-health` ≤ 30K tokens/invocation (was 50–70K). 10 invocations/hour → ≤ 300K/hour, down from ~700K.
