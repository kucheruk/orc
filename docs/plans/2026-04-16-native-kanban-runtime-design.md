# Step 2 Design: Native Kanban Runtime Instead Of Backlog Compatibility Layer

## Context

Today kanban execution in ORC is not a native runtime. It is a kanban-shaped adapter layered on top of the older backlog execution engine.

That coupling is visible in the current code:
- `build_kanban_request()` writes a fake `_board` sentinel to satisfy backlog fields in `TaskExecutionRequest` ([request_builder.py](/Users/vetinary/work/orc/orc_core/agents/infra/request_builder.py:20)).
- `TaskExecutionRequest` is backlog-oriented by shape: `backlog_path`, `backlog_arg`, `integrate_to_main` ([request.py](/Users/vetinary/work/orc/orc_core/tasks/execution/request.py:18)).
- `TaskExecutionEngine` always resolves base/runtime backlog paths and instantiates `MarkdownBacklogQuery` ([engine.py](/Users/vetinary/work/orc/orc_core/tasks/execution/engine.py:27)).
- `run_stage_loop()` passes `MarkdownTaskSource(...).list_tasks()` into launch-time monitoring ([stage_loop.py](/Users/vetinary/work/orc/orc_core/tasks/execution/stage_loop.py:111)).
- completion logic contains explicit kanban escape hatches such as “if `_board`, skip backlog invariant” ([finalize.py](/Users/vetinary/work/orc/orc_core/tasks/execution/finalize.py:126), [detector.py](/Users/vetinary/work/orc/orc_core/tasks/backlog/detector.py:51)).
- resume logic decides whether state is reusable by comparing backlog paths ([resume.py](/Users/vetinary/work/orc/orc_core/tasks/execution/resume.py:68)).
- hook/task-state payloads require `backlog_path` and treat completion as a backlog concern ([hooks.py](/Users/vetinary/work/orc/orc_core/tasks/integration/hooks.py:92), [orc_stop.py](/Users/vetinary/work/orc/orc_core/hook_scripts/orc_stop.py:78)).

This is the architectural reason kanban fixes keep arriving as local conditionals instead of as stable runtime rules. The system still thinks “a task is a backlog task” and kanban repeatedly proves otherwise.

## Relationship To Step 1

This design assumes Step 1 as the target completion contract:
- the agent returns an explicit structured result artifact;
- the agent does not mutate task markdown as the control-plane output.

Step 2 does not require Step 1 to be fully implemented first, but the native kanban runtime must be designed around explicit structured output, not backlog completion heuristics.

## Goal

Introduce a dedicated kanban runtime so that:
- kanban execution no longer depends on backlog paths, backlog sentinels, or markdown backlog queries;
- kanban completion is determined by native kanban contracts, not backlog mutation;
- worker/teamlead code can continue to use a stable executor interface without importing backlog-only DTOs;
- hooks and run-state files become runtime-kind aware instead of assuming “everything is a backlog task”.

## Non-Goals

Out of scope for this step:
- changing task/worktree identity (`task_uid`, branch naming);
- replacing direct lifecycle mutations with a single application service;
- redesigning board state storage;
- removing backlog runtime for legacy non-kanban flows.

Backlog runtime remains supported. The goal is to stop forcing kanban through it.

## Target Invariants

After this step:
- kanban execution never creates or reads a fake `_board` backlog sentinel;
- no kanban code path depends on `MarkdownBacklogQuery` or `MarkdownTaskSource`;
- kanban completion never depends on a task being marked done in a backlog file;
- kanban resume eligibility is based on kanban run identity and card state, not `backlog_path`;
- hooks do not require `backlog_path` for kanban runs;
- the worker/integrator boundary stays explicit: the kanban runtime runs an agent, but does not pretend to be the backlog main-integration pipeline.

## Problem Statement

The current implementation mixes three layers that should be independent:

1. Low-level agent runtime
   - launch process;
   - monitor output;
   - restart/resume;
   - prompt file materialization;
   - token accounting.

2. Backlog-specific policy
   - how “done” is detected;
   - how base/runtime backlog are synchronized;
   - when main integration is run;
   - what task-state payload means.

