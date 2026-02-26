# Hooks

Hooks let you observe, control, and extend the agent loop using custom scripts. Hooks are spawned processes that communicate over stdio using JSON in both directions. They run before or after defined stages of the agent loop and can observe, block, or modify behavior.

[Media](/docs-static/images/agent/hooks.mp4)

With hooks, you can:

- Run formatters after edits
- Add analytics for events
- Scan for PII or secrets
- Gate risky operations (e.g., SQL writes)
- Control subagent (Task tool) execution
- Inject context at session start

Looking for ready-to-use integrations? See [Partner Integrations](https://cursor.com/docs/agent/hooks.md#partner-integrations) for security, governance, and secrets management solutions from our ecosystem partners.

Cursor supports loading hooks from third-party tools like Claude Code. See [Third Party Hooks](https://cursor.com/docs/agent/third-party-hooks.md) for details on compatibility and configuration.

## Agent and Tab Support

Hooks work with both **Cursor Agent** (Cmd+K/Agent Chat) and **Cursor Tab** (inline completions), but they use different hook events:

**Agent (Cmd+K/Agent Chat)** uses the standard hooks:

- `sessionStart` / `sessionEnd` - Session lifecycle management
- `preToolUse` / `postToolUse` / `postToolUseFailure` - Generic tool use hooks (fires for all tools)
- `subagentStart` / `subagentStop` - Subagent (Task tool) lifecycle
- `beforeShellExecution` / `afterShellExecution` - Control shell commands
- `beforeMCPExecution` / `afterMCPExecution` - Control MCP tool usage
- `beforeReadFile` / `afterFileEdit` - Control file access and edits
- `beforeSubmitPrompt` - Validate prompts before submission
- `preCompact` - Observe context window compaction
- `stop` - Handle agent completion
- `afterAgentResponse` / `afterAgentThought` - Track agent responses

**Tab (inline completions)** uses specialized hooks:

- `beforeTabFileRead` - Control file access for Tab completions
- `afterTabFileEdit` - Post-process Tab edits

These separate hooks allow different policies for autonomous Tab operations versus user-directed Agent operations.

## Quickstart

Create a `hooks.json` file. You can create it at the project level (`<project>/.cursor/hooks.json`) or in your home directory (`~/.cursor/hooks.json`). Project-level hooks apply only to that specific project, while home directory hooks apply globally.

### User hooks (\~/.cursor/)

For user-level hooks that apply globally, create `~/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": "./hooks/format.sh" }]
  }
}
```

Create your hook script at `~/.cursor/hooks/format.sh`:

```bash
#!/bin/bash
# Read input, do something, exit 0
cat > /dev/null
exit 0
```

Make it executable:

```bash
chmod +x ~/.cursor/hooks/format.sh
```

### Project hooks (.cursor/)

For project-level hooks that apply to a specific repository, create `<project>/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": ".cursor/hooks/format.sh" }]
  }
}
```

Note: Project hooks run from the **project root**, so use `.cursor/hooks/format.sh` (not `./hooks/format.sh`).

Create your hook script at `<project>/.cursor/hooks/format.sh`:

```bash
#!/bin/bash
# Read input, do something, exit 0
cat > /dev/null
exit 0
```

Make it executable:

```bash
chmod +x .cursor/hooks/format.sh
```

Restart Cursor. Your hook now runs after every file edit.

## Hook Types

Hooks support two execution types: command-based (default) and prompt-based (LLM-evaluated).

### Command-Based Hooks

Command hooks execute shell scripts that receive JSON input via stdin and return JSON output via stdout.

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./scripts/approve-network.sh",
        "timeout": 30,
        "matcher": "curl|wget|nc"
      }
    ]
  }
}
```

**Exit code behavior:**

- Exit code `0` - Hook succeeded, use the JSON output
- Exit code `2` - Block the action (equivalent to returning `permission: "deny"`)
- Other exit codes - Hook failed, action proceeds (fail-open by default)

### Prompt-Based Hooks

Prompt hooks use an LLM to evaluate a natural language condition. They're useful for policy enforcement without writing custom scripts.

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "type": "prompt",
        "prompt": "Does this command look safe to execute? Only allow read-only operations.",
        "timeout": 10
      }
    ]
  }
}
```

**Features:**

- Returns structured `{ ok: boolean, reason?: string }` response
- Uses a fast model for quick evaluation
- `$ARGUMENTS` placeholder is auto-replaced with hook input JSON
- If `$ARGUMENTS` is absent, hook input is auto-appended
- Optional `model` field to override the default LLM model

## Examples

The examples below use `./hooks/...` paths, which work for **user hooks** (`~/.cursor/hooks.json`) where scripts run from `~/.cursor/`. For **project hooks** (`<project>/.cursor/hooks.json`), use `.cursor/hooks/...` paths instead since scripts run from the project root.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "./hooks/session-init.sh"
      }
    ],
    "sessionEnd": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./hooks/audit.sh"
      },
      {
        "command": "./hooks/block-git.sh"
      }
    ],
    "beforeMCPExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterShellExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterMCPExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterFileEdit": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeSubmitPrompt": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "preCompact": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "stop": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeTabFileRead": [
      {
        "command": "./hooks/redact-secrets-tab.sh"
      }
    ],
    "afterTabFileEdit": [
      {
        "command": "./hooks/format-tab.sh"
      }
    ]
  }
}
```

```sh title="audit.sh"
#!/bin/bash

