# Quickstart

This quickstart walks you through working with Cursor's Agent. By the end, you'll understand how to plan effectively, manage context, and iterate on code with AI.

## Start with Agent

Open the Agent panel with Cmd I. Agent can complete complex coding tasks independently: searching your codebase, editing files, and running terminal commands.

How does this project work?

Agent will explore the codebase, read relevant files, and explain the architecture. This is one of the fastest ways to understand unfamiliar code.

## Plan before building

The most impactful change you can make is planning before coding.

Press Shift+Tab in the agent input to toggle **Plan Mode**. Instead of immediately writing code, Agent will:

1. Research your codebase to find relevant files
2. Ask clarifying questions about your requirements
3. Create a detailed implementation plan
4. Wait for your approval before building

Click "Save to workspace" to store plans in `.cursor/plans/`. This creates documentation for your team and provides context for future work.

Try it: Ask Agent to "add a new feature" in Plan Mode. Review the plan, make adjustments, then click to build.

## Let Agent find context

You don't need to manually tag every file in your prompt.

Agent has powerful search tools and pulls context on demand. When you ask about "the authentication flow," Agent finds relevant files through search, even if your prompt doesn't contain the exact file names.

Keep it simple: if you know the exact file, tag it with `@`. If not, Agent will find it. Including irrelevant files can confuse Agent about what's important.

## Write specific prompts

Agent's success rate improves significantly with specific instructions. Compare:

| Vague                   | Specific                                                                                                             |
| :---------------------- | :------------------------------------------------------------------------------------------------------------------- |
| "add tests for auth.ts" | "Write a test case for auth.ts covering the logout edge case, using the patterns in `__tests__/` and avoiding mocks" |
| "fix the bug"           | "The login form submits twice when clicking the button. Find the cause and fix it"                                   |

Be explicit about what you want, reference existing patterns, and describe the expected outcome.

## Know when to start fresh

Long conversations can cause Agent to lose focus. Start a new conversation when:

- You're moving to a different task or feature
- Agent seems confused or keeps making the same mistakes
- You've finished one logical unit of work

Continue the conversation when:

- You're iterating on the same feature
- Agent needs context from earlier in the discussion
- You're debugging something it just built

Use `@Past Chats` to reference previous work in new conversations rather than copy-pasting entire discussions.

## Review and iterate

Watch Agent work. The diff view shows changes as they happen. If you see Agent heading in the wrong direction, press **Escape** to interrupt and redirect.

After Agent finishes, click **Review** → **Find Issues** to run a dedicated review pass that analyzes proposed edits and flags potential problems.

AI-generated code can look right while being subtly wrong. Read the diffs carefully. The faster an agent works, the more important your review process becomes.

## Provide verifiable goals

Agents perform best when they have clear targets to iterate against:

- **Use typed languages** so Agent gets immediate feedback from the type checker
- **Write tests** so Agent can run them and iterate until they pass
- **Configure linters** to catch style and quality issues automatically

Try this workflow: Ask Agent to write tests first, confirm they fail, then ask it to implement code that passes the tests.

## Next steps

### Agent Overview

Learn about Agent's tools and capabilities

### Rules

Create persistent instructions for your project

### Common Workflows

TDD, git workflows, and more patterns

### AI Foundations

Deep dive into how AI works


---

## Sitemap

[Overview of all docs pages](/llms.txt)
