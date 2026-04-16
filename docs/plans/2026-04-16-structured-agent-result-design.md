# Step 1 Design: Structured Agent Result Instead Of Card Mutation

## Context

The current kanban runtime uses the task card markdown file as all of the following at once:
- the human-readable task document;
- the agent-facing work contract;
- the IPC channel between agent and orchestrator;
- the source of truth for the next state transition.

This coupling created the split-brain failure class already visible in the autonomy ledger:
- agent writes the worktree-local card copy, while ORC may read the canonical card in the base repo;
- stage moves can happen while the agent is still editing an older path;
- stale worktree card copies can survive stage moves;
- a completed agent output can apply after the canonical card state already changed.

The first architectural step is to remove the card markdown file from the control plane.

## Goal

Introduce a structured, deterministic agent result artifact so that:
- ORC remains the only writer of canonical card state in `tasks/`;
- agents report intent through a dedicated result file, not by mutating task markdown;
- result application is validated against the launch snapshot before any board mutation happens;
- card markdown becomes a projection rendered by ORC from canonical state.

## Non-Goals

Out of scope for this step:
- replacing the legacy backlog-based execution engine;
- redesigning task/worktree identity (`task_uid`, branch naming);
- replacing teamlead imperative actions with a unified lifecycle service;
- removing markdown cards from the repository.

This step only changes how agent output is returned to ORC.

## Target Invariants

After this step:
- agents never write `tasks/**/*.md`;
- canonical card files are written only by ORC;
- one agent run produces exactly one result artifact;
- the result artifact is applied only if the canonical card still matches the launch fingerprint;
- missing or invalid result artifacts fail the run instead of silently falling back to card reads;
- worktree card copies are no longer part of the state transition mechanism.

## High-Level Design

### New Output Contract

For each agent run, ORC creates a deterministic result file path and passes it to the agent via:
- prompt instructions;
- environment variable `ORC_AGENT_RESULT_FILE`.

The agent must write a single JSON document to that path before exiting successfully.

ORC then:
1. reads the result artifact;
2. validates schema and role-specific permissions;
3. verifies that the canonical card still matches the launch fingerprint;
4. applies the result to canonical in-memory state;
5. renders the updated canonical card back into `tasks/`.

At no point does ORC infer state transitions by re-reading a card file modified by the agent.

### Read Model vs Write Model

The step introduces a clean split:

- Read model for humans: markdown card in `tasks/`.
- Write model for agents: structured JSON result artifact in `.orc/.../results/`.

The markdown card remains important, but it is no longer used as a mutable protocol surface.

## Result Artifact

### Location

Store artifacts under the existing per-run root:

```text
<run_root>/results/<task-id>__<stage-id>__attempt-<n>.json
```

Where:
- `run_root` is already created for the kanban session;
- `task-id` is the visible card id for now;
- `stage-id` is the current execution stage label;
- `attempt` is the restart attempt number for that run.

This keeps artifacts grouped with the rest of runtime state and avoids coupling them to `tasks/`.

### Schema v1

Proposed minimal schema:

```json
{
  "schema_version": 1,
  "task_id": "AUTH-001",
  "role": "coder",
  "run_id": "s2:AUTH-001:attempt-1",
  "launch_fingerprint": {
    "stage": "4_Coding",
    "action": "Coding",
    "file_path": "tasks/4_Coding/AUTH-001.md",
    "updated_at": "2026-04-16T12:31:10+00:00"
  },
  "result": {
    "next_action": "Reviewing",
    "field_updates": {
      "title": "optional",
      "effort_score": 34,
      "dependencies": ["TASK-001"]
    },
    "section_updates": {
      "product_requirements": "markdown",
      "technical_design": "markdown",
      "implementation_notes": "markdown",
      "feedback_checklist": "markdown"
    },
    "summary": "short completion summary"
  }
}
```

### Notes

- `schema_version` allows future incompatible upgrades.
- `launch_fingerprint` makes stale writes explicit and machine-checkable.
- `field_updates` contains only structured, typed changes to canonical card fields.
- `section_updates` contains markdown fragments for well-known body sections.
- `summary` is optional, intended for logs and notifications.

## Section Update Model

The card body should stop being treated as opaque markdown edited by the agent.
Instead, ORC owns the body layout and exposes only logical section keys:

- `product_requirements`
- `technical_design`
- `implementation_notes`
- `feedback_checklist`

ORC will:
1. parse the current canonical card body into named sections;
2. replace only the sections present in `section_updates`;
3. render the full body back through a deterministic serializer.

This preserves human-readable cards without letting the agent arbitrarily rewrite the whole file.

## Role Permissions

The existing role restrictions should move from “validate after free-form markdown mutation” to “validate before apply”.

### Product

Allowed:
- `next_action`: `Architect` or `Coding`
- `field_updates`: title, class_of_service, cos_justification, deadline, value_score
- `section_updates`: product_requirements, feedback_checklist

### Architect

Allowed:
- `next_action`: `Product`, `Coding`, `Blocked`
- `field_updates`: effort_score, dependencies
- `section_updates`: technical_design, feedback_checklist

