# Common Agent Workflows

These are proven patterns for working effectively with Cursor's Agent. Each workflow leverages Agent's ability to search, edit, and run commands autonomously.

## Test-driven development

Agents perform best when they have a clear target to iterate against. Tests provide exactly that—a verifiable goal the agent can work toward.

### The TDD workflow

1. **Ask Agent to write tests** based on expected input/output pairs. Be explicit that you're doing TDD so it avoids creating mock implementations for functionality that doesn't exist yet.

2. **Tell Agent to run the tests and confirm they fail.** Explicitly say not to write implementation code at this stage.

3. **Commit the tests** when you're satisfied with them.

4. **Ask Agent to write code that passes the tests**, instructing it not to modify the tests. Tell it to keep iterating until all tests pass.

5. **Commit the implementation** once you're satisfied with the changes.

This workflow works especially well because Agent can run tests, see failures, and iterate automatically. The test suite becomes the acceptance criteria.

### Example prompts

```text
Write tests for a function that validates email addresses. 
Expected behavior:
- "user@example.com" returns true
- "invalid-email" returns false  
- Empty string returns false

Use the testing patterns in `__tests__/`. Don't implement the function yet—I want the tests to fail first.
```

```text
Now implement the validateEmail function to pass all tests. 
Don't modify the tests. Keep iterating until all tests pass.
```

## Git workflows with commands

Commands let you automate multi-step git workflows. Store them as Markdown files in `.cursor/commands/` and trigger them with `/` in the agent input.

### Pull request command

Create `.cursor/commands/pr/COMMAND.md`:

```markdown
Create a pull request for the current changes.

1. Look at the staged and unstaged changes with `git diff`
2. Write a clear commit message based on what changed
3. Commit and push to the current branch
4. Use `gh pr create` to open a pull request with title/description
5. Return the PR URL when done
```

Now type `/pr` in Agent to commit, push, and open a PR automatically.

### Fix issue command

Create `.cursor/commands/fix-issue/COMMAND.md`:

```markdown
Fix the GitHub issue specified by the user.

1. Fetch issue details with `gh issue view <number>`
2. Search the codebase to find relevant code
3. Implement a fix following existing patterns
4. Write tests if appropriate
5. Open a PR referencing the issue
```

Usage: `/fix-issue 123`

### Other useful commands

| Command        | Purpose                                                                              |
| :------------- | :----------------------------------------------------------------------------------- |
| `/review`      | Run linters, check for common issues, summarize what needs attention                 |
| `/update-deps` | Check for outdated dependencies and update them one by one, running tests after each |
| `/docs`        | Generate or update documentation for recent changes                                  |

Check commands into git so your whole team can use them. When you see Agent make a workflow mistake, update the command.

## Codebase understanding

When onboarding to a new codebase, use Agent as you would a knowledgeable teammate. Ask the same questions you'd ask a colleague:

### Example questions

- "How does logging work in this project?"
- "How do I add a new API endpoint?"
- "What edge cases does `CustomerOnboardingFlow` handle?"
- "Why are we calling `setUser()` instead of `createUser()` on line 1738?"
- "Walk me through what happens when a user submits the login form"

Agent uses both grep and semantic search to explore the codebase and find answers. This is one of the fastest ways to ramp up on unfamiliar code.

### Building understanding incrementally

Start broad and narrow down:

1. "Give me a high-level overview of this codebase"
2. "How does the authentication system work?"
3. "Show me the token refresh flow specifically"
4. "Why does this function check for null here?"

Each question builds on the last, and Agent maintains context throughout the conversation.

## Architecture diagrams

For significant changes or documentation, ask Agent to generate architecture diagrams.

### Example prompt

```text
Create a Mermaid diagram showing the data flow for our authentication system, 
including OAuth providers, session management, and token refresh.
```

Agent will analyze the codebase and generate a diagram you can include in documentation. These diagrams are useful for:

- PR descriptions explaining complex changes
- Documentation for new team members
- Revealing architectural issues before code review

## Long-running agent loops

Using [hooks](https://cursor.com/docs/agent/hooks.md), you can create agents that run for extended periods, iterating until they achieve a goal.

### Example: Run until tests pass

Configure the hook in `.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "stop": [{ "command": "bun run .cursor/hooks/grind.ts" }]
  }
}
```

The hook script (`.cursor/hooks/grind.ts`) receives context and returns a `followup_message` to continue the loop:

```typescript
import { readFileSync, existsSync } from "fs";

interface StopHookInput {
  conversation_id: string;
  status: "completed" | "aborted" | "error";
  loop_count: number;
}

const input: StopHookInput = await Bun.stdin.json();
const MAX_ITERATIONS = 5;

if (input.status !== "completed" || input.loop_count >= MAX_ITERATIONS) {
  console.log(JSON.stringify({}));
  process.exit(0);
}

const scratchpad = existsSync(".cursor/scratchpad.md")
  ? readFileSync(".cursor/scratchpad.md", "utf-8")
  : "";

if (scratchpad.includes("DONE")) {
  console.log(JSON.stringify({}));
} else {
  console.log(JSON.stringify({
    followup_message: `[Iteration ${input.loop_count + 1}/${MAX_ITERATIONS}] Continue working. Update .cursor/scratchpad.md with DONE when complete.`
  }));
}
```

This pattern is useful for:

- Running and fixing until all tests pass
- Iterating on UI until it matches a design mockup
- Any goal-oriented task where success is verifiable

## Design to code

Agent can process images directly. Paste screenshots, drag in design files, or reference image paths.

### Workflow

1. Paste a design mockup into the agent input
2. Ask Agent to implement the component
3. Agent matches layouts, colors, and spacing from the image
4. Use the [browser sidebar](https://cursor.com/docs/agent/browser.md) to preview and iterate

For more complex designs, you can also use the [Figma MCP server](https://cursor.com/docs/context/mcp/directory.md) to pull design data directly.

### Visual debugging

Screenshot an error state or unexpected UI and paste it into Agent. This is often faster than describing the problem in words.

Agent can also control a browser to take its own screenshots, test applications, and verify visual changes. See the [Browser documentation](https://cursor.com/docs/agent/browser.md) for details.

## Delegating to cloud agents

[Cloud agents](https://cursor.com/docs/cloud-agent.md) work well for tasks you'd otherwise add to a todo list:

- Bug fixes that came up while working on something else
- Refactors of recent code changes
- Generating tests for existing code
- Documentation updates

Start cloud agents from [cursor.com/agents](https://cursor.com/agents), the Cursor editor, or from your phone. They run in remote sandboxes, so you can close your laptop and check results later.

You can trigger agents from Slack with "@Cursor". See the [Slack integration](https://cursor.com/docs/integrations/slack.md) for setup.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
