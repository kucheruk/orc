# Step 4 Design: Single TaskLifecycleService For All Task Transitions

## Context

ORC already has a useful transition table in [state_machine.py](/Users/vetinary/work/orc/orc_core/board/state_machine.py:1), but the runtime still allows many state changes to happen outside one controlled application boundary.

Today the following code paths mutate lifecycle state directly:
- agent completion applies `action`, saves the card, and sometimes moves stage inside [agent_output.py](/Users/vetinary/work/orc/orc_core/agents/infra/agent_output.py:95);
- integration finalization moves a card to `Done` or resets it back to `Integrating` inside [finalize_task_worktree.py](/Users/vetinary/work/orc/orc_core/git/use_cases/finalize_task_worktree.py:24);
- repeated failure escalation blocks a card via [escalate_card.py](/Users/vetinary/work/orc/orc_core/board/use_cases/escalate_card.py:9);
- unblocking mutates action directly in [unblock_card.py](/Users/vetinary/work/orc/orc_core/board/use_cases/unblock_card.py:13);
- pull-time sweeps auto-promote and auto-archive by setting `card.action`, `move_card()`, and `save_card()` inside [kanban_pull.py](/Users/vetinary/work/orc/orc_core/board/kanban_pull.py:44);
- teamlead actions such as [skip.py](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_actions/actions/skip.py:14), [set_action.py](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_actions/actions/set_action.py:13), and [move.py](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_actions/actions/move.py:10) mutate cards directly;
- background automation in [teamlead_steps.py](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_steps.py:281) can commit arbitrary base-repo changes outside task lifecycle ownership.

The system therefore has a state machine, but not a single state transition owner.

## Relationship To Steps 1-3

This step assumes the target architecture of the previous three steps:
- Step 1: agent output is a structured artifact, not card mutation;
- Step 2: kanban has its own runtime and completion contract;
- Step 3: task identity and worktree ownership are keyed by `task_uid`, not by display id.

Without those steps, a lifecycle service would still inherit ambiguous agent output, backlog leakage, and unstable task ownership.

## Goal

Introduce one public application service, `TaskLifecycleService`, through which every lifecycle transition flows, so that:
- all stage/action/terminal changes have one entrypoint;
- `Done` is reachable only after verified integration onto `main`;
- archival is a separate terminal path, not a fake `Done`;
- blocking/unblocking/manual interventions reuse the same invariants as agent-driven transitions;
- base-repo commits are no longer performed by background heuristics outside lifecycle ownership.

## Non-Goals

Out of scope for this step:
- redesigning the board markdown format itself;
- replacing the state machine table with another policy language;
- rewriting integration internals;
- removing all existing board persistence code in one patch;
- solving task identity without Step 3.

This step is about who is allowed to transition state, not about changing every lower-level persistence primitive immediately.

## Problem Statement

The current state machine is necessary, but not sufficient.

### 1. Transition policy and mutation are still separate

`state_machine.py` defines which action changes are legal, but callers still decide:
- when to mutate the card object;
- when to save;
- when to move stages;
- when to release assignment;
- when to publish events;
- when to integrate;
- when to archive.

That means the real lifecycle contract is still distributed across callers.

### 2. Terminal semantics are overloaded

ORC currently uses `8_Done` both for:
- code that was integrated into `main`;
- non-delivery retirement such as decomposed parents;
- operator skip flows.

This breaks the desired invariant. If `Done` can also mean “retired without integration”, then `Done == integrated on main` can never be enforced.

### 3. External code can bypass lifecycle rules

[BoardGateway](/Users/vetinary/work/orc/orc_core/board/gateway.py:1) exposes low-level `save_card()` and `move_card()` to use cases outside the board module.

That API shape makes bypassing inevitable: any caller with a card instance can mutate it and persist it without passing through lifecycle policy.

### 4. Side effects are not ordered by one transaction boundary

Blocking, integration, cleanup, assignment release, notifications, outcome tracking, and board file writes happen in different modules.

This causes drift such as:
- blocked cards ending in impossible stages;
- integrator `Done` behavior split between agent result processing and finalize;
- teamlead actions bypassing integration semantics;
- background base-repo commits that are unrelated to the current task transition.

### 5. Auto-commit in the base repo violates ownership

