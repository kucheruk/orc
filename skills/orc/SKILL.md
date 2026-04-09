---
name: orc
description: >
  Prepare any project for the ORC orchestrator and work with its kanban board model.
  Creates kanban board folder structure (tasks/ with 8 stage columns), slices specs/PRDs
  into backlog task cards with proper YAML frontmatter and 4-section markdown body,
  links cards to source specs, manages card lifecycle and board state.
  Use this skill whenever the user mentions ORC, orchestrator, kanban board setup,
  task cards, backlog preparation, slicing specs into tasks, "nарезать задачи",
  "подготовить проект под orc", "канбан", "бэклог", "тикеты", init-kanban,
  or wants to create/manage task cards in the tasks/ folder structure.
  Also use when user asks about ORC modes (orc/orcs/kanban), card format,
  WIP limits, pull system, roles, or board workflow.
---

# ORC Orchestrator Skill

ORC is an AI orchestrator with three modes:
- **orc** — single agent, sequential tasks from BACKLOG.md
- **orcs** — up to 4 parallel agents with AI conflict analysis
- **kanban** — virtual team of 7 AI roles on a pull-based kanban board

This skill focuses on the **kanban model** — preparing projects and managing the board.

## Quick Reference

```
orc --init-kanban --workspace .   # create tasks/ folder structure
orc --mode kanban --workspace .   # run kanban orchestrator
```

---

## 1. Preparing a Project for ORC Kanban

A project ready for kanban needs this structure:

```
project/
├── tasks/                    # kanban board (created by init or by you)
│   ├── 1_Inbox/              # new ideas, no WIP limit
│   ├── 2_Estimate/           # architect estimation, _index.md
│   ├── 3_Todo/               # backlog ready for coding, wip=5
│   ├── 4_Coding/             # in progress, wip=3
│   ├── 5_Review/             # code review, wip=3
│   ├── 6_Testing/            # QA, wip=3
│   ├── 7_Handoff/            # integration to main, wip=2
│   └── 8_Done/               # completed, .gitkeep
├── PRD.md                    # product requirements (optional, used by Product role)
├── TECHSPEC.md               # technical spec (optional, used by Architect/Coder)
├── AGENTS.md                 # agent rules (recommended)
└── BACKLOG.md                # only needed for orc/orcs modes, NOT kanban
```

### Creating the Board Structure

Create folders and WIP-limit index files:

```
tasks/1_Inbox/
tasks/2_Estimate/_index.md    → ---\nstage: 2_Estimate\nwip_limit: 5\n---
tasks/3_Todo/_index.md        → ---\nstage: 3_Todo\nwip_limit: 5\n---
tasks/4_Coding/_index.md      → ---\nstage: 4_Coding\nwip_limit: 3\n---
tasks/5_Review/_index.md      → ---\nstage: 5_Review\nwip_limit: 3\n---
tasks/6_Testing/_index.md     → ---\nstage: 6_Testing\nwip_limit: 3\n---
tasks/7_Handoff/_index.md     → ---\nstage: 7_Handoff\nwip_limit: 2\n---
tasks/8_Done/.gitkeep
```

WIP limits are configurable per project — edit the `wip_limit` value in each `_index.md`.

---

## 2. Slicing Specs into Task Cards (Primary Workflow)

This is the core workflow: take project specs (PRD, TECHSPEC, design docs, feature descriptions) and produce a backlog of kanban cards.

### Step-by-step

1. **Read all spec files** in the project — PRD.md, TECHSPEC.md, any docs/ folder, README sections describing features. Understand the full scope.

2. **Identify natural task boundaries.** A good task is:
   - Independently deliverable (can be coded, reviewed, tested, merged on its own)
   - Small enough for one agent session (ideally 1-4 hours of coding work)
   - Has clear acceptance criteria derivable from the spec
   - Does not require more than 2-3 files to change (guideline, not hard rule)

3. **Determine task ordering and dependencies.** If task B needs types/interfaces defined in task A, mark `dependencies: [TASK-A-ID]`. The board will not allow a card with unmet dependencies to be picked for coding.

