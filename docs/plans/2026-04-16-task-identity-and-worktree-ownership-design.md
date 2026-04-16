# Step 3 Design: Stable Task Identity And External Worktree Ownership

## Context

ORC currently overloads the visible card id (`TASK-001`, `AUTH-003`, `UX-001`) as all of the following:
- the human-facing identifier on the board;
- the canonical filename stem in `tasks/`;
- the git branch identity;
- the worktree directory identity;
- the integration branch lookup key;
- the cleanup/recovery lookup key.

That design is encoded directly in the current implementation:
- `task_branch_name(task_id)` derives the branch name from `_safe_name(task_id)` ([worktree_flow.py](/Users/vetinary/work/orc/orc_core/git/worktree_flow.py:25)).
- `create_task_worktree()` derives the worktree directory from the same `_safe_name(task_id)` ([worktree_flow.py](/Users/vetinary/work/orc/orc_core/git/worktree_flow.py:145)).
- `cleanup_done_worktrees()` reconstructs worktree ownership from `_safe_name(card_id)` again during startup sweep ([state_persistence.py](/Users/vetinary/work/orc/orc_core/agents/session/state_persistence.py:68)).
- integration logic re-derives the branch name from the visible card id ([agent_output.py](/Users/vetinary/work/orc/orc_core/agents/infra/agent_output.py:46), [main_integrator.py](/Users/vetinary/work/orc/orc_core/tasks/integration/main_integrator.py:37)).
- `KanbanCard` has no separate runtime identity field; `id` is the only durable identifier on the card ([kanban_card.py](/Users/vetinary/work/orc/orc_core/board/kanban_card.py:21)).

The result is that the visible board label is acting as the primary key for both human workflow and machine ownership. That is the root architectural problem.

## Why This Must Be A Separate Step

Step 1 removes the card markdown file from the control plane.
Step 2 gives kanban its own runtime instead of tunneling through backlog semantics.

Neither of those solves task identity by itself.

If ORC keeps using the visible card id as the runtime key, the system will still be vulnerable to:
- lossy branch/path collisions;
- mis-attaching a branch created for one card to another card with a similar id;
- sweep/cleanup code reconstructing the wrong worktree from a derived name;
- integration checks reading the wrong branch for a card;
- worktree ownership depending on transient session state.

Step 3 is the point where ORC stops treating the display id as the machine identity.

## Goal

Introduce a stable opaque `task_uid` and move worktree ownership out of the git working tree into an external registry so that:
- the visible card id remains human-facing only;
- branch names and worktree paths are derived from `task_uid`, not from a lossy transform of display id;
- ownership is recoverable without session-local state;
- create/reuse/cleanup/integration all resolve the same task identity through one canonical service;
- no ownership metadata written by ORC makes a fresh worktree dirty.

## Non-Goals

Out of scope for this step:
- replacing kanban card markdown with another board storage;
- redesigning dependency notation (`dependencies` still point to visible card ids);
- rewriting the worker/integration lifecycle;
- changing the operator-facing visible card id format (`TASK-001` remains valid);
- removing old backlog identity assumptions outside kanban-specific flows.

## Current Failure Modes

### 1. Lossy branch and path derivation

`_safe_name()` normalizes arbitrary ids into a reduced alphabet and truncated length ([worktree_flow.py](/Users/vetinary/work/orc/orc_core/git/worktree_flow.py:13)).

That means distinct visible ids can collapse to the same machine identity.

Example collision class:
- `TASK-1!`
- `TASK-1?`

Both normalize to `TASK-1`, which means both resolve to:
- the same branch name: `orc/TASK-1`
- the same worktree directory: `<worktrees_root>/TASK-1`

This is not a theoretical risk. It is a direct consequence of the current naming function.

### 2. Ownership metadata inside the worktree makes the worktree dirty

To detect collisions, ORC writes `.orc-card-id` into the worktree root ([worktree_flow.py](/Users/vetinary/work/orc/orc_core/git/worktree_flow.py:196)).

That makes a newly created worktree dirty even before any agent touches source files.
Later, `cleanup_task_worktree()` refuses normal removal unless the remaining dirty paths are classified as runtime artifacts, but `.orc-card-id` is not one of them ([git_helpers.py](/Users/vetinary/work/orc/orc_core/git/git_helpers.py:90)).

So create and cleanup already disagree about what ORC itself owns.

### 3. Recovery and cleanup reconstruct identity instead of loading it