[AutoCommitStep](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_steps.py:281) can commit both `tasks/` and arbitrary workspace files in the base repo.

That is not a lifecycle transition. It is an uncontrolled side effect that can:
- create commits with no task-level intent;
- blur the line between worktree-owned code and base-repo orchestration state;
- make “what changed because of this task?” harder to answer;
- bypass the invariant that delivery code lives in a task worktree until integration.

This step removes that behavior rather than wrapping it.

## Target Invariants

After this step:
- only `TaskLifecycleService` may change card `action`, `stage`, or terminal outcome;
- only `integrate_task()` may place a delivery-bearing task into `8_Done`;
- non-delivery retirement uses a separate archive path;
- `block_task()` is the only way to produce `action=Blocked`;
- agent completion never writes `Done` directly;
- direct `card.action = ...`, `board.move_card(...)`, and `board.save_card(...)` are forbidden outside lifecycle internals;
- no background process commits arbitrary base-repo source changes.

## Design Principles

### 1. Intents, not field edits

Callers request lifecycle intents such as:
- transition this task to `Reviewing`;
- block this task;
- integrate this task;
- archive this task.

They do not directly edit `card.action` or call `move_card()`.

### 2. One policy layer, one execution layer

The state machine remains the pure policy source of truth.
`TaskLifecycleService` becomes the only execution layer that applies those rules to persisted task state.

### 3. Distinct terminal outcomes

Integrated completion and archival are different domain outcomes and must not share one terminal stage.

### 4. Idempotent commands

Every public lifecycle command must be safe to retry after crash or duplicate delivery.

### 5. Worktree and lifecycle ownership align

Integration and archival decisions must resolve task ownership through Step 3's `task_uid` and worktree registry, not via display-id reconstruction.

## Target Domain Model

## New Terminal Stage

Add a separate archive stage:

```text
9_Archived
```

Semantics:
- `8_Done`: integrated on `main`;
- `9_Archived`: retired without code integration.

Examples that belong in `9_Archived`:
- decomposed parent replaced by sub-cards;
- operator skip of a non-delivery card;
- duplicate or invalid card retired by decision.

This separation is what makes `Done == integrated on main` enforceable.

## Card Metadata

Add minimal lifecycle metadata:

```python
lifecycle_version: int = 0
terminal_outcome: str = ""
terminal_reason: str = ""
```

Semantics:
- `lifecycle_version` increments on every accepted lifecycle command and is used for compare-and-swap;
- `terminal_outcome` is one of `""`, `"integrated"`, `"archived"`;
- `terminal_reason` stores the durable operator/system reason for terminalization.

If Step 3 already adds task-scoped runtime state, applied command ids can live outside the card in the repo state root. The card only needs the durable version and visible terminal metadata.

## Public Service API

Only these methods are public:

### `complete_agent_run(command)`

Consumes a structured agent result from Step 1 and applies the non-terminal consequences of a successful run.

Responsibilities:
- verify `task_uid`, `run_id`, role, and launch fingerprint;
- reject duplicate `run_id`;
- validate field updates and role permissions;
- validate requested lifecycle change against state machine policy;
- persist card content updates and allowed action/stage transition;
- emit a lifecycle result that may require subsequent integration.

Important rule:
- if an integrator run requests completion, `complete_agent_run()` does not write `Done`;
- it records that integration is requested and returns that fact to the caller;
- the worker then calls `integrate_task()`.

### `request_transition(command)`

Manual or deterministic system transition that is not a block/integration/archive.

Used for:
- teamlead “set action”;
- teamlead/manual move that is lifecycle-legal;
- auto-promote from Estimate to Todo;
- auto-unblock into a valid working action.

Responsibilities:
- load current card under lock;
- verify expected `lifecycle_version` when supplied;
- validate actor and reason;
- derive stage moves from policy instead of trusting caller-chosen stage;
- persist change and emit side effects in one place.

`request_transition()` must reject terminal targets such as `Done` and `Archived`.

### `block_task(command)`

The only public way to block a task.

Responsibilities:
- set `action=Blocked`;
- move card to `7_Handoff` when not already there;
- release assignment if held;
- append block reason or operator directive;
- increment `lifecycle_version`;
- emit escalation and notification side effects exactly once.

This replaces direct `card.block()` + `save_card()` patterns.