4. **Generate card IDs.** Use a consistent prefix based on the project or feature area:
   - `AUTH-001`, `AUTH-002` for authentication tasks
   - `API-001`, `API-002` for API tasks
   - `TASK-001`, `TASK-002` as a generic fallback
   - IDs must be uppercase letters, digits, and hyphens

5. **Write each card** as a markdown file in `tasks/1_Inbox/` with `action: Product` and `stage: 1_Inbox`. Leave `value_score: 0` and `effort_score: 0` — the AI Product and Architect roles will fill these as the card progresses through the pipeline.

6. **Link to source spec.** In the `# 1. Product Requirements` section, reference the exact spec section/paragraph the task comes from. Use a clear citation format:
   ```
   Source: PRD.md, section "User Authentication"
   Source: TECHSPEC.md, sections "API Gateway" + "Rate Limiting"
   ```

### Where to Place Cards

- **`tasks/1_Inbox/`** (recommended, default) — the card enters the full pipeline: Product scores value, sets class of service, writes acceptance criteria; then Architect designs solution and estimates effort. This is the right choice for any new task sliced from specs.

- **`tasks/2_Estimate/`** — requirements are already clear and section 1 is filled, but you want the Architect to write technical design and estimate effort. Set `action: Architect` and `stage: 2_Estimate`.

- **`tasks/3_Todo/`** (skip pipeline — only if all sections pre-filled) — use only when the user explicitly asks to skip Product/Architect evaluation, or when sections 1 and 2 are already fully written with acceptance criteria, technical design, DoD, and both `value_score` and `effort_score` are set. Set `action: Coding` and `stage: 3_Todo`.

---

## 3. Card Format

Every card is a markdown file with YAML frontmatter. The primary example is an Inbox card entering the full pipeline:

```yaml
---
id: AUTH-001
title: Implement OAuth2 login flow
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
created_at: '2026-04-09T10:00:00+00:00'
updated_at: '2026-04-09T10:00:00+00:00'
---

# 1. Product Requirements

Source: PRD.md, section "User Authentication"

Implement OAuth2 login with GitHub and Google providers.

Key points from spec:
- Login page at /login with provider selection
- OAuth redirect flow with PKCE
- Session tokens stored in httpOnly cookies
- Logout endpoint clears session
- Error handling for denied/expired auth

# 2. Technical Design & DoD

(filled by Architect role during Estimate stage)

# 3. Implementation Notes

(filled by Coder during implementation)

# 4. Feedback & Checklist

(filled by Reviewer/Tester with issues found)
```

**Alternative: card placed directly in Todo** (only if user explicitly asked to skip the pipeline and sections 1-2 are fully pre-filled):