Startup sweep for completed/blocked cards rebuilds the worktree path from `_safe_name(card_id)` ([state_persistence.py](/Users/vetinary/work/orc/orc_core/agents/session/state_persistence.py:68)).

That means the system does not have a canonical ownership record. It re-derives ownership from the display id every time and hopes the derivation is unique and stable.

### 4. Integration lookup is tied to display id

Branch-integrated checks and main-merge logic rebuild branch names from `card.id` rather than from a stable runtime key ([agent_output.py](/Users/vetinary/work/orc/orc_core/agents/infra/agent_output.py:46), [main_integrator.py](/Users/vetinary/work/orc/orc_core/tasks/integration/main_integrator.py:37)).

That means identity bugs in worktree creation automatically leak into integration correctness.

### 5. Session-scoped state is not ownership

There is a worktree registry path keyed by `session_id` in `state_paths.py` ([state_paths.py](/Users/vetinary/work/orc/orc_core/infra/io/state_paths.py:95)), but session ids are ephemeral and cannot be the canonical owner of a task branch or worktree.

Worktree ownership must outlive a session crash, restart, or pool reallocation.

## Design Principles

### 1. Display id is not the primary key

Visible ids such as `TASK-001` or `AUTH-003` remain:
- human-readable;
- stable for dependencies and operator commands;
- present in filenames and UI.

But they are no longer the runtime identity.

### 2. Every task gets a stable opaque `task_uid`

`task_uid` is the primary key for:
- branch identity;
- worktree identity;
- ownership records;
- run artifacts;
- integration lookups.

The visible `id` becomes a label, not the ownership key.

### 3. Ownership metadata lives outside the worktree

ORC must not write owner markers into the git working tree root.
Ownership must be tracked in ORC state storage under `ORC_STATE_ROOT`, not as an untracked file inside the repo worktree.

### 4. Machine identity is loaded, not reconstructed

If ORC needs to know “which worktree belongs to this task?”, it should load a canonical record keyed by `task_uid`.
It should not recompute a path from the display id and hope it lands on the correct resource.

### 5. One identity builder, one registry reader

All code paths that need task ownership must go through a shared identity module and registry module.
No direct `_safe_name(card.id)` calls may remain in business logic once migration is complete.

## Proposed Data Model

## Card Model

Extend `KanbanCard` with a new persistent field:

```python
task_uid: str
```

### Semantics

- `id`: visible immutable board id, for humans and dependencies.
- `task_uid`: opaque immutable runtime id, for ORC ownership and git/runtime resources.

### Serialization

`task_uid` is stored in the YAML frontmatter alongside `id`.

### Protection

`task_uid` becomes a protected field just like `id` and `stage`.
Agents and teamlead actions must never mutate it.

## UID Format

Use a full opaque uuid-like token in storage, for example:

```text
5f0a0c7b3f174f0e9c4ef9b43b4e5d12
```

Requirements:
- generated once at card creation time;
- globally unique without coordination;
- lowercase ASCII;
- never reused;
- never derived from `id` or title.

The runtime may use a short prefix of `task_uid` for human-readable derived names, but the canonical stored value remains full-length.

## Derived Machine Names

### Branch Name

Replace:

```text
orc/<safe-display-id>
```

With:

```text
orc/t-<uid12>-<display-slug>
```

Example:

```text
orc/t-5f0a0c7b3f17-auth-003
```

Where:
- `<uid12>` is the first 12 chars of `task_uid`;
- `<display-slug>` is optional, human-friendly, and non-authoritative;
- uniqueness comes from `task_uid`, not from the slug.

### Worktree Path

Replace:

```text
<worktrees_root>/<safe-display-id>
```

With:

```text
<worktrees_root>/<uid12>
```

or, if operator readability is useful:

```text
<worktrees_root>/<uid12>-<display-slug>
```

Again, uniqueness comes from `task_uid`.

### Run/Artifact Paths

As Step 1 and Step 2 progress, run roots and result artifacts should move to `task_uid` too:

```text
.../runs/kanban/<uid12>/<session-id>/...
.../results/<uid12>__attempt-<n>.json
```

The visible id may still appear in filenames for readability, but it must never be the uniqueness key.

## External Worktree Registry

## Canonical Record

Introduce a task-keyed worktree registry entry stored outside the repo working tree:

```text
<repo_state_root>/worktrees/by-task/<task_uid>.json
```