# audit.sh - Hook script that writes all JSON input to /tmp/agent-audit.log
# This script is designed to be called by Cursor's hooks system for auditing purposes

# Read JSON input from stdin
json_input=$(cat)

# Create timestamp for the log entry
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Create the log directory if it doesn't exist
mkdir -p "$(dirname /tmp/agent-audit.log)"

# Write the timestamped JSON entry to the audit log
echo "[$timestamp] $json_input" >> /tmp/agent-audit.log

# Exit successfully
exit 0
```

```sh title="block-git.sh"
#!/bin/bash

# Hook to block git commands and redirect to gh tool usage
# This hook implements the beforeShellExecution hook from the Cursor Hooks Spec

# Initialize debug logging
echo "Hook execution started" >> /tmp/hooks.log

# Read JSON input from stdin
input=$(cat)
echo "Received input: $input" >> /tmp/hooks.log

# Parse the command from the JSON input
command=$(echo "$input" | jq -r '.command // empty')
echo "Parsed command: '$command'" >> /tmp/hooks.log

# Check if the command contains 'git' or 'gh'
if [[ "$command" =~ git[[:space:]] ]] || [[ "$command" == "git" ]]; then
    echo "Git command detected - blocking: '$command'" >> /tmp/hooks.log
    # Block the git command and provide guidance to use gh tool instead
    cat << EOF
{
  "continue": true,
  "permission": "deny",
  "user_message": "Git command blocked. Please use the GitHub CLI (gh) tool instead.",
  "agent_message": "The git command '$command' has been blocked by a hook. Instead of using raw git commands, please use the 'gh' tool which provides better integration with GitHub and follows best practices. For example:\n- Instead of 'git clone', use 'gh repo clone'\n- Instead of 'git push', use 'gh repo sync' or the appropriate gh command\n- For other git operations, check if there's an equivalent gh command or use the GitHub web interface\n\nThis helps maintain consistency and leverages GitHub's enhanced tooling."
}
EOF
elif [[ "$command" =~ gh[[:space:]] ]] || [[ "$command" == "gh" ]]; then
    echo "GitHub CLI command detected - asking for permission: '$command'" >> /tmp/hooks.log
    # Ask for permission for gh commands
    cat << EOF
{
  "continue": true,
  "permission": "ask",
  "user_message": "GitHub CLI command requires permission: $command",
  "agent_message": "The command '$command' uses the GitHub CLI (gh) which can interact with your GitHub repositories and account. Please review and approve this command if you want to proceed."
}
EOF
else
    echo "Non-git/non-gh command detected - allowing: '$command'" >> /tmp/hooks.log
    # Allow non-git/non-gh commands
    cat << EOF
{
  "continue": true,
  "permission": "allow"
}
EOF
fi
```

### TypeScript stop automation hook

Choose TypeScript when you need typed JSON, durable file I/O, and HTTP calls in the same hook. This Bun-powered `stop` hook tracks per-conversation failure counts on disk, forwards structured telemetry to an internal API, and can automatically schedule a retry when the agent fails twice in a row.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "stop": [
      {
        "command": "bun run .cursor/hooks/track-stop.ts --stop"
      }
    ]
  }
}
```

```ts title=".cursor/hooks/track-stop.ts"
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { stdin } from 'bun';

type StopHookInput = {
  conversation_id: string;
  generation_id: string;
  model: string;
  status: 'completed' | 'aborted' | 'error';
  loop_count: number;
};

type StopHookOutput = {
  followup_message?: string;
};

type MetricsEntry = {
  lastStatus: StopHookInput['status'];
  errorCount: number;
  lastUpdatedIso: string;
};

type MetricsStore = Record<string, MetricsEntry>;

const STATE_DIR = '.cursor/hooks/state';
const METRICS_PATH = `${STATE_DIR}/agent-metrics.json`;
const TELEMETRY_URL = Bun.env.AGENT_TELEMETRY_URL;

async function parseHookInput<T>(): Promise<T> {
  const text = await stdin.text();
  return JSON.parse(text) as T;
}

async function readMetrics(): Promise<MetricsStore> {
  try {
    return JSON.parse(await readFile(METRICS_PATH, 'utf8')) as MetricsStore;
  } catch {
    return {};
  }
}

async function writeMetrics(store: MetricsStore) {
  await mkdir(STATE_DIR, { recursive: true });
  await writeFile(METRICS_PATH, JSON.stringify(store, null, 2), 'utf8');
}

async function sendTelemetry(payload: StopHookInput, entry: MetricsEntry) {
  if (!TELEMETRY_URL) return;
  await fetch(TELEMETRY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversationId: payload.conversation_id,
      generationId: payload.generation_id,
      model: payload.model,
      status: payload.status,
      errorCount: entry.errorCount,
      loopCount: payload.loop_count,
      timestamp: entry.lastUpdatedIso
    })
  });
}

async function main() {
  const payload = await parseHookInput<StopHookInput>();
  const metrics = await readMetrics();
  const entry =
    metrics[payload.conversation_id] ?? {
      lastStatus: payload.status,
      errorCount: 0,
      lastUpdatedIso: ''
    };

  entry.lastStatus = payload.status;
  entry.lastUpdatedIso = new Date().toISOString();
  entry.errorCount = payload.status === 'error' ? entry.errorCount + 1 : 0;

  metrics[payload.conversation_id] = entry;
  await writeMetrics(metrics);
  await sendTelemetry(payload, entry);

  const response: StopHookOutput = {};
  if (entry.errorCount >= 2 && payload.loop_count < 4) {
    response.followup_message =
      'Automated retry triggered after two failures. Double-check credentials before running again.';
  }

  process.stdout.write(JSON.stringify(response) + '\n');
}

main().catch(error => {
  console.error('[stop hook] failed', error);
  process.stdout.write('{}\n');
});
```

