# Modes

Agent offers different modes optimized for specific tasks. Each mode has different capabilities and tools enabled to match your workflow needs.

Understanding [how agents work](https://cursor.com/learn/agents.md) and [tool calling fundamentals](https://cursor.com/learn/tool-calling.md) will help you choose the right mode for your task.

| Mode                                                      | For                                 | Capabilities                                                       | Tools                    |
| :-------------------------------------------------------- | :---------------------------------- | :----------------------------------------------------------------- | :----------------------- |
| **[Agent](https://cursor.com/docs/agent/modes.md#agent)** | Complex features, refactoring       | Autonomous exploration, multi-file edits                           | All tools enabled        |
| **[Ask](https://cursor.com/docs/agent/modes.md#ask)**     | Learning, planning, questions       | Read-only exploration, no automatic changes                        | Search tools only        |
| **[Plan](https://cursor.com/docs/agent/modes.md#plan)**   | Complex features requiring planning | Creates detailed plans before execution, asks clarifying questions | All tools enabled        |
| **[Debug](https://cursor.com/docs/agent/modes.md#debug)** | Tricky bugs, regressions            | Hypothesis generation, log instrumentation, runtime analysis       | All tools + debug server |

## Agent

The default mode for complex coding tasks. Agent autonomously explores your codebase, edits multiple files, runs commands, and fixes errors to complete your requests.

![Agent mode](/docs-static/images/chat/agent.png)

## Ask

Read-only mode for learning and exploration. Ask searches your codebase and provides answers without making any changes - perfect for understanding code before modifying it.

![Ask mode](/docs-static/images/chat/ask.png)

## Plan

Plan Mode creates detailed implementation plans before writing any code. Agent researches your codebase, asks clarifying questions, and generates a reviewable plan you can edit before building.

Press Shift+Tab from the chat input to rotate to Plan Mode. Cursor also suggests it automatically when you type keywords that indicate complex tasks.

### How it works

1. Agent asks clarifying questions to understand your requirements
2. Researches your codebase to gather relevant context
3. Creates a comprehensive implementation plan
4. You review and edit the plan through chat or markdown files
5. Click to build the plan when ready

Plans are saved by default in your home directory. Click "Save to workspace" to move it to your workspace for future reference, team sharing, and documentation.

### When to use Plan Mode

Plan Mode works best for:

- Complex features with multiple valid approaches
- Tasks that touch many files or systems
- Unclear requirements where you need to explore before understanding scope
- Architectural decisions where you want to review the approach first

For quick changes or tasks you've done many times before, jumping straight to Agent mode is fine.

### Starting over from a plan

Sometimes Agent builds something that doesn't match what you wanted. Instead of trying to fix it through follow-up prompts, go back to the plan.

Revert the changes, refine the plan to be more specific about what you need, and run it again. This is often faster than fixing an in-progress agent, and produces cleaner results.

For larger changes, spend extra time creating a precise, well-scoped plan. The hard part is often figuring out **what** change should be made—a task suited well for humans. With the right instructions, delegate implementation to Agent.

## Debug

Debug Mode helps you find root causes and fix tricky bugs that are hard to reproduce or understand. Instead of immediately writing code, the agent generates hypotheses, adds log statements, and uses runtime information to pinpoint the exact issue before making a targeted fix.

![Debug Mode showing collected logs and reproduction steps](/docs-static/images/chat/debug-mode-steps.png)

### When to use Debug Mode

Debug Mode works best for:

- **Bugs you can reproduce but can't figure out**: When you know something is wrong but the cause isn't obvious from reading the code
- **Race conditions and timing issues**: Problems that depend on execution order or async behavior
- **Performance problems and memory leaks**: Issues that require runtime profiling to understand
- **Regressions where something used to work**: When you need to trace what changed

When standard Agent interactions struggle with a bug, Debug Mode provides a different approach—using runtime evidence rather than guessing at fixes.

### How it works

1. **Explore and hypothesize**: The agent explores relevant files, builds context, and generates multiple hypotheses about potential root causes.

2. **Add instrumentation**: The agent adds log statements that send data to a local debug server running in a Cursor extension.

3. **Reproduce the bug**: Debug Mode asks you to reproduce the bug and provides specific steps. This keeps you in the loop and ensures the agent captures real runtime behavior.

4. **Analyze logs**: After reproduction, the agent reviews the collected logs to identify the actual root cause based on runtime evidence.

5. **Make targeted fix**: The agent makes a focused fix that directly addresses the root cause—often just a few lines of code.

6. **Verify and clean up**: You can re-run the reproduction steps to verify the fix. Once confirmed, the agent removes all instrumentation.

### Tips for Debug Mode

- **Provide detailed context**: The more you describe the bug and how to reproduce it, the better the agent's instrumentation will be. Include error messages, stack traces, and specific steps.
- **Follow reproduction steps exactly**: Execute the steps the agent provides to ensure logs capture the actual issue.
- **Reproduce multiple times if needed**: Reproducing the bug multiple times may help the agent identify particularly tricky problems like race conditions.
- **Be specific about expected vs. actual behavior**: Help the agent understand what should happen versus what is happening.

## Custom slash commands

For specialized workflows, you can create [custom slash commands](https://cursor.com/docs/agent/chat/commands.md) that combine specific instructions with tool limitations.

### Examples

### Learn

Create a `/learn` command that focuses on explaining concepts thoroughly and asks clarifying questions. To limit the agent to search tools only, include instructions in the command prompt like: "Use only search tools (read file, codebase search, grep) - do not make any edits or run terminal commands."

### Refactor

Create a `/refactor` command that instructs the agent to improve code structure without adding new functionality. Include in the prompt: "Focus on refactoring existing code - improve structure, readability, and organization without adding new features."

### Debug

Create a `/debug` command that instructs the agent to investigate issues thoroughly before proposing fixes. Include in the prompt: "Investigate the issue using search tools and terminal commands first. Only propose fixes after thoroughly understanding the root cause."

See the [Commands documentation](https://cursor.com/docs/agent/chat/commands.md) for details on creating custom slash commands.

## Switching modes

- Use the mode picker dropdown in Agent
- Press Cmd+. for quick switching
- Set keyboard shortcuts in [settings](https://cursor.com/docs/agent/modes.md#settings)

## Settings

All modes share common configuration options:

| Setting            | Description                           |
| :----------------- | :------------------------------------ |
| Model              | Choose which AI model to use          |
| Keyboard shortcuts | Set shortcuts to switch between modes |

Mode-specific settings:

| Mode      | Settings                     | Description                               |
| :-------- | :--------------------------- | :---------------------------------------- |
| **Agent** | Auto-run and Auto-fix Errors | Automatically run commands and fix errors |
| **Ask**   | Search Codebase              | Automatically find relevant files         |


---

## Sitemap

[Overview of all docs pages](/llms.txt)