3. Kanban-specific policy
   - one board card per run;
   - explicit role/action transitions;
   - worktree-driven delivery;
   - integration owned by worker/integration manager, not by generic execution engine.

The existing engine merges all three. Kanban inherits backlog policy and then spends code to turn it back off.

## Design Principles

### 1. Shared infra is allowed, shared semantics are not

Kanban and backlog may share:
- process launch/monitoring;
- stream parsing;
- restart policy;
- commit-phase executor;
- prompt-file generation;
- token/duration accounting.

They must not share:
- execution request DTOs;
- completion detection;
- run-state schema;
- resume eligibility rules;
- hook assumptions about backlog files;
- main-integration semantics.

### 2. Runtime kind must be explicit

Any state payload or hook input that can represent more than one runtime must include a discriminant:

```json
{
  "kind": "kanban"
}
```

No more sentinel-style inference via `_board`.

### 3. Kanban completion is explicit

For kanban:
- success = process completed + structured result artifact exists and validates;
- failure = process exited/stalled/ttl/etc. without a valid result artifact;
- no backlog mutation is consulted.

## Target Architecture

## Runtime Split

Introduce three explicit layers:

### A. Shared run core

A small shared layer for low-level agent execution. It owns:
- prompt file creation;
- process launch;
- stream monitoring;
- wait/restart loops;
- commit-phase execution;
- metrics/token capture.

This can initially reuse existing modules in `orc_core/tasks/execution/*`, but the architectural target is a neutral package such as:
- `orc_core/run_core/launch.py`
- `orc_core/run_core/restart_policy.py`
- `orc_core/run_core/monitor_wait.py`
- `orc_core/run_core/prompt_files.py`
- `orc_core/run_core/stats.py`

### B. Backlog runtime

The current backlog execution behavior stays in a backlog-specific package, for example:
- `orc_core/backlog_runtime/request.py`
- `orc_core/backlog_runtime/engine.py`
- `orc_core/backlog_runtime/resume.py`
- `orc_core/backlog_runtime/finalize.py`

This package is the only place allowed to import:
- `MarkdownBacklogQuery`
- `MarkdownTaskSource`
- backlog sync and backlog invariant validators.

### C. Kanban runtime

Add a dedicated package:
- `orc_core/kanban_runtime/request.py`
- `orc_core/kanban_runtime/state.py`
- `orc_core/kanban_runtime/engine.py`
- `orc_core/kanban_runtime/resume.py`
- `orc_core/kanban_runtime/finalize.py`
- `orc_core/kanban_runtime/outcome.py`

This package owns kanban semantics end-to-end.

## Neutral Executor Interface

Today `TaskExecutor` and `RunnerStateManager` are typed to `TaskExecutionRequest` ([protocols.py](/Users/vetinary/work/orc/orc_core/agents/infra/protocols.py:21)).

That is another hidden backlog dependency.

### Proposed Change

Introduce a neutral request protocol or base DTO, for example:

```python
class ExecutionRequest(Protocol):
    workdir: str
    base_workdir: str
    run_root: Path
    timing: TimingConfig
    models: ModelConfig
    templates: TemplateConfig
    process_lifecycle: ProcessLifecyclePort
    state_writer: TaskStateWriter
    state_paths: StatePathsPort
```

Then:
- `BacklogExecutionRequest` implements it.
- `KanbanExecutionRequest` implements it.

`TaskExecutor.execute(request) -> TaskExecutionResult` can stay stable; only the request type becomes runtime-neutral.

This preserves worker/teamlead composition while removing DTO leakage from backlog runtime.

## KanbanExecutionRequest

### Shape

Proposed dedicated request:

```python
@dataclass(frozen=True, kw_only=True)
class KanbanExecutionRequest:
    card_id: str
    card_title: str
    role: str
    session_id: str
    run_id: str
    launch_fingerprint: KanbanLaunchFingerprint
    result_file: Path
    task_state_file: Path
    workdir: str
    base_workdir: str
    run_root: Path
    timing: TimingConfig
    models: ModelConfig
    templates: TemplateConfig
    commit_phase: bool
    allow_fallback_commits: bool
    main_branch: str
    progress_done: int
    progress_total: int
    progress_in_progress: int
    process_lifecycle: ProcessLifecyclePort
    state_writer: TaskStateWriter
    state_paths: StatePathsPort
    agent_env: Optional[Mapping[str, str]]
    snapshot_publisher: Optional[Callable[[MonitorSnapshot], None]]
```

