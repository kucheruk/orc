# orc.py Hook Workflow

This project runs a Cursor Agent against a backlog and relies on Cursor hooks to mark tasks complete and trigger follow-up actions. The script itself launches the agent and then waits for hooks to finish the task.

## Quick Start

### Prerequisites

- Python 3.8+
- Cursor IDE installed
- `ht` (headless terminal) installed (optional, but recommended)
- A repository with a `BACKLOG.md` file containing tasks with IDs

### First Time Setup

1. **Clone or download this repository:**
   ```bash
   git clone <repository-url>
   cd orc
   ```

2. **Configure Telegram notifications (optional):**
   ```bash
   mkdir -p .orc
   cp .orc/telegram.json.example .orc/telegram.json
   # Edit .orc/telegram.json and add your bot token and chat ID
   ```
   
   Or set environment variables:
   ```bash
   export ORC_TELEGRAM_TOKEN="your_bot_token"
   export ORC_TELEGRAM_CHAT_ID="your_chat_id"
   ```

3. **Prepare your target repository:**
   - Create a `BACKLOG.md` file with tasks in format:
     ```
     - [ ] TASK-01 First task description
     - [ ] TASK-02 Second task description
     ```
   - Each task must have a unique ID (uppercase letters, numbers, dashes, underscores)

4. **Run the orchestrator:**
   ```bash
   python3 orc.py --workspace /path/to/your/repo
   ```

   The orchestrator will:
   - Parse `BACKLOG.md` and find the first open task
   - Create necessary hook files in `.orc/` directory
   - Launch the Cursor agent to work on the task
   - Wait for completion and mark tasks as done automatically

## Files created per repo

When `orc.py` runs for a workspace, it creates these files inside that repository:

- `.orc/orc-task.json` - task state used by hooks
- `.orc/hooks/orc_before_submit.py` - hook for capturing `conversation_id`
- `.orc/hooks/orc_stop.py` - hook for marking tasks done + followup
- `.orc/hooks.json` - hook configuration for the repo
- `.orc/orc-hook.log` - hook debug log

If `.orc/orc-task.json` does not exist, the hooks do nothing and Cursor behaves normally.

## orc.py algorithm (high level)

1. Parse `BACKLOG.md` and find the first open task with a task ID.
2. If `.orc/orc-task.json` already exists:
   - Read the task from that file.
   - If the task is already marked `[x]` in `BACKLOG.md`, delete the task file and continue.
   - Otherwise, launch the agent in "continue" mode for the stored task.
3. If there is no active task file:
   - Create `.orc/orc-task.json` with `task_id`, `task_text`, `backlog_path`, and `workspace_root`.
   - Ensure hook scripts exist and that `.orc/hooks.json` includes them.
   - Launch the agent with the default prompt for that task.
4. Wait until `.orc/orc-task.json` is removed by the stop hook.
5. Repeat from step 1.

## Hook behavior

### beforeSubmitPrompt

Reads JSON from stdin, and if `.orc/orc-task.json` exists in the repo:

- Captures `conversation_id` from the hook payload
- Stores it in `.orc/orc-task.json` (if not already set)
- Logs to `.orc/orc-hook.log`

### stop

Reads JSON from stdin. If status is `completed`, and the task file exists:

- Verifies the conversation id matches (if present)
- Marks the matching ID line in `BACKLOG.md` as `[x]`
- Deletes `.orc/orc-task.json`
- Emits a follow-up JSON:
  ```
  {"followup_message":"commit+push with task ID and task description as commit message"}
  ```
- Logs details and early exits to `.orc/orc-hook.log`

## Troubleshooting

If a task completes but no follow-up happens or the task file is not removed:

1. Check `.orc/orc-hook.log` for hook activity and exit reasons.
2. Confirm `.orc/orc-task.json` has the right `task_id` and `backlog_path`.
3. Ensure the backlog line contains the same task ID in the `- [ ]` entry.
4. Verify `.orc/hooks.json` references the repo hook scripts.

## Usage

Run:

```
python3 orc.py --workspace /path/to/repo
```

Or with absolute path:

```
python3 /path/to/orc/orc.py --workspace /path/to/repo
```
