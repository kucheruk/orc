# Third Party Hooks

Cursor supports loading hooks from third-party tools, enabling compatibility with existing hook configurations from other AI coding assistants.

## Claude Code Hooks

Cursor can load and execute hooks configured for Claude Code, allowing you to use the same hook scripts across both tools.

### Requirements

To enable Claude Code hooks compatibility:

1. **Enable Third-party skills** in Cursor Settings → Features → Third-party skills
2. The feature must be enabled for your account

### Configuration Locations

Claude Code hooks are loaded from these locations (in priority order):

| Location          | Path                          | Description                            |
| ----------------- | ----------------------------- | -------------------------------------- |
| **Project local** | `.claude/settings.local.json` | Project-specific, gitignored overrides |
| **Project**       | `.claude/settings.json`       | Project-level hooks, checked into repo |
| **User**          | `~/.claude/settings.json`     | User-level hooks, apply globally       |

### Priority Order

When hooks are configured in multiple locations, they are merged in this priority order (highest to lowest):

1. Enterprise hooks (managed deployment)
2. Team hooks (dashboard-configured)
3. Project hooks (`.cursor/hooks.json`)
4. User hooks (`~/.cursor/hooks.json`)
5. Claude project local (`.claude/settings.local.json`)
6. Claude project (`.claude/settings.json`)
7. Claude user (`~/.claude/settings.json`)

Higher-priority hooks run first, and any hook can block execution for lower-priority hooks.

### Claude Code Hook Format

Claude Code hooks use a similar but slightly different format. Cursor automatically maps Claude hook names to their Cursor equivalents.

**Example Claude Code settings.json:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Shell",
        "hooks": [
          {
            "type": "command",
            "command": "./hooks/validate-shell.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "./hooks/audit.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Step Mapping

Claude Code hook names are automatically mapped to Cursor hook names:

| Claude Code Hook   | Cursor Hook          |
| ------------------ | -------------------- |
| `PreToolUse`       | `preToolUse`         |
| `PostToolUse`      | `postToolUse`        |
| `UserPromptSubmit` | `beforeSubmitPrompt` |
| `Stop`             | `stop`               |
| `SubagentStop`     | `subagentStop`       |
| `SessionStart`     | `sessionStart`       |
| `SessionEnd`       | `sessionEnd`         |
| `PreCompact`       | `preCompact`         |

### Exit Code Behavior

Both Cursor and Claude Code hooks support exit code `2` to block an action. This provides consistent behavior when sharing hooks between tools:

```bash
#!/bin/bash
# Block dangerous commands
if [[ "$COMMAND" == *"rm -rf"* ]]; then
  echo '{"decision": "deny", "reason": "Destructive command blocked"}'
  exit 2
fi
echo '{"decision": "allow"}'
exit 0
```

- **Exit code 0**: Hook succeeded, use the JSON output
- **Exit code 2**: Block the action (equivalent to `decision: "deny"`)
- **Other exit codes**: Hook failed, action proceeds (fail-open)

### Migration from Claude Code

If you have existing Claude Code hooks, you can:

1. **Keep using Claude Code config files**: Enable third-party skills and your existing `.claude/settings.json` hooks will work automatically
2. **Migrate to Cursor format**: Copy your hooks to `.cursor/hooks.json` using the Cursor format for full feature support

**Cursor format equivalent:**

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "command": "./hooks/validate-shell.sh",
        "matcher": "Shell"
      }
    ],
    "postToolUse": [
      {
        "command": "./hooks/audit.sh"
      }
    ]
  }
}
```

## Supported Features

When using Claude Code hooks in Cursor, the following features are supported:

| Claude Code Event   | Cursor Mapping       | Supported |
| ------------------- | -------------------- | --------- |
| `PreToolUse`        | `preToolUse`         | Yes       |
| `PostToolUse`       | `postToolUse`        | Yes       |
| `Stop`              | `stop`               | Yes       |
| `SubagentStop`      | `subagentStop`       | Yes       |
| `SessionStart`      | `sessionStart`       | Yes       |
| `SessionEnd`        | `sessionEnd`         | Yes       |
| `PreCompact`        | `preCompact`         | Yes       |
| `UserPromptSubmit`  | `beforeSubmitPrompt` | Yes       |
| `Notification`      | -                    | No        |
| `PermissionRequest` | -                    | No        |

**Additional supported features:**

| Feature                                 | Supported |
| --------------------------------------- | --------- |
| Command-based hooks (`type: "command"`) | Yes       |
| Prompt-based hooks (`type: "prompt"`)   | Yes       |
| Exit code 2 blocking                    | Yes       |
| Tool matchers (regex patterns)          | Yes       |
| Timeout configuration                   | Yes       |

### Tool Name Mapping

Claude Code tool names are mapped to Cursor tool names:

| Claude Code Tool | Cursor Tool | Supported |
| ---------------- | ----------- | --------- |
| `Bash`           | `Shell`     | Yes       |
| `Read`           | `Read`      | Yes       |
| `Write`          | `Write`     | Yes       |
| `Edit`           | `Write`     | Yes       |
| `Grep`           | `Grep`      | Yes       |
| `Task`           | `Task`      | Yes       |
| `Glob`           | -           | No        |
| `WebFetch`       | -           | No        |
| `WebSearch`      | -           | No        |

### Limitations

Some features are only available when using the native Cursor format:

- `subagentStart` hook (Claude Code only has `SubagentStop`)
- Loop limit configuration (`loop_limit`)
- Team/Enterprise hook distribution via dashboard

## Troubleshooting

**Claude Code hooks not loading**

1. Verify "Third-party skills" is enabled in Cursor Settings
2. Check that your `.claude/settings.json` file is valid JSON
3. Restart Cursor after enabling the setting

**Hooks running but not blocking**

1. Ensure your hook script exits with code `2` to block actions
2. Check the JSON output format matches the expected schema
3. View the Hooks output channel in Cursor for error details

**Different behavior between Cursor and Claude Code**

Some behavior differences may exist due to different execution environments. Test your hooks in both tools to ensure compatibility.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
