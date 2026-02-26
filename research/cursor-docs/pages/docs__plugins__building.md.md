# Building plugins

Cursor plugins let you package and distribute rules, skills, agents, commands, MCP servers, and hooks. Once installed, plugins work across all Cursor surfaces: the IDE, CLI, and Cloud.

If you're starting from scratch, use the [plugin template repository](https://github.com/cursor/plugin-template). It includes the required layout and starter files.

## Plugin structure

A plugin is a directory with a manifest file and your plugin assets:

```text
my-plugin/
├── .cursor-plugin/
│   └── plugin.json        # Required: plugin manifest
├── rules/                 # Cursor rules (.mdc files)
│   ├── coding-standards.mdc
│   └── review-checklist.mdc
├── skills/                # Agent skills
│   └── code-reviewer/
│       └── SKILL.md
├── agents/                # Custom agent configurations
│   └── security-reviewer.md
├── commands/              # Agent-executable commands
│   └── deploy.md
├── hooks/                 # Hook definitions
│   └── hooks.json
├── .mcp.json              # MCP server definitions
├── assets/                # Logos and static assets
│   └── logo.svg
├── scripts/               # Hook and utility scripts
│   └── format-code.py
└── README.md
```

## Plugin manifest

Every plugin requires a `.cursor-plugin/plugin.json` manifest file.

### Required fields

| Field  | Type   | Description                                                                                                                                                              |
| :----- | :----- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name` | string | Plugin identifier. Lowercase, kebab-case (alphanumerics, hyphens, and periods). Must start and end with an alphanumeric character. Examples: `my-plugin`, `prompts.chat` |

### Optional fields

| Field         | Type                     | Description                                                                                                                                                                                                          |
| :------------ | :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `description` | string                   | Brief plugin description                                                                                                                                                                                             |
| `version`     | string                   | Semantic version (e.g., `1.0.0`)                                                                                                                                                                                     |
| `author`      | object                   | Author info: `name` (required), `email` (optional)                                                                                                                                                                   |
| `homepage`    | string                   | URL to plugin homepage                                                                                                                                                                                               |
| `repository`  | string                   | URL to plugin repository                                                                                                                                                                                             |
| `license`     | string                   | License identifier (e.g., `MIT`)                                                                                                                                                                                     |
| `keywords`    | array                    | Tags for discovery and categorization                                                                                                                                                                                |
| `logo`        | string                   | Relative path to a logo file in the repo (e.g., `assets/logo.svg`), or an absolute URL. Relative paths resolve to `raw.githubusercontent.com` URLs. Preferred: commit the logo to your repo and use a relative path. |
| `rules`       | string or array          | Path(s) to rule files or directories                                                                                                                                                                                 |
| `agents`      | string or array          | Path(s) to agent files or directories                                                                                                                                                                                |
| `skills`      | string or array          | Path(s) to skill directories                                                                                                                                                                                         |
| `commands`    | string or array          | Path(s) to command files or directories                                                                                                                                                                              |
| `hooks`       | string or object         | Path to hooks config file, or inline hook config                                                                                                                                                                     |
| `mcpServers`  | string, object, or array | Path to MCP config file, inline MCP server config, or an array of either. Overrides default `.mcp.json` discovery.                                                                                                   |

### Example manifest

```json
{
  "name": "enterprise-plugin",
  "version": "1.2.0",
  "description": "Enterprise development tools with security scanning and compliance checks",
  "author": {
    "name": "ACME DevTools",
    "email": "devtools@acme.com"
  },
  "keywords": ["enterprise", "security", "compliance"],
  "logo": "assets/logo.svg"
}
```

## Component discovery

When the manifest does not specify explicit paths for a component type, the parser uses **automatic folder-based discovery**:

| Component   | Default location          | How it's discovered                                                                        |
| :---------- | :------------------------ | :----------------------------------------------------------------------------------------- |
| Skills      | `skills/`                 | Each subdirectory containing a `SKILL.md` file                                             |
| Rules       | `rules/`                  | All `.md`, `.mdc`, or `.markdown` files                                                    |
| Agents      | `agents/`                 | All `.md`, `.mdc`, or `.markdown` files                                                    |
| Commands    | `commands/`               | All `.md`, `.mdc`, `.markdown`, or `.txt` files                                            |
| Hooks       | `hooks/hooks.json`        | Parsed for hook event names                                                                |
| MCP Servers | `.mcp.json`               | Parsed for server entries                                                                  |
| Root Skill  | `SKILL.md` at plugin root | Treated as a single-skill plugin (only if no `skills/` dir and no manifest `skills` field) |

If a manifest field **is** specified (e.g., `"skills": "./my-skills/"`), it **replaces** folder discovery for that component. The default folder is not also scanned.

## Writing rules

Rules are `.mdc` files providing persistent guidance to the AI. Place them in the `rules/` directory.

Rules require YAML frontmatter with metadata:

```markdown title="rules/prefer-const.mdc"
---
description: Prefer const over let for variables that are never reassigned
alwaysApply: true
---