### Notes

- No `backlog_path`.
- No `backlog_arg`.
- No `integrate_to_main`.
- No `stage_specs` unless kanban later explicitly needs multi-phase runs.

Integration remains the worker/integrator concern after execution succeeds.

## Kanban Run State

The current task-state file is backlog-oriented and written by `write_task_file()` ([hooks.py](/Users/vetinary/work/orc/orc_core/tasks/integration/hooks.py:92)).

Kanban needs its own payload.

### Proposed Schema

```json
{
  "version": 1,
  "kind": "kanban",
  "run_id": "s2:AUTH-001:attempt-1",
  "session_id": "s2",
  "card_id": "AUTH-001",
  "card_title": "Implement login flow",
  "role": "coder",
  "workspace_root": "/repo",
  "worktree_path": "/repo/.worktrees/AUTH-001",
  "branch_name": "orc/AUTH-001",
  "state_root": "/repo/.orc",
  "conversation_id": "",
  "created_at": "2026-04-16T23:10:00+03:00",
  "restart_count": 0,
  "status": "active",
  "result_file": "/repo/.orc/run/.../results/AUTH-001__implementation__attempt-1.json",
  "launch_fingerprint": {
    "stage": "4_Coding",
    "action": "Coding",
    "file_path": "tasks/4_Coding/AUTH-001.md",
    "updated_at": "2026-04-16T20:05:00+00:00"
  }
}
```

### Resume Eligibility

Kanban resume should be accepted only if all of the following still match:
- `kind == "kanban"`
- `card_id`
- `role`
- `workspace_root`
- `worktree_path`
- `launch_fingerprint`

If any differ, ORC drops stale state and starts fresh. This is much closer to kanban reality than comparing backlog paths.

## Kanban Engine Flow

The native kanban engine is intentionally simpler than the backlog engine.

### Before Launch

The worker prepares:
- current canonical card snapshot;
- kanban launch fingerprint;
- result artifact path;
- kanban run-state file;
- environment variables:
  - `ORC_RUN_KIND=kanban`
  - `ORC_RUN_STATE_FILE=<...>`
  - `ORC_AGENT_RESULT_FILE=<...>`
  - existing workspace/session vars as needed.

### Launch

The engine launches the agent through shared run-core machinery:
- prompt file;
- process spawn;
- stream monitor;
- periodic snapshots;
- token accounting.

### Wait Loop

The kanban wait loop uses process/monitor signals only:
- `COMPLETED`
- `WAITING_FOR_INPUT`
- `STALLED`
- `TTL_EXCEEDED`
- `PROCESS_EXITED`
- `MODEL_UNAVAILABLE`

There is no backlog done detector and no runtime/base backlog sync.

### Successful Completion

On process completion:
1. load structured result artifact from Step 1;
2. validate schema and launch fingerprint;
3. optionally run commit phase if enabled;
4. return `TaskExecutionResult(status=COMPLETED, ...)`.

The board transition is still applied outside the engine by worker orchestration logic.

### Failure Completion

If the process completed but no valid result artifact exists:
- return `FAILED` with a kanban-specific reason such as `missing_result_artifact` or `invalid_result_artifact`.

This is deliberate fail-fast. Silent inference from backlog state must not come back through another door.

## Hook Contract

Current stop hook logic is backlog-centric:
- it requires `backlog_path`;
- it parses backlog counts;
- it decides completion cleanup from backlog/task state;
- it may emit follow-up commit instructions ([orc_stop.py](/Users/vetinary/work/orc/orc_core/hook_scripts/orc_stop.py:78)).

That is incompatible with a native kanban runtime.

### New Rule

Hooks must become runtime-kind aware.

