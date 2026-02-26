# Git

Cursor provides AI-powered Git features to streamline your workflow, including automatic commit message generation and intelligent merge conflict resolution.

## AI Commit Message

Cursor generates commit messages from staged changes.

1. Stage files to commit
2. Open the Git tab in the sidebar
3. Click the sparkle (✨) icon next to the commit message input

Generated messages use staged changes and repository git history. If you use conventions like [Conventional Commits](https://www.conventionalcommits.org/), messages follow the same pattern.

### Add shortcut

To bind to a keyboard shortcut:

1. Go to Keyboard Shortcuts (Cmd+R Cmd+S or Cmd+Shift+P and search "Open Keyboard Shortcuts (JSON)")

2. Add this binding for Cmd+M:

   ```json
   {
     "key": "cmd+m",
     "command": "cursor.generateGitCommitMessage"
   }
   ```

3. Save

You cannot customize commit message generation. Cursor adapts to your existing
commit style.

## AI Resolve Conflicts

When merge conflicts occur, Cursor Agent can help resolve them by understanding both sides of the conflict and proposing a resolution.

### How to use

1. When a merge conflict occurs, you'll see the conflict markers in your file
2. Click the **Resolve in Chat** button that appears in the merge conflict UI
3. Agent will analyze both versions and suggest a resolution
4. Review the proposed changes and apply them

## Agent Attribution

Cursor can automatically add attribution to commits and pull requests made by the Agent, making it easy to identify AI-assisted contributions in your git history.

### Settings

Both settings are enabled by default. Configure in **Cursor Settings > Agent > Attribution**.

### Commit Attribution

When enabled, Agent commits include a `Co-authored-by` trailer:

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

This trailer is automatically appended to any git commit command the Agent runs.

### PR Attribution

When enabled, pull requests created by the Agent include a footer:

```
Made with [Cursor](https://cursor.com)
```

This is automatically added to the body of any `gh pr create` command the Agent runs.

Attribution is only added to commits and PRs created by the Agent. The modifications are idempotent: if the attribution already exists, it won't be added again.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
