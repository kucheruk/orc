# Orchestrator Tech Spec (Hook-Based)

## Goal

Provide a reliable, repo-local orchestrator that runs a Cursor Agent against a backlog and advances tasks one-by-one. The orchestrator must avoid spawning multiple concurrent agents, must tolerate hook timing and conversation ID variability, and must never modify global Cursor hooks.

## Key Requirements

1. **Single active task at a time**
   - At most one active task file exists per repo.
   - If an active task exists, the orchestrator must resume/continue it, not start another.
   - If the active task is already `[x]`, the orchestrator must delete the task file and continue.

2. **Repo-local hooks only**
   - Hooks must be configured in `<repo>/.cursor/hooks.json`.
   - No writes to `~/.cursor/hooks/hooks.json`.

3. **Backlog by ID**
   - Each task line contains an ID in the checklist entry.
   - The orchestrator must match and mark tasks by ID, not by title text.

4. **Hook-driven completion**
   - The stop hook marks the backlog `[x]`, removes the task file, and triggers follow-up.
   - If the agent already set `[x]`, this is valid and must still remove the task file.

5. **Follow-up message**
   - On task completion, stop hook emits:
     ```json
     {"followup_message":"commit+push with task ID and task description as commit message"}
     ```

6. **Conversation ID mismatch tolerance**
   - Hooks must not fail the completion flow on conversation ID mismatch.
   - If mismatch occurs, log it but proceed.

7. **Robust logging**
   - Hook activity and early exits must be logged to `.orc/orc-hook.log`.
   - Log includes stop status, loop count, and mismatch events.

## Data Contracts

### Backlog Format

Checklist entries must contain an ID token:

```
- [ ] AUTH-03 Настроить cookie-сессии...
- [x] **BRAND-001: Применение Project Branding...**
```

ID regex (normalized):
```
(?:\*\*)?(?P<id>[A-Z][A-Z0-9_-]+)(?::)?(?:\*\*)?\s
```

### Task File

Path: `<repo>/.cursor/orc-task.json`

Example:
```json
{
  "version": 1,
  "task_id": "AUTH-03",
  "task_text": "AUTH-03 ...",
  "backlog_path": "/abs/path/BACKLOG.md",
  "workspace_root": "/abs/path",
  "conversation_id": "",
  "created_at": "2026-01-21T23:52:06"
}
```

### Runtime Task File

Path: `<repo>/.cursor/orc-task-runtime.json`

Example:
```json
{
  "version": 1,
  "task_id": "AUTH-03",
  "active_seconds": 0.0,
  "last_heartbeat_at": 0.0,
  "run_id": ""
}
```

### Hook Configuration

Path: `<repo>/.cursor/hooks.json`

Example:
```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      { "command": "python3 /path/to/repo/.cursor/hooks/orc_before_submit.py" }
    ],
    "stop": [
      { "command": "python3 /path/to/repo/.cursor/hooks/orc_stop.py" }
    ]
  }
}
```

### Hook Input/Output (Cursor)

**beforeSubmitPrompt input (stdin JSON)**
```json
{
  "conversation_id": "uuid",
  "generation_id": "uuid",
  "prompt": "string",
  "workspace_roots": ["..."],
  "hook_event_name": "beforeSubmitPrompt"
}
```

**stop input (stdin JSON)**
```json
{
  "status": "completed|aborted|error",
  "loop_count": 0,
  "conversation_id": "uuid",
  "workspace_roots": ["..."]
}
```

**stop output (stdout JSON)**
```json
{"followup_message":"commit+push with task ID and task description as commit message"}
```

## Orchestrator Workflow

1. Parse backlog.
2. Find first open task with ID.
3. If `.cursor/orc-task.json` exists:
   - Load task.
   - If that task is already `[x]`, delete file.
   - Otherwise run continue prompt for that task.
4. If no task file exists:
   - Create task file with ID and backlog path.
   - Create runtime task file for monitor heartbeat state.
   - Ensure repo hook scripts exist.
   - Ensure `<repo>/.cursor/hooks.json` has the hook entries.
   - Launch agent with default prompt.
5. Wait until `.cursor/orc-task.json` disappears (hook removes it).
6. Repeat from step 1.

## Hook Behavior

### orc_before_submit.py

- If task file is missing: exit.
- Else capture and store `conversation_id` if not already set.
- Does not modify runtime heartbeat file.
- Append to `.orc/orc-hook.log`:
  - `beforeSubmitPrompt`
  - `stored conversation_id=...`

### orc_stop.py