prefer-const: Always use `const` for variables that are never reassigned.
Only use `let` when the variable needs to be reassigned. Never use `var`.
```

### Rule frontmatter fields

| Field         | Type            | Description                                                                     |
| :------------ | :-------------- | :------------------------------------------------------------------------------ |
| `description` | string          | Brief description of what the rule does                                         |
| `alwaysApply` | boolean         | If `true`, rule applies to all files. If `false`, rule is available on request. |
| `globs`       | string or array | File patterns the rule applies to (e.g., `"**/*.ts"`)                           |

Use `/create-rule` in the Cursor agent to generate rules with proper frontmatter.

For full documentation, see [Rules](https://cursor.com/docs/context/rules.md).

## Writing skills

Skills are specialized capabilities defined in `SKILL.md` files. Each skill lives in its own directory under `skills/`.

Skills require YAML frontmatter with metadata:

```markdown title="skills/api-designer/SKILL.md"
---
name: api-designer
description: Design RESTful APIs following OpenAPI 3.0 specification.
  Use when designing new API endpoints, reviewing API contracts,
  or generating API documentation.
---

# API Designer Skill

## When to use

- Designing new API endpoints
- Reviewing API contracts
- Generating API documentation

## Instructions

1. Follow REST conventions for resource naming
2. Use appropriate HTTP methods (GET, POST, PUT, DELETE, PATCH)
3. Include proper error responses with standard HTTP status codes
4. Document all endpoints with OpenAPI 3.0 specification
5. Use consistent naming conventions (kebab-case for URLs, camelCase for JSON)
```

### Skill frontmatter fields

| Field         | Type   | Description                                           |
| :------------ | :----- | :---------------------------------------------------- |
| `name`        | string | Skill identifier (lowercase, kebab-case)              |
| `description` | string | Description of what the skill does and when to use it |

Use `/create-skill` in the Cursor agent to generate skills with proper frontmatter.

For full documentation, see [Agent Skills](https://cursor.com/docs/context/skills.md).

## Writing agents

Agents are markdown files defining custom agent behaviors and prompts. Place them in the `agents/` directory.

Agents require YAML frontmatter with metadata:

```markdown title="agents/security-reviewer.md"
---
name: security-reviewer
description: Security-focused code reviewer that checks for
  vulnerabilities and proven approaches
---

# Security Reviewer

You are a security-focused code reviewer. When reviewing code:

1. Check for injection vulnerabilities (SQL, XSS, command injection)
2. Verify proper authentication and authorization
3. Look for sensitive data exposure (API keys, passwords, PII)
4. Ensure secure cryptographic practices
5. Review dependency security and known vulnerabilities
6. Check for proper input validation and sanitization
```

### Agent frontmatter fields

| Field         | Type   | Description                              |
| :------------ | :----- | :--------------------------------------- |
| `name`        | string | Agent identifier (lowercase, kebab-case) |
| `description` | string | Brief description of the agent's purpose |

Use `/create-agent` in the Cursor agent to generate agents with proper frontmatter.

## Writing commands

Commands are markdown or text files defining agent-executable actions. Place them in the `commands/` directory.

Commands support `.md`, `.mdc`, `.markdown`, and `.txt` extensions. They can include YAML frontmatter:

```markdown title="commands/deploy-staging.md"
---
name: deploy-staging
description: Deploy the current branch to the staging environment
---

# Deploy to staging