Set `AGENT_TELEMETRY_URL` to the internal endpoint that should receive run summaries.

### Python manifest guard hook

Python shines when you need rich parsing libraries. This hook uses `pyyaml` to inspect Kubernetes manifests before `kubectl apply` runs; Bash would struggle to parse multi-document YAML safely.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "python3 .cursor/hooks/kube_guard.py"
      }
    ]
  }
}
```

```python title=".cursor/hooks/kube_guard.py"
#!/usr/bin/env python3
import json
import shlex
import sys
from pathlib import Path

import yaml

SENSITIVE_NAMESPACES = {"prod", "production"}

def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("command", "")
    cwd = Path(payload.get("cwd") or ".")
    response = {"continue": True, "permission": "allow"}

    try:
        args = shlex.split(command)
    except ValueError:
        print(json.dumps(response))
        return

    if len(args) < 2 or args[0] != "kubectl" or args[1] != "apply" or "-f" not in args:
        print(json.dumps(response))
        return

    f_index = args.index("-f")
    if f_index + 1 >= len(args):
        print(json.dumps(response))
        return

    manifest_arg = args[f_index + 1]
    manifest_path = (cwd / manifest_arg).resolve()

    if not manifest_path.exists():
        print(json.dumps(response))
        return

    cli_namespace = None
    for i, arg in enumerate(args):
        if arg in ("-n", "--namespace") and i + 1 < len(args):
            cli_namespace = args[i + 1]
        elif arg.startswith("--namespace="):
            cli_namespace = arg.split("=", 1)[1]
        elif arg.startswith("-n="):
            cli_namespace = arg.split("=", 1)[1]

    try:
        documents = list(yaml.safe_load_all(manifest_path.read_text()))
    except (OSError, yaml.YAMLError) as exc:
        sys.stderr.write(f"Failed to read/parse {manifest_path}: {exc}\n")
        print(json.dumps(response))
        return

    if cli_namespace in SENSITIVE_NAMESPACES or any(
        (doc or {}).get("metadata", {}).get("namespace") in SENSITIVE_NAMESPACES
        for doc in documents
    ):
        response.update(
            {
                "permission": "ask",
                "user_message": "kubectl apply to prod requires manual approval.",
                "agent_message": f"{manifest_path.name} includes protected namespaces; confirm with your team before continuing.",
            }
        )

    print(json.dumps(response))

if __name__ == "__main__":
    main()
```

Install PyYAML (for example, `pip install pyyaml`) wherever your hook scripts run so the parser import succeeds.

## Partner Integrations

We partner with ecosystem vendors who have built hooks support with Cursor. These integrations cover security scanning, governance, secrets management, and more.

### MCP governance and visibility

| Partner                                                                                 | Description                                                                                                                                   |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [MintMCP](https://www.mintmcp.com/blog/mcp-governance-cursor-hooks)                     | Build a complete inventory of MCP servers, monitor tool usage patterns, and scan responses for sensitive data before it reaches the AI model. |
| [Oasis Security](https://www.oasis.security/blog/cursor-oasis-governing-agentic-access) | Enforce least-privilege policies on AI agent actions and maintain full audit trails across enterprise systems.                                |
| [Runlayer](https://www.runlayer.com/blog/cursor-hooks)                                  | Wrap MCP tools and integrate with their MCP broker for centralized control and visibility over agent-to-tool interactions.                    |

### Code security and best practices

| Partner                                                          | Description                                                                                                                             |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Corridor](https://corridor.dev/blog/corridor-cursor-hooks/)     | Get real-time feedback on code implementation and security design decisions as code is being written.                                   |
| [Semgrep](https://semgrep.dev/blog/2025/cursor-hooks-mcp-server) | Automatically scan AI-generated code for vulnerabilities with real-time feedback to regenerate code until security issues are resolved. |

### Dependency security

| Partner                                                                                                             | Description                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| [Endor Labs](https://www.endorlabs.com/learn/bringing-malware-detection-into-ai-coding-workflows-with-cursor-hooks) | Intercept package installations and scan for malicious dependencies, preventing supply chain attacks before they enter your codebase. |

### Agent security and safety

| Partner                                                          | Description                                                                                                                             |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Snyk](https://snyk.io/blog/evo-agent-guard-cursor-integration/) | Review agent actions in real-time with Evo Agent Guard, detecting and preventing issues like prompt injection and dangerous tool calls. |

### Secrets management

| Partner                                                                 | Description                                                                                                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [1Password](https://marketplace.1password.com/integration/cursor-hooks) | Validate that environment files from 1Password Environments are properly mounted before shell commands execute, enabling just-in-time secrets access without writing credentials to disk. |

For more details about our hooks partners, see the [Hooks for security and platform teams](/blog/hooks-partners) blog post.

## Configuration

Define hooks in a `hooks.json` file. Configuration can exist at multiple levels; higher-priority sources override lower ones:

```sh
~/.cursor/
├── hooks.json
└── hooks/
    ├── audit.sh
    └── block-git.sh