```yaml
---
id: AUTH-001
title: Implement OAuth2 login flow
stage: 3_Todo
action: Coding
class_of_service: standard
cos_justification: ''
deadline: ''
value_score: 80
effort_score: 30
roi: 2.67
dependencies: []
loop_count: 0
assigned_agent: ''
created_at: '2026-04-09T10:00:00+00:00'
updated_at: '2026-04-09T10:00:00+00:00'
---
# (sections 1 and 2 must be fully filled before placing in Todo)
```
```

### Frontmatter Fields

| Field | Type | When to Set | Description |
|-------|------|-------------|-------------|
| `id` | string | Always | Unique task ID, uppercase + digits + hyphens |
| `title` | string | Always | Short description (one line) |
| `stage` | string | Always | Must match the folder name: `1_Inbox`, `3_Todo`, etc. |
| `action` | enum | Always | Current work type (see Actions below) |
| `class_of_service` | enum | Inbox/Todo | `standard`, `expedite`, `fixed-date`, `intangible` |
| `cos_justification` | string | If expedite | Why this is urgent |
| `deadline` | YYYY-MM-DD | If fixed-date | Hard deadline |
| `value_score` | 0-100 | Inbox/Todo | Business value (set by Product or manually) |
| `effort_score` | 0-100 | Estimate/Todo | Implementation effort (set by Architect or manually) |
| `roi` | float | Auto | value_score / effort_score, computed by board |
| `dependencies` | list | If needed | IDs of tasks that must be Done before this one starts |
| `loop_count` | int | 0 | Incremented when sent back from Review/Testing to Coding |
| `assigned_agent` | string | Leave empty | Set by orchestrator at runtime |
| `created_at` | ISO datetime | Always | When the card was created |
| `updated_at` | ISO datetime | Always | Last modification time |

### Actions

| Action | Meaning | Set by |
|--------|---------|--------|
| `Product` | Needs product evaluation | Initial / Architect returning |
| `Architect` | Needs technical design | Product role |
| `Coding` | Ready for implementation | Product / Reviewer / Tester (returning) |
| `Reviewing` | Ready for code review | Coder |
| `Testing` | Ready for QA | Coder / Reviewer |
| `Integrating` | Ready to merge to main | Tester |
| `Done` | Completed | Integrator |
| `Blocked` | Needs human intervention | Teamlead (loop_count >= 4) |
| `Arbitration` | Teamlead breaking deadlock | System (loop_count >= 2) |

### Class of Service (Priority)

Cards are picked in this priority order: `expedite` > `fixed-date` (by deadline) > `standard` (by ROI) > `intangible`.

- **expedite** — drop everything, do this now. Requires `cos_justification`.
- **fixed-date** — has a hard deadline. Requires `deadline` field.
- **standard** — normal priority, sorted by ROI (higher = picked first).
- **intangible** — tech debt, refactoring, nice-to-haves. Picked last.

---

## 4. Workflow: How Cards Move Through the Board

The board is a **pull system** — workers look for work right-to-left (from Handoff toward Inbox), prioritizing cards closest to Done.

```
1_Inbox ──→ 2_Estimate ──→ 3_Todo ──→ 4_Coding ──→ 5_Review ──→ 6_Testing ──→ 7_Handoff ──→ 8_Done
 Product      Architect     (queue)     Coder        Reviewer      Tester       Integrator
```

Cards move automatically when an agent changes the `action` field:
- Coder sets `action: Reviewing` → card moves from 4_Coding to 5_Review
- Reviewer sets `action: Testing` → card moves to 6_Testing
- Reviewer sets `action: Coding` → card goes back, loop_count increments

### Feedback Loops

- Reviewer finds issues → sets `action: Coding`, writes checklist in section 4 → card returns to coder
- Tester finds bugs → sets `action: Coding`, writes bug report in section 4 → card returns to coder
- Each return increments `loop_count`
- `loop_count >= 2` → Teamlead arbitrates
- `loop_count >= 4` → card blocked, Telegram notification, human intervention needed

### 7 Roles and Their Prompts

Each role has a prompt template in `prompts/kanban_<role>.txt` that gets injected with the current board state and card content. The ORC installation at `/Users/vetinary/work/orc` contains all prompts.

| Role | Prompt file | Gets worktree? |
|------|-------------|----------------|
| Product | `kanban_product.txt` | No |
| Architect | `kanban_architect.txt` | No |
| Coder | `kanban_coder.txt` | Yes |
| Reviewer | `kanban_reviewer.txt` | No |
| Tester | `kanban_tester.txt` | Yes |
| Integrator | `kanban_integrator.txt` | No |
| Teamlead | `kanban_teamlead.txt` | No |

---

## 5. Practical Patterns

### Pattern A: Fresh project with specs → full kanban backlog (default)

This is the standard entry point and should be used unless the user explicitly asks otherwise. Spec documents go in, a working board comes out.

1. Create the board structure (all 8 stage folders + _index.md files)
2. Read specs thoroughly
3. Slice into tasks, write cards into `tasks/1_Inbox/` with `action: Product`, `stage: 1_Inbox`
4. Each card's `# 1. Product Requirements` section quotes/references the relevant spec section
5. Leave `value_score: 0`, `effort_score: 0` — the Product and Architect AI roles will fill these as the card flows through Inbox → Estimate → Todo
6. Run `orc --mode kanban` — the AI team takes over: Product scores value, Architect designs and estimates, then the card enters the coding pipeline with full context