For `kind == "kanban"`:
- do backfill `conversation_id` if needed;
- do collect token/duration metrics;
- do not require `backlog_path`;
- do not parse backlog counts;
- do not mark completion by backlog state;
- do not delete run-state files on their own;
- do not emit “commit EVERYTHING+push” follow-up prompts.

In kanban mode, hooks are observational only. The orchestrator owns completion, cleanup, and lifecycle transitions.

### Migration Compatibility

During migration, the hook may support both:
- legacy payloads with `backlog_path`;
- new payloads with `kind`.

But new kanban runtime must write only the explicit `kind == "kanban"` shape.

## Request Factory Changes

`KanbanRequestFactory` should stop building a backlog-shaped request.

Instead of:
- creating `_board`;
- populating `backlog_path` / `backlog_arg`;
- returning `TaskExecutionRequest`;

it should:
- create `KanbanExecutionRequest`;
- allocate kanban run-state path;
- allocate result artifact path;
- inject runtime-kind env vars.

This removes one of the earliest compatibility hacks in the kanban path.

## What Remains Outside Kanban Runtime

The native kanban runtime still should not own:
- board mutation;
- role/action validation;
- integration into main;
- worktree cleanup;
- teamlead arbitration.

Those stay in the kanban orchestration layer:
- worker runner;
- board state machine;
- integration manager;
- result-apply logic from Step 1.

The runtime’s responsibility is only: execute one kanban agent run deterministically.

## Migration Plan

### Phase 1: Introduce kanban-specific DTOs and state file

Add:
- `KanbanExecutionRequest`
- `KanbanRunState`
- a kanban request builder

Keep shared low-level launch code unchanged.

### Phase 2: Introduce KanbanExecutionEngine

Implement a one-phase kanban engine that:
- launches;
- waits;
- resumes;
- validates explicit result artifact;
- runs optional commit phase.

No backlog imports are allowed in this package.

### Phase 3: Switch worker/session composition to native kanban engine

Update:
- request factory;
- state manager;
- worker runner typing.

At this point kanban no longer creates `_board`.

### Phase 4: Make hooks runtime-kind aware

Update:
- `orc_stop.py`
- `orc_hook_lib.py`
- task-state writing path

Kanban hooks become observational only.

### Phase 5: Delete kanban compatibility branches from backlog engine

Remove:
- `_board` sentinel handling;
- kanban branches in backlog detector/finalizer;
- kanban resume logic that depends on backlog paths.

After this phase, backlog engine is backlog-only again.

## Testing Strategy

### Unit Tests

Add:
- `tests/test_kanban_runtime_request.py`
- `tests/test_kanban_runtime_resume.py`
- `tests/test_kanban_runtime_engine.py`
- `tests/test_kanban_runtime_hooks.py`

Cover:
- no sentinel `_board` creation;
- no `MarkdownBacklogQuery` usage;
- resume acceptance/rejection by kanban run identity;
- failure on missing result artifact;
- hook behavior for `kind == "kanban"` without `backlog_path`.

### Integration Tests

Add:
- worker runner using native kanban engine with worktree;
- successful completion path with structured result artifact;
- restart path after waiting-for-input;
- stale run-state auto-drop when fingerprint changes.

### Regression Tests

Retire kanban assertions that depend on backlog semantics, especially tests that currently validate:
- backlog sync from worktree to base;
- backlog mismatch as the kanban resume discriminator.

Those behaviors belong to backlog runtime only.

## Open Questions

- Should the shared executor protocol be widened via a neutral `ExecutionRequest` Protocol, or should `TaskExecutor` become generic?
- Should kanban run-state replace the old `ORC_TASK_FILE` env var immediately, or should we carry `ORC_RUN_STATE_FILE` + legacy `ORC_TASK_FILE` in parallel for one migration window?
- Should kanban keep optional multi-stage execution hooks for future internal sub-phases, or explicitly stay single-phase until a concrete need appears?

## Expected Outcome

After this step:
- kanban execution becomes understandable on its own terms;
- bugs in kanban no longer require patching backlog completion logic;
- `_board` and similar compatibility hacks disappear;
- hook/state logic becomes explicit instead of accidental;
- future work on identity, lifecycle ownership, and integration safety can proceed on top of a real kanban runtime rather than on top of backlog emulation.
