# Code Review with Cursor CLI

This tutorial shows you how to set up code review using Cursor CLI in GitHub Actions. The workflow will analyze pull requests, identify issues, and post feedback as comments.

For most users, we recommend using [Bugbot](https://cursor.com/docs/bugbot.md) instead. Bugbot
provides managed automated code review with no setup required. This CLI
approach is useful to explore capabilities and for advanced customization.

### Example: Full workflow file

**Example: `.github/workflows/cursor-code-review.yml`**

```yaml
name: Code Review

on:
pull_request:
types: [opened, synchronize, reopened, ready_for_review]

permissions:
pull-requests: write
contents: read
issues: write

jobs:
code-review:
runs-on: ubuntu-latest # Skip automated code review for draft PRs
if: github.event.pull_request.draft == false
steps: - name: Checkout repository
uses: actions/checkout@v4
with:
fetch-depth: 0
ref: ${{ github.event.pull_request.head.sha }}

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git identity
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Perform automated code review
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          MODEL: gpt-5.2
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BLOCKING_REVIEW: ${{ vars.BLOCKING_REVIEW || 'false' }}
        run: |
          agent --force --model "$MODEL" --output-format=text --print 'You are operating in a GitHub Actions runner performing automated code review. The gh CLI is available and authenticated via GH_TOKEN. You may comment on pull requests.

          Context:
          - Repo: ${{ github.repository }}
          - PR Number: ${{ github.event.pull_request.number }}
          - PR Head SHA: ${{ github.event.pull_request.head.sha }}
          - PR Base SHA: ${{ github.event.pull_request.base.sha }}
          - Blocking Review: ${{ env.BLOCKING_REVIEW }}

          Objectives:
          1) Re-check existing review comments and reply resolved when addressed.
          2) Review the current PR diff and flag only clear, high-severity issues.
          3) Leave very short inline comments (1-2 sentences) on changed lines only and a brief summary at the end.

          Procedure:
          - Get existing comments: gh pr view --json comments
          - Get diff: gh pr diff
          - Get changed files with patches to compute inline positions: gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/files --paginate --jq '.[] | {filename,patch}'
          - Compute exact inline anchors for each issue (file path + diff position). Comments MUST be placed inline on the changed line in the diff, not as top-level comments.
          - Detect prior top-level "no issues" style comments authored by this bot (match bodies like: "✅ no issues", "No issues found", "LGTM").
          - If CURRENT run finds issues and any prior "no issues" comments exist:
            - Prefer to remove them to avoid confusion:
              - Try deleting top-level issue comments via: gh api -X DELETE repos/${{ github.repository }}/issues/comments/<comment_id>
              - If deletion isn't possible, minimize them via GraphQL (minimizeComment) or edit to prefix "[Superseded by new findings]".
            - If neither delete nor minimize is possible, reply to that comment: "⚠️ Superseded: issues were found in newer commits".
          - If a previously reported issue appears fixed by nearby changes, reply: ✅ This issue appears to be resolved by the recent changes
          - Analyze ONLY for:
            - Null/undefined dereferences
            - Resource leaks (unclosed files or connections)
            - Injection (SQL/XSS)
            - Concurrency/race conditions
            - Missing error handling for critical operations
            - Obvious logic errors with incorrect behavior
            - Clear performance anti-patterns with measurable impact
            - Definitive security vulnerabilities
          - Avoid duplicates: skip if similar feedback already exists on or near the same lines.

          Commenting rules:
          - Max 10 inline comments total; prioritize the most critical issues
          - One issue per comment; place on the exact changed line
          - All issue comments MUST be inline (anchored to a file and line/position in the PR diff)
          - Natural tone, specific and actionable; do not mention automated or high-confidence
          - Use emojis: 🚨 Critical 🔒 Security ⚡ Performance ⚠️ Logic ✅ Resolved ✨ Improvement

          Submission:
          - If there are NO issues to report and an existing top-level comment indicating "no issues" already exists (e.g., "✅ no issues", "No issues found", "LGTM"), do NOT submit another comment. Skip submission to avoid redundancy.
          - If there are NO issues to report and NO prior "no issues" comment exists, submit one brief summary comment noting no issues.
          - If there ARE issues to report and a prior "no issues" comment exists, ensure that prior comment is deleted/minimized/marked as superseded before submitting the new review.
          - If there ARE issues to report, submit ONE review containing ONLY inline comments plus an optional concise summary body. Use the GitHub Reviews API to ensure comments are inline:
            - Build a JSON array of comments like: [{ "path": "<file>", "position": <diff_position>, "body": "..." }]
            - Submit via: gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/reviews -f event=COMMENT -f body="$SUMMARY" -f comments='[$COMMENTS_JSON]'
          - Do NOT use: gh pr review --approve or --request-changes

          Blocking behavior:
          - If BLOCKING_REVIEW is true and any 🚨 or 🔒 issues were posted: echo "CRITICAL_ISSUES_FOUND=true" >> $GITHUB_ENV
          - Otherwise: echo "CRITICAL_ISSUES_FOUND=false" >> $GITHUB_ENV
          - Always set CRITICAL_ISSUES_FOUND at the end
          '

      - name: Check blocking review results
        if: env.BLOCKING_REVIEW == 'true'
        run: |
          echo "Checking for critical issues..."
          echo "CRITICAL_ISSUES_FOUND: ${CRITICAL_ISSUES_FOUND:-unset}"

          if [ "${CRITICAL_ISSUES_FOUND:-false}" = "true" ]; then
            echo "❌ Critical issues found and blocking review is enabled. Failing the workflow."
            exit 1
          else
            echo "✅ No blocking issues found."
          fi

```

![Automated code review in action showing inline comments on a pull request](/docs-static/images/cli/cookbook/code-review/comment.png)

## Configure authentication

[Set up your API key and repository secrets](https://cursor.com/docs/cli/github-actions.md#authentication) to authenticate Cursor CLI in GitHub Actions.

## Set up agent permissions

Create a configuration file to control what actions the agent can perform. This prevents unintended operations like pushing code or creating pull requests.

Create `.cursor/cli.json` in your repository root:

```json
{
  "permissions": {
    "deny": [
      "Shell(git push)",
      "Shell(gh pr create)",
      "Write(**)"
    ]
  }
}
```

This configuration allows the agent to read files and use the GitHub CLI for comments, but prevents it from making changes to your repository. See the [permissions reference](https://cursor.com/docs/cli/reference/permissions.md) for more configuration options.

## Build the GitHub Actions workflow

Now let's build the workflow step by step.

### Set up the workflow trigger

Create `.github/workflows/cursor-code-review.yml` and configure it to run on pull requests:

```yaml
name: Cursor Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

jobs:
  code-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
```

### Checkout the repository

Add the checkout step to access the pull request code:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    ref: ${{ github.event.pull_request.head.sha }}
```

### Install Cursor CLI

Add the CLI installation step:

```yaml
- name: Install Cursor CLI
  run: |
    curl https://cursor.com/install -fsS | bash
    echo "$HOME/.cursor/bin" >> $GITHUB_PATH
```

For local testing on Windows, use PowerShell: `irm 'https://cursor.com/install?win32=true' | iex`

### Configure the review agent

Before implementing the full review step, let's understand the anatomy of our review prompt. This section outlines how we want the agent to behave:

**Objective**:
We want the agent to review the current PR diff and flag only clear, high-severity issues, then leave very short inline comments (1-2 sentences) on changed lines only with a brief summary at the end. This keeps the signal-to-noise ratio balanced.

**Format**:
We want comments that are short and to the point. We use emojis to make scanning comments easier, and we want a high-level summary of the full review at the end.

**Submission**:
When the review is done, we want the agent to include a short comment based on what was found during the review. The agent should submit one review containing inline comments plus a concise summary.

**Edge cases**:
We need to handle: - Existing comments being resolved: The agent should mark them as done when addressed - Avoid duplicates: The agent should skip commenting if similar feedback already exists on or near the same lines

**Final prompt**:
The complete prompt combines all these behavioral requirements to create focused, actionable feedback

Now let's implement the review agent step:

```yaml
- name: Perform code review
  env:
    CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
    GH_TOKEN: ${{ github.token }}
  run: |
    agent --force --model "$MODEL" --output-format=text --print "You are operating in a GitHub Actions runner performing automated code review. The gh CLI is available and authenticated via GH_TOKEN. You may comment on pull requests.

    Context:
    - Repo: ${{ github.repository }}
    - PR Number: ${{ github.event.pull_request.number }}
    - PR Head SHA: ${{ github.event.pull_request.head.sha }}
    - PR Base SHA: ${{ github.event.pull_request.base.sha }}

    Objectives:
    1) Re-check existing review comments and reply resolved when addressed
    2) Review the current PR diff and flag only clear, high-severity issues
    3) Leave very short inline comments (1-2 sentences) on changed lines only and a brief summary at the end

    Procedure:
    - Get existing comments: gh pr view --json comments
    - Get diff: gh pr diff
    - If a previously reported issue appears fixed by nearby changes, reply: ✅ This issue appears to be resolved by the recent changes
    - Avoid duplicates: skip if similar feedback already exists on or near the same lines

    Commenting rules:
    - Max 10 inline comments total; prioritize the most critical issues
    - One issue per comment; place on the exact changed line
    - Natural tone, specific and actionable; do not mention automated or high-confidence
    - Use emojis: 🚨 Critical 🔒 Security ⚡ Performance ⚠️ Logic ✅ Resolved ✨ Improvement

    Submission:
    - Submit one review containing inline comments plus a concise summary
    - Use only: gh pr review --comment
    - Do not use: gh pr review --approve or --request-changes"
