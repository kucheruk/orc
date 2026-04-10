---
name: orc-repo-init
description: >
  Initialize any project directory for ORC kanban orchestration — from zero to a working board
  in one step. Checks git status, reads a spec/PRD/plan file, slices it into kanban task cards,
  creates the full board folder structure, and gives launch instructions.
  Use this skill when the user says "подготовь проект под orc", "init orc", "настрой orc",
  "создай канбан доску", "нарежь задачи", "prepare for orc", "set up orc", "orc init",
  "initialize orc board", "slice into tasks", "create board from spec", or wants to go from
  a spec/PRD/plan to a running ORC kanban board. Also use when the user opens a new project
  and mentions ORC or kanban setup. This skill is the entry point — use it even if the user
  just says "orc" in a non-ORC repo with no tasks/ folder.
---

# ORC Repo Init — from spec to running board

This skill walks through 4 steps to prepare any project directory for ORC kanban orchestration.
Execute them in order, pausing to ask the user when indicated.

## Step 1: Git check

ORC requires a git repository (it uses worktrees for isolated coding).

Run `git rev-parse --is-inside-work-tree 2>/dev/null` in the current working directory.

**If it IS a git repo:** confirm and continue to step 2.

**If it is NOT a git repo:** tell the user:

> This directory is not a git repository. ORC needs git for worktree isolation — each coding
> task runs in its own branch so that parallel agents don't conflict.
>
> Want me to run `git init` and create an initial commit?

If user agrees — run `git init`, create `.gitignore` (with sensible defaults for the project
type if detectable, otherwise a minimal one with `.orc/`, `__pycache__/`, `.env`), stage all
files, and commit with message "Initial commit". Then continue.

If user declines — explain that ORC cannot run without git and stop.

## Step 2: Find the spec

Ask the user:

> Which file contains the specification, PRD, or task plan? Give me the filename
> (e.g., `PRD.md`, `TECHSPEC.md`, `spec.md`, `TODO.md`, `tasks.txt`).
>
> I accept any format: markdown, plain text, YAML, or even a pasted list of tasks.

If the user names a file — read it fully.
If the user pastes text directly — use that as the spec content.
If the user says they don't have one — offer to interview them about their project (ask what
they're building, what the key features are, what the tech stack is) and compose a minimal
spec from their answers before proceeding.

## Step 3: Slice and create the board

### 3a. Create board folder structure

Create the full kanban board structure in `tasks/`:

```
tasks/
  1_Inbox/
  2_Estimate/
    _index.md    (stage: 2_Estimate, wip_limit: 5)
  3_Todo/
    _index.md    (stage: 3_Todo, wip_limit: 5)
  4_Coding/
    _index.md    (stage: 4_Coding, wip_limit: 3)
  5_Review/
    _index.md    (stage: 5_Review, wip_limit: 3)
  6_Testing/
    _index.md    (stage: 6_Testing, wip_limit: 3)
  7_Handoff/
    _index.md    (stage: 7_Handoff, wip_limit: 2)
  8_Done/
    .gitkeep
```

Each `_index.md` has YAML frontmatter:

```yaml
---
stage: 3_Todo
wip_limit: 5
---
```

### 3b. Choose card ID prefix

Pick a short uppercase prefix that reflects the project or feature area.
Examples: `BE-` for backend, `FE-` for frontend, `API-`, `AUTH-`, `INFRA-`.
If the spec covers multiple areas, use area-based prefixes. If unclear, use `TASK-`.

Number cards sequentially with zero-padded 3-digit numbers: `BE-001`, `BE-002`, etc.

### 3c. Slice the spec into task cards

Read the spec and break it into independently deliverable tasks. Good tasks:

- Can be coded, reviewed, tested, and merged on their own
- Take roughly 1-4 hours of coding work for one agent
- Touch no more than 3-5 files (guideline, not rule)
- Have clear, testable acceptance criteria

Think about ordering and dependencies:
- Infrastructure/config tasks before features that use them
- Shared types/interfaces before consumers
- Database schema before code that queries it
- Mark dependencies explicitly: `dependencies: [BE-001]`
- Minimize dependencies — prefer tasks that can run in parallel

### 3d. Write each card

Write each card as a `.md` file in `tasks/1_Inbox/` with this exact format:

```yaml
---
id: BE-001
title: Short one-line description of the task
stage: 1_Inbox
action: Product
class_of_service: standard
cos_justification: ''
deadline: ''
value_score: 0
effort_score: 0
roi: 0.0
dependencies: []
loop_count: 0
assigned_agent: ''
created_at: 'YYYY-MM-DDTHH:MM:SS+00:00'
updated_at: 'YYYY-MM-DDTHH:MM:SS+00:00'
---

# 1. Product Requirements

Source: <spec filename>, section "<section name>"

<Restate the relevant requirements as clear acceptance criteria.
Quote or reference specific paragraphs from the spec.
This section tells the AI Product role what the task delivers and why it matters.>

# 2. Technical Design & DoD

(filled by Architect role during Estimate stage)

# 3. Implementation Notes

(filled by Coder during implementation)

# 4. Feedback & Checklist

(filled by Reviewer/Tester with issues found)
```

Important rules:
- `stage` must be `1_Inbox` and `action` must be `Product` — the AI team will handle scoring and design
- Leave `value_score: 0` and `effort_score: 0` — Product and Architect roles will set these
- `created_at` and `updated_at` use current UTC time in ISO format
- Fill section 1 thoroughly — this is the only context the AI Product role gets
- Sections 2-4 stay empty with placeholder text (AI roles fill them as the card flows)

## Step 4: Report and instruct

After all cards are created, output a summary report:

```
## Board ready

Created N task cards in tasks/1_Inbox/:

| ID      | Title                        | Dependencies |
|---------|------------------------------|-------------|
| BE-001  | Bootstrap ASP.NET project    | —           |
| BE-002  | Add database schema          | BE-001      |
| BE-003  | Implement user API           | BE-002      |
| ...     | ...                          | ...         |

Dependency graph: BE-001 → BE-002 → BE-003, BE-004
                  BE-001 → BE-005

## How to run

1. Install ORC (if not installed):
   cd /Users/vetinary/work/orc && uv tool install --editable .

2. Launch the kanban board:
   orc --mode kanban --workspace <project-path>

   This starts a virtual team of 7 AI roles:
   Product → Architect → Coder → Reviewer → Tester → Integrator
   with a Teamlead that arbitrates deadlocks.

3. Watch the TUI — cards flow from Inbox through the pipeline to Done.
   The AI team will score value, design solutions, write code, review,
   test, and merge to main automatically.

4. If a card gets stuck (loop_count >= 4), you'll get a Telegram notification.
   Use /unblock TASK-ID in the TUI chat to intervene.

## Optional: choose backend and model

   orc --mode kanban --workspace . --backend claude --model claude-sonnet-4-6
   orc --mode kanban --workspace . --backend cursor
   orc --mode kanban --workspace . --backend codex

Backends: cursor (default), claude, codex
```

Adjust the installation path, project path, and card table to match actuals.