### Pattern B: Skip pipeline → Todo (exception, only on explicit request)

Use only when the user explicitly asks to skip Product/Architect evaluation, or when tasks are already fully specified with sections 1 and 2 completely filled, value and effort scored. If sections are empty, the card will reach the Coder with no design or DoD — this leads to poor results.

1. Create board structure
2. Write cards into `tasks/3_Todo/` with `action: Coding`, `stage: 3_Todo`
3. You must fill `value_score` and `effort_score` yourself (needed for ROI prioritization)
4. You must fill sections 1 and 2 of the card body completely (requirements + technical design + DoD)
5. Run `orc --mode kanban`

### Pattern C: Existing BACKLOG.md → convert to kanban cards

When migrating from orc/orcs mode:

1. Read BACKLOG.md, parse each `- [ ] TASK-ID description` line
2. Create a card for each open task in `tasks/1_Inbox/`
3. Copy task description into `# 1. Product Requirements`
4. Preserve the original task ID

### Pattern D: Add tasks to a running board

While kanban is running, you can add tasks via TUI input or by creating files in `tasks/1_Inbox/`. Use the next available ID (check existing cards to find the highest number).

---

## 6. Tips for Good Task Decomposition

**Right-sized tasks** complete in one coding session. Signs a task is too big:
- Touches more than 5 files
- Has more than 8 acceptance criteria
- Description is longer than a paragraph
- You'd naturally say "first do X, then do Y" — that's two tasks

**Right-sized tasks** are not too small either. Signs a task is too granular:
- "Add import statement" or "rename variable" — too trivial
- Can be done as part of a neighboring task
- Has no independently testable acceptance criteria

**Dependencies** should be minimal. If task B depends on task A, B cannot start until A reaches 8_Done. Prefer designing tasks that can run in parallel. Common dependency patterns:
- Database schema migration must precede code that uses new columns
- Shared interfaces/types must precede consumers
- Config/infrastructure before features that use them

**Spec linking** makes the board traceable. Every card should reference its source:
```markdown
# 1. Product Requirements

Source: TECHSPEC.md, section "Payment Processing", paragraphs 3-5
Source: PRD.md, requirement REQ-042

[Then restate the requirements in your own words as acceptance criteria]
```

---

## 7. ORC Modes Comparison

| | orc | orcs | kanban |
|---|---|---|---|
| Sessions | 1 | up to 4 | up to 4 |
| Task source | BACKLOG.md | BACKLOG.md | tasks/ folders |
| Distribution | Sequential | AI conflict analysis | Pull right-to-left |
| Roles | Coder only (+ optional review/test) | Coder only (+ optional) | 7 specialized roles |
| Quality gates | Optional | Optional | Built-in (review + test loops) |
| Human input | Minimal | Minimal | /unblock for blocked cards |
| Best for | Simple task lists | Parallel independent tasks | Complex projects needing design/review/test |

---

## 8. Running ORC

```bash
# Install (from orc repo)
cd /Users/vetinary/work/orc && uv tool install --editable .

# Initialize kanban board in target project
orc --init-kanban --workspace /path/to/project

# Start kanban mode
orc --mode kanban --workspace /path/to/project

# With specific model
orc --mode kanban --workspace /path/to/project --model claude-sonnet-4-6

# With more/fewer parallel workers
orc --mode kanban --workspace /path/to/project --max-sessions 2

# Test Telegram notifications
orc --telegram-test
```

### TUI Controls (Kanban Mode)

- **Columns**: 8 columns showing cards with ID, action, agent, timer, ROI
- **Metrics bar**: Lead Time, Throughput, Total/Done/Blocked cards
- **Decision Journal**: Event feed (moves, completions, escalations)
- **Chat input**: Type card title to add to Inbox, or `/unblock TASK-ID directive`
- **Keys**: Escape=quit, T=toggle theme