- If task file missing: log and exit.
- If status != completed: log and exit.
- If conversation ID mismatch: log but continue (no early exit).
- If task ID found in backlog:
  - Ensure the line is `[x]` (no title edits).
  - Read `active_seconds` from `.cursor/orc-task-runtime.json` (or `ORC_TASK_RUNTIME_FILE` override).
  - Delete `.cursor/orc-task.json`.
  - Delete `.cursor/orc-task-runtime.json`.
  - Emit followup JSON.
- If task ID not found: log and exit.

## Prompts

### Default prompt requirements
- Must reference `{backlog}` and `{task_id}`.
```
Открой @{backlog}
Найди пункт с ID {task_id}. Не выбирай другой ID.
```

### Continue prompt requirements
```
Продолжай выполнение ТОЙ ЖЕ задачи из BACKLOG.md. Ориентируйся на ID {task_id}.
Не переключайся на другие пункты {backlog}, пока этот не станет [x].
```

## Logging

File: `<repo>/.orc/orc-hook.log`

Minimum log events:
- beforeSubmitPrompt
- stored conversation_id
- stop status + loop_count
- stop: no task file
- stop: status not completed
- stop: conv mismatch (continuing)
- stop: marked <ID>
- stop: task not found in backlog

## Error Handling

- Malformed hook input: ignore.
- Malformed task file: log and ignore.
- Backlog parse failure: orchestrator exits with error.
- Hook exceptions must not crash Cursor; hook exits 0 after logging.

## Non-Goals

- No multi-task concurrency.
- No global hooks modifications.
- No assumptions about agent working directory beyond `workspace_root`.

## Stream-JSON Runtime (Mandatory)

ORC runs agents only through headless Cursor CLI stream output:

```bash
agent -p --force --output-format stream-json --stream-partial-output "<PROMPT>"
```

### Why stream-json

- Structured lifecycle events without terminal scraping.
- Stable machine-readable telemetry (`system`, `assistant`, `tool_call`, `result`).
- No external terminal wrappers or PTY-level dependencies.

### Lifecycle Signals

- **Started**: process spawned + first `system/init` event.
- **Running**: `assistant` and `tool_call` events arrive.
- **Finished Success**: `result` event with success subtype/status.
- **Finished Error**: `result` event with non-success status or early process exit.

### Constraints / Notes

- `stream-json` schema can evolve between CLI versions; parser must be tolerant to optional fields.
- Task completion remains hook-driven (`stop` marks backlog and removes task file).
- If `result success` observed but task file lingers, orchestrator invokes stop-hook fallback.

## Conversation Log Access (Unsupported)

Cursor does not expose a public API for conversation logs, but local storage exists on disk. This is **unsupported** and may change without notice. Use only for diagnostics.

### Local storage locations (macOS)

- `~/Library/Application Support/Cursor/User/workspaceStorage`
  - Each workspace has a hashed folder.
  - Chat data is stored in `state.vscdb` (SQLite).

### Access method (read-only)

1. Find the workspace folder under `workspaceStorage/` that corresponds to your repo.
   - Each folder has `workspace.json` with a `folder` field.
   - Example search (macOS):
     ```
     rg "file:///Users/<you>/work/zagzag" \
       ~/Library/Application\ Support/Cursor/User/workspaceStorage -g "workspace.json"
     ```
2. Open `state.vscdb` in that folder using SQLite.
3. The data lives in `ItemTable` and/or `cursorDiskKV`.

### Verified keys (2026-01, macOS)

In the `ItemTable`:
- `aiService.prompts` — JSON array of prompts submitted to the agent
- `aiService.generations` — JSON array of responses/generations
- `composer.composerData` — composer UI state (may include conversation metadata)

Example queries:
```
sqlite3 state.vscdb "SELECT key FROM ItemTable LIMIT 50;"
sqlite3 state.vscdb "SELECT typeof(value), length(value) FROM ItemTable WHERE key='aiService.prompts';"
sqlite3 state.vscdb "SELECT substr(value,1,800) FROM ItemTable WHERE key='aiService.generations';"
```

### Notes

- This path is **not** an official API and may break across versions.
- Some community tools/exporters read these SQLite files, but they are not guaranteed stable.

## Testing Checklist

1. Run orchestrator on repo with open task.
2. Verify `.cursor/orc-task.json` created.
3. Verify repo `.cursor/hooks.json` created.
4. Agent completes task:
   - backlog line `[x]`
   - task file deleted
   - followup message emitted
5. Confirm `.orc/orc-hook.log` includes full event chain.
6. Verify no global hook file is changed.
