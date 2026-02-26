# Agent Security

AI can behave unexpectedly due to prompt injection, hallucinations, and other issues. We protect users with guardrails that limit what agents can do. By default, sensitive actions require your manual approval. This document explains our guardrails and what they mean for you.

These controls and behaviors are our defaults. We recommend keeping them enabled.

## First-party tool calls

Cursor includes tools that help agents write code: reading files, editing files, running terminal commands, searching the web, and more.

Reading files and searching code don't require approval. Use [.cursorignore](https://cursor.com/docs/context/ignore-files.md) to block agent access to specific files. Actions that could expose sensitive data require your explicit approval.

Agents can modify workspace files without approval, except for configuration files. Changes save immediately to disk. Always use version control so you can revert changes. Configuration files (like workspace settings) need your approval first.

**Warning:** If you have auto-reload enabled, agent changes might execute before you can review them.

Terminal commands need your approval by default. Review every command before letting the agent run it.

You can enable auto-approval if you accept the risk. We have an [allowlist](https://cursor.com/docs/agent/tools.md) feature, but it's not a security guarantee. The allowlist is best-effort—bypasses are possible. Never use "Run Everything" mode, which skips all safety checks.

## Third-party tool calls

You can connect external tools using [MCP](https://cursor.com/docs/context/mcp.md). All MCP connections need your approval. After you approve an MCP connection, each tool call still needs individual approval before running.

## Network requests

Attackers could use network requests to steal data. Our tools only make network requests to:

- GitHub
- Direct link retrieval
- Web search providers

Agents cannot make arbitrary network requests with default settings.

## Workspace trust

Cursor supports [workspace trust](https://code.visualstudio.com/docs/editing/workspaces/workspace-trust), but it's disabled by default. When enabled, it prompts you to choose between normal or restricted mode for new workspaces. Restricted mode breaks AI features. For untrusted repos, use a basic text editor instead.

To enable workspace trust:

1. Open your user settings.json file
2. Add the following configuration:

   ```json
   "security.workspace.trust.enabled": true
   ```

Organizations can enforce this setting through MDM solutions.

## Responsible disclosure

Found a vulnerability? Email [security-reports@cursor.com](mailto:security-reports@cursor.com) with details and steps to reproduce.

We acknowledge vulnerability reports within 5 business days. For critical incidents, we notify all users via email.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