### `integrate_task(command)`

The only public way to place a task into `8_Done`.

Preconditions:
- task is owned by `task_uid`;
- lifecycle state indicates integration is requested or task is in integration-ready state;
- worktree/branch ownership is resolved through the Step 3 registry;
- merge to `main` succeeds or is already proven complete.

Responsibilities:
- run integration;
- persist integration metadata;
- move card to `8_Done`;
- set `terminal_outcome="integrated"`;
- clean up worktree ownership or mark cleanup retry separately if cleanup fails after merge;
- emit completion side effects.

If integration fails, the service must keep the task non-terminal and return a typed failure. No caller may “help” by writing `Done` anyway.

### `archive_task(command)`

The only public way to retire a task without integration.

Preconditions:
- explicit actor and reason;
- no unintegrated delivery branch/worktree exists for this task;
- archival policy allows the current state to be retired.

Responsibilities:
- move card to `9_Archived`;
- set `terminal_outcome="archived"`;
- clear assignment;
- clean up runtime ownership when safe;
- emit archival events.

This is the replacement for:
- `skip_card`;
- auto-archive of decomposed parents;
- any future “retire without delivery” flows.

## Internal Architecture

`TaskLifecycleService` should stay thin and delegate to small collaborators so code stays under the repo's size limits.

Proposed modules:
- `orc_core/lifecycle/commands.py`
- `orc_core/lifecycle/results.py`
- `orc_core/lifecycle/policy.py`
- `orc_core/lifecycle/service.py`
- `orc_core/lifecycle/ports.py`
- `orc_core/lifecycle/idempotency.py`

### `policy.py`

Pure rules:
- wraps existing [state_machine.py](/Users/vetinary/work/orc/orc_core/board/state_machine.py:1);
- adds terminal rules that state machine does not express today;
- forbids `Done` through `request_transition()`;
- forbids archive when unintegrated delivery ownership still exists.

### `service.py`

Application orchestration:
- lock task by `task_uid`;
- load current card + lifecycle runtime state;
- run idempotency check;
- call policy;
- persist card and runtime journal;
- invoke side effects in deterministic order.

### `idempotency.py`

Stores applied command ids, for example:

```text
<repo_state_root>/lifecycle/by-task/<task_uid>.json
```

Tracked keys:
- applied `run_id`s for `complete_agent_run`;
- applied `integration_id`s for `integrate_task`;
- applied operator `command_id`s for manual/block/archive actions.

This makes retries safe across crashes and process restarts.

## Persistence And Ports

Replace external low-level write access with a lifecycle-oriented port.

### New Port

Introduce something like:

```python
class TaskLifecyclePort(Protocol):
    def complete_agent_run(self, command: CompleteAgentRun) -> LifecycleResult: ...
    def request_transition(self, command: TransitionRequest) -> LifecycleResult: ...
    def block_task(self, command: BlockTask) -> LifecycleResult: ...
    def integrate_task(self, command: IntegrateTask) -> LifecycleResult: ...
    def archive_task(self, command: ArchiveTask) -> LifecycleResult: ...
```

### Retire Low-Level External Writes

[BoardGateway](/Users/vetinary/work/orc/orc_core/board/gateway.py:1) should stop exposing `save_card()` and `move_card()` to external use cases.

Those operations remain available only inside lifecycle/board internals.

## Side-Effect Ordering

For every accepted lifecycle command, the order must be:

1. Lock task by `task_uid`.
2. Load latest card and lifecycle state.
3. Validate idempotency and expected version.
4. Compute allowed transition via policy.
5. Persist card + lifecycle journal atomically as far as the filesystem layer allows.
6. Run side effects after state is durable.

Side effects include:
- assignment release;
- outcome tracking;
- notifications;
- event publishing;
- integration execution;
- worktree cleanup scheduling.

This order prevents “event emitted but state not saved” and similar split-brain failures.

## How Existing Callers Change

## Worker / Agent Completion

[process_task_result.py](/Users/vetinary/work/orc/orc_core/tasks/use_cases/process_task_result.py:1) and [agent_output.py](/Users/vetinary/work/orc/orc_core/agents/infra/agent_output.py:1) stop mutating board state directly.