Where `repo_state_root` is already derived from `repo_key(workdir)` in `state_paths.py` ([state_paths.py](/Users/vetinary/work/orc/orc_core/infra/io/state_paths.py:17)).

### Proposed Schema

```json
{
  "version": 1,
  "task_uid": "5f0a0c7b3f174f0e9c4ef9b43b4e5d12",
  "display_id": "AUTH-003",
  "branch_name": "orc/t-5f0a0c7b3f17-auth-003",
  "worktree_path": "/.../worktrees/5f0a0c7b3f17-auth-003",
  "base_workdir": "/repo",
  "repo_key": "29d175b81f9b5e9f",
  "status": "attached",
  "created_at": "2026-04-16T23:50:00+03:00",
  "last_attached_at": "2026-04-16T23:50:00+03:00",
  "last_session_id": "s2",
  "last_known_head": "abc123...",
  "legacy_branch_name": "orc/AUTH-003"
}
```

### Notes

- `task_uid` is the record key and payload key.
- `display_id` is informational only.
- `status` can be `attached`, `detached`, `cleaned`, `orphaned`, `migration_pending`.
- `legacy_branch_name` is temporary and only needed during migration.

## Session Records Remain Secondary

Session-scoped state can still exist:
- active session;
- active task;
- session manifests.

But these records point to `task_uid`.
They are not authoritative ownership records.

## Identity Service

Add a small dedicated identity module, for example:

- `orc_core/identity/task_identity.py`
- `orc_core/git/worktree_registry.py`

### Responsibilities

#### Task identity

- generate `task_uid`;
- build canonical branch name;
- build canonical worktree path;
- build task-keyed registry path;
- parse/render operator-friendly slugs.

#### Worktree registry

- load/save task-keyed worktree records;
- mark attach/detach/cleanup transitions;
- recover from partial state when git/worktree/registry disagree;
- expose a single `resolve_task_worktree(card)` entry point.

No other module should build branch names or worktree paths manually.

## Lifecycle Changes

## Card Creation

When a new card is created:
1. generate `task_uid`;
2. persist it into card frontmatter;
3. return the card with both `id` and `task_uid`.

The existing visible id generation (`TASK-001`) remains unchanged.

## Worktree Creation

When a worker needs a worktree:
1. load the task-keyed worktree record by `task_uid`;
2. if it exists and points to a live matching branch/worktree, reuse it;
3. otherwise create a new branch and worktree from the canonical task identity;
4. persist/update the external registry record.

There is no owner file written inside the worktree.

## Worktree Reuse

Reuse is allowed only if all of the following match:
- `task_uid`;
- `base_workdir` / `repo_key`;
- `branch_name`;
- `worktree_path`.

Visible `display_id` mismatch is logged as a data-integrity warning, not used as the runtime key.

## Cleanup

Cleanup uses the registry record, not `_safe_name(card_id)`.

Algorithm:
1. load record by `task_uid`;
2. if `worktree_path` exists, attempt normal `git worktree remove`;
3. update registry status;
4. do not infer the path from display id;
5. preserve or retire the branch according to higher-level policy, but always write the outcome to the registry.

Because ownership metadata no longer lives in the worktree root, a fresh worktree is no longer dirty by ORC’s own design.

## Recovery And Startup Sweep

Startup cleanup and orphan recovery must also become registry-driven.

Instead of:
- iterating visible ids;
- deriving `_safe_name(card_id)`;
- hoping that path still belongs to the same task,

the system should:
1. load the registry;
2. compare records with board cards by `task_uid`;
3. reconcile missing branches/worktrees;
4. clean or detach resources whose owning card is done/blocked/removed.

This is the only way recovery can be deterministic after crashes.

## Integration Lookup

Integration code must stop resolving branch names from `card.id`.

All such flows should use:
- `card.task_uid`
- identity service -> `branch_name_for(card.task_uid, card.id)`

Affected surfaces include:
- “is branch integrated” checks;
- main integration branch resolution;
- stale branch cleanup and reporting.

This makes integration correctness independent of display-id normalization.

## Migration Strategy

## Phase 1: Add `task_uid` to cards

Extend `KanbanCard` frontmatter with `task_uid`.

For existing cards that do not have it:
- perform a startup migration before worker sessions launch;
- write a generated `task_uid` back to canonical card files;
- never generate it lazily in the middle of a worktree operation.

This keeps migration explicit and idempotent.

## Phase 2: Introduce dual-read identity resolution