### Coder

Allowed:
- `next_action`: `Reviewing`, `Testing`
- `section_updates`: implementation_notes, feedback_checklist

### Reviewer

Allowed:
- `next_action`: `Testing`, `Coding`
- `section_updates`: feedback_checklist

### Tester

Allowed:
- `next_action`: `Integrating`, `Coding`, `Reviewing`
- `section_updates`: feedback_checklist

### Integrator

Allowed:
- `next_action`: `Done`, `Reviewing`, `Testing`, `Coding`
- `section_updates`: feedback_checklist

Any field or section outside the role contract is rejected as a validation error.

## Orchestrator Flow

### Before Launch

Worker prepares:
- canonical card snapshot;
- launch fingerprint `(stage, action, file_path, updated_at)`;
- result artifact path;
- prompt block describing the strict JSON contract.

Worker no longer needs `process_agent_result()` to search the worktree for card files.

### During Agent Run

The agent:
- edits source files in the worktree;
- does not edit `tasks/**/*.md`;
- writes the result JSON to `ORC_AGENT_RESULT_FILE`.

### After Completion

The worker:
1. checks whether the canonical card still matches the launch fingerprint;
2. loads the result artifact;
3. validates schema;
4. validates role permissions and transition rules;
5. applies structured updates to canonical state;
6. persists the canonical card through the board repository;
7. continues with delivery checks, integration flow, token accounting.

If the fingerprint changed, the result is discarded as stale without reading any task markdown from the worktree.

## Prompt Contract

Each role prompt should gain a short deterministic output section:

```text
You must not edit tasks/*.md.
Write your final structured result as JSON to:
<absolute path>

Required top-level keys:
- schema_version
- task_id
- role
- run_id
- launch_fingerprint
- result
```

The prompt should include:
- allowed `next_action` values for the current role;
- allowed `field_updates` keys;
- allowed `section_updates` keys;
- instruction to fail fast rather than invent unsupported fields.

## Implementation Outline

### New Modules

Add:
- `orc_core/agents/result_schema.py`
  - dataclasses / typed payload parsing for schema v1
- `orc_core/agents/result_io.py`
  - deterministic path builder, atomic read/write helpers
- `orc_core/agents/result_apply.py`
  - validate + apply result to canonical `KanbanCard`
- `orc_core/board/card_sections.py`
  - parse/render named markdown sections

### Existing Modules To Shrink

Refactor:
- `orc_core/agents/infra/agent_output.py`
  - remove worktree card read path and markdown diff-based application
- `orc_core/agents/runners/worker.py`
  - prepare result path and launch fingerprint
- `orc_core/agents/roles.py` and `prompts/kanban_*.txt`
  - emit new output contract
- `orc_core/git/worktree_card_sync.py`
  - likely removable after migration

## Failure Handling

The new contract should be fail-fast:

- missing result file => failed run;
- invalid JSON => failed run;
- wrong `task_id` / `role` / `run_id` => failed run;
- disallowed field updates => failed run;
- invalid transition => failed run;
- stale launch fingerprint => discard result, keep canonical state.

This is intentionally strict. Silent interpretation of partial markdown edits is exactly what created the current bug class.

## Migration Plan

### Phase 1

Introduce the structured artifact path and validator without changing the rest of kanban state logic.

Changes:
- worker passes `ORC_AGENT_RESULT_FILE`;
- prompts instruct the agent to write the artifact and stop editing cards;
- ORC applies the structured result to canonical cards;
- worktree card scanning is removed from the apply path.

### Phase 2

Delete the old markdown-mutation path.

Changes:
- remove worktree card sync from the control plane;
- remove legacy `process_agent_result()` behavior that re-reads card markdown from worktree;
- keep markdown cards only as rendered projections.

There should be no long-lived dual-write mode.

## Testing Strategy

### Unit Tests

Add coverage for:
- valid result artifact application for each role;
- rejection of unsupported field updates;
- rejection of invalid transitions;
- stale fingerprint discard;
- deterministic section rendering;
- missing result file and malformed JSON.

### Integration Tests

Add kanban worker tests for:
- coder writes code + result artifact, card moves to Review without reading worktree card;
- reviewer loop-back increments `loop_count`;
- integrator `Done` still remains gated by integration;
- card changed mid-run causes stale result discard.

### Regression Tests

Cover ledger-derived failure modes:
- no re-read from stale worktree stage path;
- no loss of agent feedback when canonical card moved;
- no card mutation when the artifact belongs to another run.

## Open Questions

- Should `updated_at` be part of the launch fingerprint, or should ORC use a dedicated monotonic `state_version` field on cards?
- Should `section_updates` allow append semantics for feedback, or only full section replacement?
- Should teamlead arbitration adopt the same result artifact in this step, or only after worker roles are stable?

## Expected Outcome

After this step, the most expensive current bug family should disappear:
- no agent feedback silently lost because ORC read the wrong card file;
- no state transition inferred from stale worktree markdown;
- no need to sync canonical card copies into worktree for correctness;
- much smaller surface area for later work on kanban-native runtime and unified lifecycle rules.