```

```text
.
├── .cursor/
│   └── cli.json
├── .github/
│   └── workflows/
│       └── cursor-code-review.yml
```

## Test your reviewer

Create a test pull request to verify the workflow works and the agent posts review comments with emoji feedback.

![Pull request showing automated review comments with emojis and inline feedback on specific lines](/docs-static/images/cli/cookbook/code-review/github-actions.png)

## Next steps

You now have a working automated code review system. Consider these enhancements:

- Set up additional workflows for [fixing CI failures](https://cursor.com/docs/cli/cookbook/fix-ci.md)
- Configure different review levels for different branches
- Integrate with your team's existing code review process
- Customize the agent's behavior for different file types or directories

### Advanced: Blocking reviews

You can configure the workflow to fail if critical issues are found, preventing the pull request from being merged until addressed.

**Add blocking behavior to the prompt**

First, update your review agent step to include the `BLOCKING_REVIEW` environment variable and add this blocking behavior to the prompt:

```
Blocking behavior:
- If BLOCKING_REVIEW is true and any 🚨 or 🔒 issues were posted: echo "CRITICAL_ISSUES_FOUND=true" >> $GITHUB_ENV
- Otherwise: echo "CRITICAL_ISSUES_FOUND=false" >> $GITHUB_ENV
- Always set CRITICAL_ISSUES_FOUND at the end
```

**Add the blocking check step**

Then add this new step after your code review step:

```yaml
- name: Check blocking review results
  if: env.BLOCKING_REVIEW == 'true'
  run: |
    echo "Checking for critical issues..."
    echo "CRITICAL_ISSUES_FOUND: ${CRITICAL_ISSUES_FOUND:-unset}"

    if [ "${CRITICAL_ISSUES_FOUND:-false}" = "true" ]; then
      echo "❌ Critical issues found and blocking review is enabled. Failing the workflow."
      exit 1
    else
      echo "✅ No blocking issues found."
    fi
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)