New shape:
- parse structured result artifact;
- call `complete_agent_run()`;
- if result says `integration_requested`, call `integrate_task()`.

## Integration Finalization

[finalize_task_worktree.py](/Users/vetinary/work/orc/orc_core/git/use_cases/finalize_task_worktree.py:1) becomes an implementation detail of `integrate_task()` or disappears entirely.

No external caller sets `card.action = Done` or resets `Integrating` manually.

## Teamlead Actions

The following actions are rewritten to service calls:
- `skip_card` -> `archive_task()`;
- `set_action` -> `request_transition()`;
- `move_card` -> either `request_transition()` or a narrower operator command if stage-only moves remain necessary;
- unblock flows -> `request_transition()` or `block_task()` inverse path, but never direct mutation.

## Pull-Time Sweeps

[kanban_pull.py](/Users/vetinary/work/orc/orc_core/board/kanban_pull.py:1) stops calling `save_card()` and `move_card()` directly.

Examples:
- auto-promote -> `request_transition()`;
- decomposed parent retirement -> `archive_task()`, not `Done`.

## Blocking Paths

[escalate_card.py](/Users/vetinary/work/orc/orc_core/board/use_cases/escalate_card.py:1), [unblock_card.py](/Users/vetinary/work/orc/orc_core/board/use_cases/unblock_card.py:1), token-budget block paths in [worker.py](/Users/vetinary/work/orc/orc_core/agents/runners/worker.py:96), and repeated-failure escalation in [process_task_result.py](/Users/vetinary/work/orc/orc_core/tasks/use_cases/process_task_result.py:84) all route through lifecycle commands.

## AutoCommitStep

[AutoCommitStep](/Users/vetinary/work/orc/orc_core/agents/runners/teamlead_steps.py:281) is deleted.

Replacement rules:
- task source code is committed only inside the task worktree by the worker/agent flow;
- board/task projection writes are performed by lifecycle persistence, not by background git heuristics;
- base repo merge commits are performed only by `integrate_task()`.

There is no fallback background commit path in the target design.

## Enforcement Strategy

Python cannot enforce module privacy by itself, so we need both API and test enforcement.

### API Enforcement

- external modules depend on `TaskLifecyclePort`, not on `BoardGateway.save_card/move_card`;
- `KanbanBoard.save_card()` and `move_card()` remain concrete internals, not external application APIs.

### Architecture Tests

Add tests that fail if forbidden patterns appear outside lifecycle internals:
- direct `card.action =` writes;
- external `board.save_card(` calls;
- external `board.move_card(` calls.

Whitelist only:
- lifecycle modules;
- card entity methods where the entity mutates itself;
- board persistence internals.

This turns the architectural rule into something CI can enforce.

## Migration Plan

1. Add `9_Archived`, `lifecycle_version`, and terminal metadata to the card model.
2. Introduce `TaskLifecyclePort` and `TaskLifecycleService` beside existing flows.
3. Route `skip`, `escalate`, `unblock`, and repeated-failure blocking through the service.
4. Route agent completion through `complete_agent_run()`.
5. Move integration finalization behind `integrate_task()`.
6. Convert pull-time auto-promote and auto-archive to service calls.
7. Remove low-level external write access from `BoardGateway`.
8. Delete `AutoCommitStep`.
9. Add architecture tests forbidding direct mutation outside the lifecycle boundary.

## Testing Strategy

Minimum coverage:
- integrator completion does not mark `Done` before `integrate_task()` succeeds;
- `integrate_task()` is the only path to `8_Done`;
- `skip_card` archives to `9_Archived`, not `8_Done`;
- decomposed parent auto-retirement archives, not `Done`;
- `block_task()` always lands in `7_Handoff + Blocked`;
- duplicate `run_id` is idempotent;
- repeated `integration_id` is idempotent;
- archive is rejected when task ownership still has unintegrated code;
- architecture guard fails on direct `save_card`/`move_card` usage outside lifecycle modules.

## Expected Outcome

After this step, ORC stops treating lifecycle as a convention scattered across helpers.

Instead:
- state machine remains the rulebook;
- `TaskLifecycleService` becomes the single executor of those rules;
- `Done` becomes a true integration guarantee;
- `Archived` becomes the honest non-delivery terminal state;
- teamlead/system automation stop being exceptions to the lifecycle model.