Steps to deploy to staging:
1. Run tests
2. Build the project
3. Push to staging branch
```

### Command frontmatter fields

| Field         | Type   | Description                                |
| :------------ | :----- | :----------------------------------------- |
| `name`        | string | Command identifier (lowercase, kebab-case) |
| `description` | string | Brief description of what the command does |

## Writing hooks

Hooks are automation scripts triggered by agent events. Define them in `hooks/hooks.json`:

```json title="hooks/hooks.json"
{
  "hooks": {
    "afterFileEdit": [
      {
        "command": "./scripts/format-code.sh"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./scripts/validate-shell.sh",
        "matcher": "rm|curl|wget"
      }
    ],
    "sessionEnd": [
      {
        "command": "./scripts/audit.sh"
      }
    ]
  }
}
```

**Available hook events:**

- **Agent hooks**: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`
- **Tab hooks**: `beforeTabFileRead`, `afterTabFileEdit`

For full documentation, see [Hooks](https://cursor.com/docs/agent/hooks.md).

## MCP servers

The `.mcp.json` file at the plugin root is detected automatically. You only need to specify the `mcpServers` field in `plugin.json` if using a custom path or inline config.

The MCP config file should contain server entries under a `mcpServers` key:

```json title=".mcp.json"
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "${POSTGRES_URL}"
      }
    }
  }
}
```

For full documentation, see [Model Context Protocol (MCP)](https://cursor.com/docs/context/mcp.md).

## Logos

Commit logos to your repository and reference them using a relative path:

```json
{
  "name": "my-plugin",
  "logo": "assets/logo.svg"
}
```

Relative paths resolve to `raw.githubusercontent.com` URLs based on the repository and commit SHA. For example, `assets/logo.svg` in the `acme/plugins` repo at commit `abc123` resolves to:

```text
https://raw.githubusercontent.com/acme/plugins/abc123/my-plugin/assets/logo.svg
```

Absolute GitHub user content URLs (starting with `http://` or `https://`) are also accepted.

## Multi-plugin repositories

A single Git repository can contain multiple plugins using a **marketplace manifest**. Place it at `.cursor-plugin/marketplace.json` in the repository root.

### Marketplace manifest format

```json
{
  "name": "my-marketplace",
  "owner": {
    "name": "Your Org",
    "email": "plugins@yourorg.com"
  },
  "metadata": {
    "description": "A collection of developer tool plugins"
  },
  "plugins": [
    {
      "name": "plugin-one",
      "source": "plugin-one",
      "description": "First plugin"
    },
    {
      "name": "plugin-two",
      "source": "plugin-two",
      "description": "Second plugin"
    }
  ]
}
```

### Marketplace fields

| Field      | Type   | Description                                                                           |
| :--------- | :----- | :------------------------------------------------------------------------------------ |
| `name`     | string | **(required)** Marketplace identifier (kebab-case)                                    |
| `owner`    | object | **(required)** `name` (required), `email` (optional)                                  |
| `plugins`  | array  | **(required)** Array of plugin entries (max 500)                                      |
| `metadata` | object | Optional. `description`, `version`, `pluginRoot` (prefix path for all plugin sources) |

### Plugin entry fields

Each entry in the `plugins` array supports:

| Field                                   | Type             | Description                                                 |
| :-------------------------------------- | :--------------- | :---------------------------------------------------------- |
| `name`                                  | string           | **(required)** Plugin identifier (kebab-case)               |
| `source`                                | string or object | Path to plugin directory, or object with `path` and options |
| `description`                           | string           | Plugin description                                          |
| `version`                               | string           | Semantic version                                            |
| `author`                                | object           | Author info                                                 |
| `homepage`                              | string           | URL                                                         |
| `repository`                            | string           | URL                                                         |
| `license`                               | string           | License identifier                                          |
| `keywords`                              | array            | Search tags                                                 |
| `logo`                                  | string           | Relative path or URL to logo                                |
| `category`                              | string           | Plugin category                                             |
| `tags`                                  | array            | Additional tags                                             |
| `skills`, `rules`, `agents`, `commands` | string or array  | Path(s) to component files                                  |
| `hooks`                                 | string or object | Path to hooks config or inline config                       |
| `mcpServers`                            | string or object | Path to MCP config or inline config                         |

### How resolution works

For a marketplace entry with `"source": "my-plugin"`:

1. The parser looks for `my-plugin/.cursor-plugin/plugin.json`
2. If found, the per-plugin manifest is merged with the marketplace entry (manifest values take precedence)
3. Component discovery runs within the `my-plugin/` directory, using manifest paths if specified or folder-based discovery as fallback

### Example multi-plugin repo

```text
my-plugins/
├── .cursor-plugin/
│   └── marketplace.json       # Lists all plugins
├── eslint-rules/
│   ├── .cursor-plugin/
│   │   └── plugin.json        # Per-plugin manifest
│   └── rules/
│       ├── prefer-const.mdc
│       └── no-any.mdc
├── docker/
│   ├── .cursor-plugin/
│   │   └── plugin.json
│   ├── skills/
│   │   ├── containerize-app/
│   │   │   └── SKILL.md
│   │   └── setup-docker-compose/
│   │       └── SKILL.md
│   └── .mcp.json
└── README.md
```

## Plugin examples

### Rules-only plugin

```text
eslint-rules/
├── .cursor-plugin/
│   └── plugin.json
└── rules/
    ├── prefer-const.mdc
    ├── no-any.mdc
    └── error-handling.mdc
```

```json title="plugin.json"
{
  "name": "eslint-rules",
  "description": "ESLint-inspired coding rules for TypeScript",
  "author": { "name": "Your Name" },
  "keywords": ["eslint", "typescript", "linting"]
}
```

### Skills plugin

```text
code-review-skills/
├── .cursor-plugin/
│   └── plugin.json
└── skills/
    ├── security-review/
    │   └── SKILL.md
    └── performance-audit/
        ├── SKILL.md
        └── scripts/
            └── analyze.py
```

```json title="plugin.json"
{
  "name": "code-review-skills",
  "description": "Advanced code review skills for security and performance",
  "author": { "name": "Your Name" },
  "keywords": ["code-review", "security", "performance"]
}
```

### MCP-only plugin

```text
database-mcp/
├── .cursor-plugin/
│   └── plugin.json
└── .mcp.json
```

```json title="plugin.json"
{
  "name": "database-mcp",
  "description": "MCP servers for database interactions",
  "author": { "name": "Your Name" }
}
```

### Full-featured plugin

```text
enterprise-toolkit/
├── .cursor-plugin/
│   └── plugin.json
├── assets/
│   └── logo.svg
├── rules/
│   ├── security-standards.mdc
│   └── code-style.mdc
├── skills/
│   └── compliance-check/
│       └── SKILL.md
├── agents/
│   ├── security-reviewer.md
│   ├── performance-tester.md
│   └── compliance-checker.md
├── commands/
│   └── run-compliance-scan.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── scripts/
│   ├── security-scan.sh
│   └── format-code.py
└── README.md
```

```json title="plugin.json"
{
  "name": "enterprise-toolkit",
  "version": "2.0.0",
  "description": "Complete enterprise development toolkit with security, compliance, and automation",
  "author": {
    "name": "ACME DevTools",
    "email": "devtools@acme.com"
  },
  "keywords": ["enterprise", "security", "compliance"],
  "logo": "assets/logo.svg"
}
```

## Submitting your plugin

Plugins are reviewed by the Cursor team to maintain a high quality bar. To submit a plugin:

### Create your plugin

Follow this guide's structure. Make sure your plugin has a valid `.cursor-plugin/plugin.json` manifest.

### Host in a Git repository

Push your plugin to a public Git repository. Commit your logo to the repo (optional but recommended).

### Submit your plugin

Go to [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) and submit your repository link.

The team will review your submission and publish it to the [marketplace](https://cursor.com/marketplace).

### Submission checklist

- Plugin has a valid `.cursor-plugin/plugin.json` manifest
- `name` is unique, lowercase, kebab-case (e.g., `my-awesome-plugin`)
- `description` clearly explains the plugin's purpose
- All rules, skills, agents, and commands have proper frontmatter metadata
- Logo is committed to the repo and referenced by relative path (if provided)
- `README.md` documents usage and any configuration
- All paths in manifest are relative and valid (no `..`, no absolute paths)
- Plugin has been tested locally
- For multi-plugin repos: `.cursor-plugin/marketplace.json` is at the repo root with unique plugin names

## Guidelines

1. **Keep plugins focused.** Do one thing well rather than bundling unrelated features.
2. **Document thoroughly.** Include a clear README with usage examples.
3. **Use semantic versioning.** Follow semver for version numbers.
4. **Add proper frontmatter.** All rules, skills, agents, and commands need metadata.
5. **Test locally first.** Verify your plugin works before submitting.
6. **Use descriptive keywords.** Help users discover your plugin.
7. **Commit your logo.** Push an SVG to the repo and reference it by path.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