During migration, identity resolution should support both:
- native task-keyed registry (`task_uid`);
- legacy display-id-derived resources.

If a card has a `task_uid` but no registry record:
1. look for a legacy branch/worktree using the old naming rule;
2. if exactly one safe match exists, bind it into the new registry;
3. mark the record with `legacy_branch_name`;
4. continue using the task-keyed record from then on.

## Phase 3: Rename legacy branches when safe

For unambiguous legacy branches:
- rename `orc/<safe-display-id>` to the new `task_uid`-based branch name;
- update registry.

If a rename is unsafe or blocked:
- keep the old branch temporarily;
- store it as `legacy_branch_name`;
- let integration and cleanup consult the registry alias.

The system must prefer continuity over perfect renaming.

## Phase 4: Remove legacy derivation from runtime code

After migration support is in place:
- delete direct `_safe_name(card_id)` usage from business logic;
- stop reconstructing worktree paths from visible ids;
- remove `.orc-card-id`;
- update cleanup, sweep, integration, and reporting to be registry-driven.

## Phase 5: Retire session-keyed worktree ownership

Session-keyed worktree records may still exist for diagnostics, but canonical ownership must be task-keyed.

At that point, `worktree_record_path(workdir, session_id)` is informational only or can be removed.

## Compatibility Rules

### Dependencies remain display-id based

`dependencies` continue to reference visible ids like `TASK-001`.
This is a human workflow concern and does not need to change in this step.

### Filenames may remain display-id based

Card files in `tasks/<stage>/<display-id>.md` may remain as they are.

This step is about runtime ownership, not about changing operator-facing filenames.

### Visible id stays immutable

Because dependencies and operator commands still target visible ids, `id` remains immutable and protected.
The key change is that it is no longer the machine ownership key.

## Module Impact

## New Modules

Add:
- `orc_core/identity/task_identity.py`
  - `generate_task_uid()`
  - `branch_name_for(task_uid, display_id)`
  - `worktree_path_for(base_workdir, task_uid, display_id)`
- `orc_core/git/worktree_registry.py`
  - load/save/update task-keyed worktree records
- `orc_core/git/worktree_record.py`
  - typed DTO for registry records

## Existing Modules To Change

Refactor:
- `orc_core/board/kanban_card.py`
  - add `task_uid`
- `orc_core/board/kanban_card_factory.py`
  - generate `task_uid` on create
- `orc_core/git/worktree_flow.py`
  - replace `_safe_name(task_id)` ownership logic
- `orc_core/agents/session/state_persistence.py`
  - cleanup based on registry, not visible id derivation
- `orc_core/agents/infra/agent_output.py`
  - integration lookup by `task_uid`
- `orc_core/tasks/integration/main_integrator.py`
  - branch lookup by `task_uid`
- `orc_core/infra/io/state_paths.py`
  - add task-keyed worktree registry paths

## Testing Strategy

### Unit Tests

Add coverage for:
- unique `task_uid` generation;
- branch naming from `task_uid`;
- worktree path naming from `task_uid`;
- registry round-trip save/load;
- legacy-branch binding into task-keyed registry.

### Regression Tests

Add explicit tests for the current known failure classes:
- `TASK-1!` and `TASK-1?` must not share branch or worktree identity;
- a fresh worktree must be removable without force when untouched;
- startup cleanup must find a task worktree from the registry even if the display id slug changes;
- integration lookup must use the branch associated with `task_uid`, not a recomputed display-id branch.

### Migration Tests

Add tests for:
- existing card without `task_uid` is migrated once;
- legacy branch `orc/TASK-001` is bound to the new `task_uid`;
- ambiguous legacy match fails safely rather than attaching the wrong branch.

## Open Questions

- Should `task_uid` be exposed anywhere in the TUI detail panel for diagnostics, or stay fully operator-hidden unless debug mode is enabled?
- Should worktree path include a display slug for readability, or use only `uid12` for maximal determinism?
- Should ORC keep task branches forever as recovery artifacts, or should the registry track an archival state and allow branch retirement after verified integration?

## Expected Outcome

After this step:
- visible task ids stop acting as machine primary keys;
- branch and worktree collisions from lossy normalization disappear;
- worktree ownership survives session restarts and crashes;
- cleanup and recovery stop reconstructing ownership from slugs;
- ORC’s own ownership metadata no longer makes fresh worktrees dirty;
- integration, sweep, and recovery can all talk about the same task through one stable key.
