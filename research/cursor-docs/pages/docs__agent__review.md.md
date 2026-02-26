# Review

When Agent generates code changes, they're presented in a review interface that shows additions and deletions with color-coded lines. This allows you to examine and control which changes are applied to your codebase.

The review interface displays code changes in a familiar diff format:

## Diffs

| Type              | Meaning                    | Example                          |
| :---------------- | :------------------------- | :------------------------------- |
| **Added lines**   | New code additions         | + const newVariable = 'hello';   |
| **Deleted lines** | Code removals              | - const oldVariable = 'goodbye'; |
| **Context lines** | Unchanged surrounding code |  function example()              |

## Agent Review

Agent Review runs Cursor Agent in a specialized mode focused on catching bugs in your diffs. This tool analyzes proposed changes line-by-line and flags issues before you merge.

> **Want automatic reviews on your PRs?**\
> Check out [Bugbot](https://cursor.com/docs/bugbot.md), which applies advanced analysis to catch issues early and suggest improvements automatically on every pull request.

There are two ways to use Agent Review: in the agent diff and in the source control tab.

### Agent diff

Review the output of an agent diff: after a response, click **Review**, then click **Find Issues** to analyze the proposed edits and suggest follow-ups.

![Review input interface](/docs-static/images/agent/review/diff-review.png)

### Source control

Review all changes against your main branch: open the Source Control tab and run Agent Review to review all local changes compared to your main branch.

### Billing

Running Agent Review triggers an agent run and is billed as a usage-based request.

### Settings

You can configure Agent Review in the Cursor settings.

| Setting                     | Description                                                  |
| --------------------------- | ------------------------------------------------------------ |
| **Auto-run on commit**      | Scan your code for bugs automatically after each commit      |
| **Include submodules**      | Include changes from Git submodules in the review            |
| **Include untracked files** | Include untracked files (not yet added to Git) in the review |

## Review UI

After generation completes, you'll see a prompt to review all changes before proceeding. This gives you an overview of what will be modified.

![Review input interface](/docs-static/images/chat/review/input-review.png)

### File-by-file

A floating review bar appears at the bottom of your screen, allowing you to:

- **Accept** or **reject** changes for the current file
- Navigate to the **next file** with pending changes

  [Media](/docs-static/images/chat/review/review-bar.mp4)

  Your browser does not support the video tag.

### Selective acceptance

For fine-grained control:

- To accept most changes: reject unwanted lines, then click **Accept all**
- To reject most changes: accept wanted lines, then click **Reject all**


---

## Sitemap

[Overview of all docs pages](/llms.txt)
