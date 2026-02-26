# Parallel Agents

This feature allows you to run multiple agents locally in parallel, or run a single prompt across multiple models at once.

Parallel agents run in their own worktree, allowing them to make edits, or build and test code without interfering with each other.

A worktree is a Git feature that lets you use multiple branches of one repository at once.
Each worktree has its own set of files and changes.

Cursor automatically creates and configures worktrees for you, and we currently have a 1:1 mapping of agents to worktrees. You can also add custom instructions to [configure the worktree setup](https://cursor.com/docs/configuration/worktrees.md#initialization-script), like installing dependencies or applying database migrations.

## Basic Worktree usage

The most basic way to use worktrees in Cursor is to run a single agent in a worktree.

![Basic worktree usage](/docs-static/images/worktrees/worktree-dropdown.png)

When the agent run is complete, click the "Apply" button to apply the agent's changes to your local branch. This is different from the "Keep" button in local agents.

If you'd like to see all worktrees in your git repository, you can run the command `git worktree list` in your terminal. The output will look like this:

```
/.../<repo>                                  15ae12e   [main]
/Users/<you>/.cursor/worktrees/<repo>/98Zlw  15ae12e   [feat-1-98Zlw]
/Users/<you>/.cursor/worktrees/<repo>/a4Xiu  15ae12e   [feat-2-a4Xiu]
```

# Best-of-N - Use multiple models at once

A powerful feature of worktrees is the ability to run a single prompt on multiple models at once.

![Basic best-of-N usage](/docs-static/images/worktrees/worktree-bon.png)

Once you submit a prompt, you will see two cards, one for each model. Click across the cards to see the changes made by each Agent.

![Best-of-N cards](/docs-static/images/worktrees/worktree-bon-cards.png)

Then, click the "Apply" button to apply the changes to your checked out branch.

### When to use multiple models

Running the same prompt across multiple models is especially useful for:

- **Hard problems** where different models might take different approaches
- **Comparing code quality** across model families to find the best solution
- **Finding edge cases** one model might miss that another catches
- **Benchmarking** which models work best for your specific codebase

Having multiple models attempt the same problem and picking the best result significantly improves the final output, especially for harder tasks.

Configure notifications and sounds in Cursor settings so you know when parallel agents finish their work.

## "Apply" Functionality

When you run a parallel agent, you will see a "Apply" button. Clicking this button will apply the changes to your checked out branch. The way this process works is the following:

1. When Cursor creates a worktree, all new files and edited files in your primary working tree are brought along to the worktree (the only exception is files that are ignored by Git).
2. The agent will perform its work in isolation inside this worktree, and potentially make edits to files.
3. When you click "Apply", we try to cleanly merge those changes in to your primary working tree.

If you're applying multiple times inside the same Best-of-N run, Cursor will ask you how you'd like to proceed:

- You have the option to "Full Overwrite" (replace the full contents of every file with the changes from the agent in the worktree)
- Try to "merge" between multiple options using the native conflict resolution UI

## Initialization Script

You can customize the worktree setup by editing the `.cursor/worktrees.json` file. Cursor finds this file in the following order:

1. In the worktree path
2. In the root path of your project

### Configuration options

The `worktrees.json` file supports three configuration keys:

- **`setup-worktree-unix`**: Commands or script path for macOS/Linux. Takes precedence over `setup-worktree` on Unix systems.
- **`setup-worktree-windows`**: Commands or script path for Windows. Takes precedence over `setup-worktree` on Windows.
- **`setup-worktree`**: Generic fallback for all operating systems.

Each key accepts either:

- **An array of shell commands** - executed sequentially in the worktree
- **A string filepath** - path to a script file relative to `.cursor/worktrees.json`

## Example setup configurations

### Using command arrays

#### Node.js project

```json
{
  "setup-worktree": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env"
  ]
}
```

We do not recommend symlinking dependencies into the worktree, as this can cause issues in the
main worktree. Instead, we recommend using fast package managers such as `bun`, `pnpm` or `uv`
in the Python ecosystem to install dependencies.

#### Python project with virtual environment

```json
{
  "setup-worktree": [
    "python -m venv venv",
    "source venv/bin/activate && pip install -r requirements.txt",
    "cp $ROOT_WORKTREE_PATH/.env .env"
  ]
}
```

#### Project with database migrations

```json
{
  "setup-worktree": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env",
    "npm run db:migrate"
  ]
}
```

#### Build and link dependencies

```json
{
  "setup-worktree": [
    "pnpm install",
    "pnpm run build",
    "cp $ROOT_WORKTREE_PATH/.env.local .env.local"
  ]
}
```

### Using script files

For complex setups, you can reference script files instead of inline commands:

```json
{
  "setup-worktree-unix": "setup-worktree-unix.sh",
  "setup-worktree-windows": "setup-worktree-windows.ps1",
  "setup-worktree": [
    "echo 'Using generic fallback. For better support, define OS-specific scripts.'"
  ]
}
```

Place your scripts in the `.cursor/` directory alongside `worktrees.json`:

**setup-worktree-unix.sh** (Unix/macOS):

```bash
#!/bin/bash
set -e

# Install dependencies
npm ci

# Copy environment file
cp "$ROOT_WORKTREE_PATH/.env" .env

# Run database migrations
npm run db:migrate

echo "Worktree setup complete!"
```

**setup-worktree-windows.ps1** (Windows):

```powershell
$ErrorActionPreference = 'Stop'

# Install dependencies
npm ci

# Copy environment file
Copy-Item "$env:ROOT_WORKTREE_PATH\.env" .env

# Run database migrations
npm run db:migrate

Write-Host "Worktree setup complete!"
```

### OS-specific configurations

You can provide different setup commands for different operating systems:

```json
{
  "setup-worktree-unix": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env",
    "chmod +x scripts/*.sh"
  ],
  "setup-worktree-windows": [
    "npm ci",
    "copy %ROOT_WORKTREE_PATH%\\.env .env"
  ]
}
```

### Debugging

If you would like to debug the worktree setup script, open the "Output" bottom panel and select "Worktrees Setup" from the dropdown.

## Worktrees Cleanup

Cursor automatically manages worktrees to prevent excessive disk usage:

- **Per-workspace limit**: Each workspace can have up to 20 worktrees
- **Automatic cleanup**: When you create a new worktree and exceed the limit, Cursor automatically removes the oldest worktrees

Worktrees are removed based on last access time, with the oldest worktrees being removed first. Cleanup is applied per-workspace, so worktrees from different repositories don't interfere with each other. This is done on a schedule, which can be configured in the settings:

```json
{
  // 2.1 and above only:
  "cursor.worktreeCleanupIntervalHours": 6,
  "cursor.worktreeMaxCount": 20
}
```

## Worktrees in the SCM Pane

If you would like to visualize Cursor-created worktrees in the SCM Pane, you can enable the `git.showCursorWorktrees` setting (defaults to `false`).

![Worktrees in the SCM Pane](/docs-static/images/worktrees/worktrees-scm.png)

## Language Server Protocol (LSP) Support

For performance reasons, Cursor currently does not support LSP in worktrees. The agent will not be able to lint files. We are working on supporting this functionality.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