```

- **Enterprise** (MDM-managed, system-wide):
  - macOS: `/Library/Application Support/Cursor/hooks.json`
  - Linux/WSL: `/etc/cursor/hooks.json`
  - Windows: `C:\\ProgramData\\Cursor\\hooks.json`
- **Team** (Cloud-distributed, enterprise only):
  - Configured in the [web dashboard](https://cursor.com/dashboard?tab=team-content\&section=hooks) and synced to all team members automatically
- **Project** (Project-specific):
  - `<project-root>/.cursor/hooks.json`
  - Project hooks run in any trusted workspace and are checked into version control with your project
- **User** (User-specific):
  - `~/.cursor/hooks.json`

Priority order (highest to lowest): Enterprise → Team → Project → User

The `hooks` object maps hook names to arrays of hook definitions. Each definition currently supports a `command` property that can be a shell string, an absolute path, or a relative path. The working directory depends on the hook source:

- **Project hooks** (`.cursor/hooks.json` in a repository): Run from the **project root**
- **User hooks** (`~/.cursor/hooks.json`): Run from `~/.cursor/`
- **Enterprise hooks** (system-wide config): Run from the enterprise config directory
- **Team hooks** (cloud-distributed): Run from the managed hooks directory

For project hooks, use paths like `.cursor/hooks/script.sh` (relative to project root), not `./hooks/script.sh` (which would look for `<project>/hooks/script.sh`).

### Configuration file

This example shows a user-level hooks file (`~/.cursor/hooks.json`). For project-level hooks, change paths like `./hooks/script.sh` to `.cursor/hooks/script.sh`:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [{ "command": "./session-init.sh" }],
    "sessionEnd": [{ "command": "./audit.sh" }],
    "preToolUse": [
      {
        "command": "./hooks/validate-tool.sh",
        "matcher": "Shell|Read|Write"
      }
    ],
    "postToolUse": [{ "command": "./hooks/audit-tool.sh" }],
    "subagentStart": [{ "command": "./hooks/validate-subagent.sh" }],
    "subagentStop": [{ "command": "./hooks/audit-subagent.sh" }],
    "beforeShellExecution": [{ "command": "./script.sh" }],
    "afterShellExecution": [{ "command": "./script.sh" }],
    "afterMCPExecution": [{ "command": "./script.sh" }],
    "afterFileEdit": [{ "command": "./format.sh" }],
    "preCompact": [{ "command": "./audit.sh" }],
    "stop": [{ "command": "./audit.sh", "loop_limit": 10 }],
    "beforeTabFileRead": [{ "command": "./redact-secrets-tab.sh" }],
    "afterTabFileEdit": [{ "command": "./format-tab.sh" }]
  }
}
```

The Agent hooks (`sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`) apply to Cmd+K and Agent Chat operations. The Tab hooks (`beforeTabFileRead`, `afterTabFileEdit`) apply specifically to inline Tab completions.

### Global Configuration Options

| Option    | Type   | Default | Description           |
| --------- | ------ | ------- | --------------------- |
| `version` | number | `1`     | Config schema version |

### Per-Script Configuration Options

| Option       | Type                      | Default          | Description                                                                                                                              |
| ------------ | ------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `command`    | string                    | required         | Script path or command                                                                                                                   |
| `type`       | `"command"` \| `"prompt"` | `"command"`      | Hook execution type                                                                                                                      |
| `timeout`    | number                    | platform default | Execution timeout in seconds                                                                                                             |
| `loop_limit` | number \| null            | `5`              | Per-script loop limit for stop/subagentStop hooks. `null` means no limit. Default is `5` for Cursor hooks, `null` for Claude Code hooks. |
| `matcher`    | object                    | -                | Filter criteria for when hook runs                                                                                                       |

### Matcher Configuration

Matchers let you filter when a hook runs. Which field the matcher applies to depends on the hook:

```json
{
  "hooks": {
    "preToolUse": [
      {
        "command": "./validate-shell.sh",
        "matcher": "Shell"
      }
    ],
    "subagentStart": [
      {
        "command": "./validate-explore.sh",
        "matcher": "explore|shell"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./approve-network.sh",
        "matcher": "curl|wget|nc "
      }
    ]
  }
}
```

- **subagentStart**: The matcher runs against the **subagent type** (e.g. `explore`, `shell`, `generalPurpose`). Use it to run hooks only when a specific kind of subagent is started. The example above runs `validate-explore.sh` only for explore or shell subagents.
- **beforeShellExecution**: The matcher runs against the **shell command** string. Use it to run hooks only when the command matches a pattern (e.g. network calls, file deletions). The example above runs `approve-network.sh` only when the command contains `curl`, `wget`, or `nc `.

**Available matchers by hook:**

- **preToolUse** (and other tool hooks): Filter by tool type — `Shell`, `Read`, `Write`, `Grep`, `Delete`, `MCP`, `Task`, etc.
- **subagentStart**: Filter by subagent type — `generalPurpose`, `explore`, `shell`, etc.
- **beforeShellExecution**: Filter by the shell command text; the matcher is matched against the full command string.

## Team Distribution

Hooks can be distributed to team members using project hooks (via version control), MDM tools, or Cursor's cloud distribution system.

### Project Hooks (Version Control)

Project hooks are the simplest way to share hooks with your team. Place a `hooks.json` file at `<project-root>/.cursor/hooks.json` and commit it to your repository. When team members open the project in a trusted workspace, Cursor automatically loads and runs the project hooks.

Project hooks:

- Are stored in version control alongside your code
- Automatically load for all team members in trusted workspaces
- Can be project-specific (e.g., enforce formatting standards for a particular codebase)
- Require the workspace to be trusted to run (for security)

### MDM Distribution

Distribute hooks across your organization using Mobile Device Management (MDM) tools. Place the `hooks.json` file and hook scripts in the target directories on each machine.

**User home directory** (per-user distribution):

- `~/.cursor/hooks.json`
- `~/.cursor/hooks/` (for hook scripts)

**Global directories** (system-wide distribution):

- macOS: `/Library/Application Support/Cursor/hooks.json`
- Linux/WSL: `/etc/cursor/hooks.json`
- Windows: `C:\\ProgramData\\Cursor\\hooks.json`

Note: MDM-based distribution is fully managed by your organization. Cursor does not deploy or manage files through your MDM solution. Ensure your internal IT or security team handles configuration, deployment, and updates in accordance with your organization's policies.

### Cloud Distribution (Enterprise Only)

Enterprise teams can use Cursor's native cloud distribution to automatically sync hooks to all team members. Configure hooks in the [web dashboard](https://cursor.com/dashboard?tab=team-content\&section=hooks). Cursor automatically delivers configured hooks to all client machines when team members log in.

Cloud distribution provides:

- Automatic synchronization to all team members (every thirty minutes)
- Operating system targeting for platform-specific hooks
- Centralized management through the dashboard

Enterprise administrators can create, edit, and manage team hooks from the dashboard without requiring access to individual machines.

## Reference

### Common schema

#### Input (all hooks)

All hooks receive a base set of fields in addition to their hook-specific fields:

```json
{
  "conversation_id": "string",
  "generation_id": "string",
  "model": "string",
  "hook_event_name": "string",
  "cursor_version": "string",
  "workspace_roots": ["<path>"],
  "user_email": "string | null",
  "transcript_path": "string | null"
}
```

| Field             | Type           | Description                                                                                               |
| ----------------- | -------------- | --------------------------------------------------------------------------------------------------------- |
| `conversation_id` | string         | Stable ID of the conversation across many turns                                                           |
| `generation_id`   | string         | The current generation that changes with every user message                                               |
| `model`           | string         | The model configured for the composer that triggered the hook                                             |
| `hook_event_name` | string         | Which hook is being run                                                                                   |
| `cursor_version`  | string         | Cursor application version (e.g. "1.7.2")                                                                 |
| `workspace_roots` | string\[]      | The list of root folders in the workspace (normally just one, but multiroot workspaces can have multiple) |
| `user_email`      | string \| null | Email address of the authenticated user, if available                                                     |
| `transcript_path` | string \| null | Path to the main conversation transcript file (null if transcripts disabled)                              |

### Hook events

#### preToolUse

Called before any tool execution. This is a generic hook that fires for all tool types (Shell, Read, Write, MCP, Task, etc.). Use matchers to filter by specific tools.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm install", "working_directory": "/project" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "model": "claude-sonnet-4-20250514",
  "agent_message": "Installing dependencies..."
}

