# Shell Commands

Cursor provides command-line tools to open files and folders from your terminal. Install both the `cursor` and `code` commands to integrate Cursor with your development workflow.

## Installing CLI commands

Install the CLI commands through the Command Palette:

1. Open the Command Palette (Cmd/Ctrl + P)
2. Type "Install" to filter installation commands
3. Select and run `Install 'cursor' to shell`
4. Repeat and select `Install 'code' to shell`

## Using the CLI commands

After installation, use either command to open files or folders in Cursor:

```bash
# Using the cursor command
cursor path/to/file.js
cursor path/to/folder/

# Using the code command (VS Code compatible)
code path/to/file.js
code path/to/folder/
```

## Command options

Both commands support these options:

- Open a file: `cursor file.js`
- Open a folder: `cursor ./my-project`
- Open multiple items: `cursor file1.js file2.js folder1/`
- Open in a new window: `cursor -n` or `cursor --new-window`
- Wait for the window to close: `cursor -w` or `cursor --wait`

## FAQ

### What's the difference between cursor and code commands?

The `code` command is provided for VS Code compatibility. The `cursor` command also providers access to the [Cursor CLI](https://cursor.com/docs/cli/overview.md).

### Do I need to install both commands?

No, install either or both based on preference.

### Where are the commands installed?

Commands are installed in your system's default shell configuration file (e.g., `.bashrc`, `.zshrc`, or `.config/fish/config.fish`).


---

## Sitemap

[Overview of all docs pages](/llms.txt)