// Output
{
  "decision": "allow" | "deny",
  "reason": "<reason shown to agent if denied>",
  "updated_input": { "command": "npm ci" }
}
```

| Output Field    | Type              | Description                             |
| --------------- | ----------------- | --------------------------------------- |
| `decision`      | string            | `"allow"` to proceed, `"deny"` to block |
| `reason`        | string (optional) | Explanation shown to agent when denied  |
| `updated_input` | object (optional) | Modified tool input to use instead      |

#### postToolUse

Called after successful tool execution. Useful for auditing and analytics.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm test" },
  "tool_output": "All tests passed",
  "tool_use_id": "abc123",
  "cwd": "/project",
  "duration": 5432,
  "model": "claude-sonnet-4-20250514"
}

// Output
{
  "updated_mcp_tool_output": { "modified": "output" }
}
```

| Input Field   | Type   | Description                    |
| ------------- | ------ | ------------------------------ |
| `duration`    | number | Execution time in milliseconds |
| `tool_output` | string | Full output from the tool      |

| Output Field              | Type              | Description                                                    |
| ------------------------- | ----------------- | -------------------------------------------------------------- |
| `updated_mcp_tool_output` | object (optional) | For MCP tools only: replaces the tool output seen by the model |

#### postToolUseFailure

Called when a tool fails, times out, or is denied. Useful for error tracking and recovery logic.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "error_message": "Command timed out after 30s",
  "failure_type": "timeout" | "error" | "permission_denied",
  "duration": 5000,
  "is_interrupt": false
}

// Output
{
  // No output fields currently supported
}
```

| Input Field     | Type    | Description                                                       |
| --------------- | ------- | ----------------------------------------------------------------- |
| `error_message` | string  | Description of the failure                                        |
| `failure_type`  | string  | Type of failure: `"error"`, `"timeout"`, or `"permission_denied"` |
| `duration`      | number  | Time in milliseconds until the failure occurred                   |
| `is_interrupt`  | boolean | Whether this failure was caused by a user interrupt/cancellation  |

#### subagentStart

Called before spawning a subagent (Task tool). Can allow or deny subagent creation.

```json
// Input
{
  "subagent_type": "generalPurpose",
  "prompt": "Explore the authentication flow",
  "model": "claude-sonnet-4-20250514"
}

// Output
{
  "decision": "allow" | "deny",
  "reason": "<reason if denied>"
}
```

#### subagentStop

Called when a subagent completes or errors. Can trigger follow-up actions.

```json
// Input
{
  "subagent_type": "generalPurpose",
  "status": "completed" | "error",
  "result": "<subagent output>",
  "duration": 45000,
  "agent_transcript_path": "/path/to/subagent/transcript.txt"
}

// Output
{
  "followup_message": "<auto-continue with this message>"
}
```

| Input Field             | Type           | Description                                                                        |
| ----------------------- | -------------- | ---------------------------------------------------------------------------------- |
| `subagent_type`         | string         | Type of subagent: `generalPurpose`, `explore`, `shell`, etc.                       |
| `status`                | string         | `"completed"` or `"error"`                                                         |
| `result`                | string         | Output/result from the subagent                                                    |
| `duration`              | number         | Execution time in milliseconds                                                     |
| `agent_transcript_path` | string \| null | Path to the subagent's own transcript file (separate from the parent conversation) |

The `followup_message` field enables loop-style flows where subagent completion triggers the next iteration.

#### beforeShellExecution / beforeMCPExecution

Called before any shell command or MCP tool is executed. Return a permission decision.

`beforeMCPExecution` uses **fail-closed** behavior. If the hook script fails to execute (crashes, times out, or returns invalid JSON), the MCP tool call will be blocked. This ensures MCP operations cannot bypass configured hooks.

```json
// beforeShellExecution input
{
  "command": "<full terminal command>",
  "cwd": "<current working directory>",
  "timeout": 30
}

// beforeMCPExecution input
{
  "tool_name": "<tool name>",
  "tool_input": "<json params>"
}
// Plus either:
{ "url": "<server url>" }
// Or:
{ "command": "<command string>" }

// Output
{
  "permission": "allow" | "deny" | "ask",
  "user_message": "<message shown in client>",
  "agent_message": "<message sent to agent>"
}
```

#### afterShellExecution

Fires after a shell command executes; useful for auditing or collecting metrics from command output.

```json
// Input
{
  "command": "<full terminal command>",
  "output": "<full terminal output>",
  "duration": 1234
}
```

| Field      | Type   | Description                                                                              |
| ---------- | ------ | ---------------------------------------------------------------------------------------- |
| `command`  | string | The full terminal command that was executed                                              |
| `output`   | string | Full output captured from the terminal                                                   |
| `duration` | number | Duration in milliseconds spent executing the shell command (excludes approval wait time) |

#### afterMCPExecution

Fires after an MCP tool executes; includes the tool's input parameters and full JSON result.

```json
// Input
{
  "tool_name": "<tool name>",
  "tool_input": "<json params>",
  "result_json": "<tool result json>",
  "duration": 1234
}
```

| Field         | Type   | Description                                                                         |
| ------------- | ------ | ----------------------------------------------------------------------------------- |
| `tool_name`   | string | Name of the MCP tool that was executed                                              |
| `tool_input`  | string | JSON params string passed to the tool                                               |
| `result_json` | string | JSON string of the tool response                                                    |
| `duration`    | number | Duration in milliseconds spent executing the MCP tool (excludes approval wait time) |

#### afterFileEdit

Fires after the Agent edits a file; useful for formatters or accounting of agent-written code.

```json
// Input
{
  "file_path": "<absolute path>",
  "edits": [{ "old_string": "<search>", "new_string": "<replace>" }]
}
```

#### beforeReadFile

Called before Agent reads a file. Use for access control to block sensitive files from being sent to the model.

This hook uses **fail-closed** behavior. If the hook script fails to execute (crashes, times out, or returns invalid JSON), the file read will be blocked. This provides security guarantees for sensitive file access.

```json
// Input
{
  "file_path": "<absolute path>",
  "content": "<file contents>",
  "attachments": [
    {
      "type": "file" | "rule",
      "filePath": "<absolute path>"
    }
  ]
}

// Output
{
  "permission": "allow" | "deny",
  "user_message": "<message shown when denied>"
}
```

| Input Field   | Type   | Description                                    |
| ------------- | ------ | ---------------------------------------------- |
| `file_path`   | string | Absolute path to the file being read           |
| `content`     | string | Full contents of the file                      |
| `attachments` | array  | Context attachments associated with the prompt |

| Output Field   | Type              | Description                             |
| -------------- | ----------------- | --------------------------------------- |
| `permission`   | string            | `"allow"` to proceed, `"deny"` to block |
| `user_message` | string (optional) | Message shown to user when denied       |

#### beforeTabFileRead

Called before Tab (inline completions) reads a file. Enable redaction or access control before Tab accesses file contents.

**Key differences from `beforeReadFile`:**

- Only triggered by Tab, not Agent
- Does not include `attachments` field (Tab doesn't use prompt attachments)
- Useful for applying different policies to autonomous Tab operations

```json
// Input
{
  "file_path": "<absolute path>",
  "content": "<file contents>"
}

// Output
{
  "permission": "allow" | "deny"
}
```

#### afterTabFileEdit

Called after Tab (inline completions) edits a file. Useful for formatters or auditing of Tab-written code.

**Key differences from `afterFileEdit`:**

- Only triggered by Tab, not Agent
- Includes detailed edit information: `range`, `old_line`, and `new_line` for precise edit tracking
- Useful for fine-grained formatting or analysis of Tab edits

```json
// Input
{
  "file_path": "<absolute path>",
  "edits": [
    {
      "old_string": "<search>",
      "new_string": "<replace>",
      "range": {
        "start_line_number": 10,
        "start_column": 5,
        "end_line_number": 10,
        "end_column": 20
      },
      "old_line": "<line before edit>",
      "new_line": "<line after edit>"
    }
  ]
}

// Output
{
  // No output fields currently supported
}
```

#### beforeSubmitPrompt

Called right after user hits send but before backend request. Can prevent submission.

```json
// Input
{
  "prompt": "<user prompt text>",
  "attachments": [
    {
      "type": "file" | "rule",
      "filePath": "<absolute path>"
    }
  ]
}

// Output
{
  "continue": true | false,
  "user_message": "<message shown to user when blocked>"
}
```

| Output Field   | Type              | Description                                          |
| -------------- | ----------------- | ---------------------------------------------------- |
| `continue`     | boolean           | Whether to allow the prompt submission to proceed    |
| `user_message` | string (optional) | Message shown to the user when the prompt is blocked |

#### afterAgentResponse

Called after the agent has completed an assistant message.

```json
// Input
{
  "text": "<assistant final text>"
}
```

#### afterAgentThought

Called after the agent completes a thinking block. Useful for observing the agent's reasoning process.

```json
// Input
{
  "text": "<fully aggregated thinking text>",
  "duration_ms": 5000
}

// Output
{
  // No output fields currently supported
}
```

| Field         | Type              | Description                                            |
| ------------- | ----------------- | ------------------------------------------------------ |
| `text`        | string            | Fully aggregated thinking text for the completed block |
| `duration_ms` | number (optional) | Duration in milliseconds for the thinking block        |

#### stop

Called when the agent loop ends. Can optionally auto-submit a follow-up user message to keep iterating.

```json
// Input
{
  "status": "completed" | "aborted" | "error",
  "loop_count": 0
}
```

```json
// Output
{
  "followup_message": "<message text>"
}
```

- The optional `followup_message` is a string. When provided and non-empty, Cursor will automatically submit it as the next user message. This enables loop-style flows (e.g., iterate until a goal is met).
- The `loop_count` field indicates how many times the stop hook has already triggered an automatic follow-up for this conversation (starts at 0). To prevent infinite loops, a maximum of 5 auto follow-ups is enforced.

#### sessionStart

Called when a new composer conversation is created. Use this hook to set up session-specific environment variables, inject additional context, or block session creation based on custom policies.

```json
// Input
{
  "session_id": "<unique session identifier>",
  "is_background_agent": true | false,
  "composer_mode": "agent" | "ask" | "edit"
}
```

```json
// Output
{
  "env": { "<key>": "<value>" },
  "additional_context": "<context to add to conversation>",
  "continue": true | false,
  "user_message": "<message shown if blocked>"
}
```

| Input Field           | Type              | Description                                                         |
| --------------------- | ----------------- | ------------------------------------------------------------------- |
| `session_id`          | string            | Unique identifier for this session (same as `conversation_id`)      |
| `is_background_agent` | boolean           | Whether this is a background agent session vs interactive session   |
| `composer_mode`       | string (optional) | The mode the composer is starting in (e.g., "agent", "ask", "edit") |

| Output Field         | Type               | Description                                                                                         |
| -------------------- | ------------------ | --------------------------------------------------------------------------------------------------- |
| `env`                | object (optional)  | Environment variables to set for this session. Available to all subsequent hook executions          |
| `additional_context` | string (optional)  | Additional context to add to the conversation's initial system context                              |
| `continue`           | boolean (optional) | Whether to continue with session creation. If false, the session will not be created. Default: true |
| `user_message`       | string (optional)  | Message to show to the user if `continue` is false                                                  |

#### sessionEnd

Called when a composer conversation ends. This is a fire-and-forget hook useful for logging, analytics, or cleanup tasks. The response is logged but not used.

```json
// Input
{
  "session_id": "<unique session identifier>",
  "reason": "completed" | "aborted" | "error" | "window_close" | "user_close",
  "duration_ms": 45000,
  "is_background_agent": true | false,
  "final_status": "<status string>",
  "error_message": "<error details if reason is 'error'>"
}
```

```json
// Output
{
  // No output fields - fire and forget
}
```

| Input Field           | Type              | Description                                                                               |
| --------------------- | ----------------- | ----------------------------------------------------------------------------------------- |
| `session_id`          | string            | Unique identifier for the session that is ending                                          |
| `reason`              | string            | How the session ended: "completed", "aborted", "error", "window\_close", or "user\_close" |
| `duration_ms`         | number            | Total duration of the session in milliseconds                                             |
| `is_background_agent` | boolean           | Whether this was a background agent session                                               |
| `final_status`        | string            | Final status of the session                                                               |
| `error_message`       | string (optional) | Error message if reason is "error"                                                        |

#### preCompact

Called before context window compaction/summarization occurs. This is an observational hook that cannot block or modify the compaction behavior. Useful for logging when compaction happens or notifying users.

```json
// Input
{
  "trigger": "auto" | "manual",
  "context_usage_percent": 85,
  "context_tokens": 120000,
  "context_window_size": 128000,
  "message_count": 45,
  "messages_to_compact": 30,
  "is_first_compaction": true | false
}
```

```json
// Output
{
  "user_message": "<message to show when compaction occurs>"
}
```

| Input Field             | Type    | Description                                                |
| ----------------------- | ------- | ---------------------------------------------------------- |
| `trigger`               | string  | What triggered the compaction: "auto" or "manual"          |
| `context_usage_percent` | number  | Current context window usage as a percentage (0-100)       |
| `context_tokens`        | number  | Current context window token count                         |
| `context_window_size`   | number  | Maximum context window size in tokens                      |
| `message_count`         | number  | Number of messages in the conversation                     |
| `messages_to_compact`   | number  | Number of messages that will be summarized                 |
| `is_first_compaction`   | boolean | Whether this is the first compaction for this conversation |

| Output Field   | Type              | Description                                        |
| -------------- | ----------------- | -------------------------------------------------- |
| `user_message` | string (optional) | Message to show to the user when compaction occurs |

## Environment Variables

Hook scripts receive environment variables when executed:

| Variable             | Description                                  | Always Present        |
| -------------------- | -------------------------------------------- | --------------------- |
| `CURSOR_PROJECT_DIR` | Workspace root directory                     | Yes                   |
| `CURSOR_VERSION`     | Cursor version string                        | Yes                   |
| `CURSOR_USER_EMAIL`  | Authenticated user email                     | If logged in          |
| `CURSOR_CODE_REMOTE` | Remote-aware project path                    | For remote workspaces |
| `CLAUDE_PROJECT_DIR` | Alias for project dir (Claude compatibility) | Yes                   |

Session-scoped environment variables from `sessionStart` hooks are passed to all subsequent hook executions within that session.

## Troubleshooting

**How to confirm hooks are active**

There is a Hooks tab in Cursor Settings to debug configured and executed hooks, as well as a Hooks output channel to see errors.

**If hooks are not working**

- Restart Cursor to ensure the hooks service is running.
- Check that relative paths are correct for your hook source:
  - For **project hooks**, paths are relative to the **project root** (e.g., `.cursor/hooks/script.sh`)
  - For **user hooks**, paths are relative to `~/.cursor/` (e.g., `./hooks/script.sh` or `hooks/script.sh`)

**Exit code blocking**

Exit code `2` from command hooks blocks the action (equivalent to returning `decision: "deny"`). This matches Claude Code behavior for compatibility.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
