# Commands

Custom commands allow you to create reusable workflows that can be triggered with a simple `/` prefix in the chat input box. These commands help standardize processes across your team and make common tasks more efficient.

![Commands input example](/docs-static/images/chat/commands/input.png)

Commands are currently in beta. The feature and syntax may change as we continue to improve it.

## How commands work

Commands are defined as plain Markdown files that can be stored in three locations:

1. **Project commands**: Stored in the `.cursor/commands` directory of your project
2. **Global commands**: Stored in the `~/.cursor/commands` directory in your home directory
3. **Team commands**: Created by team admins in the [Cursor Dashboard](https://cursor.com/dashboard?tab=team-content\&section=commands) and automatically available to all team members

When you type `/` in the chat input box, Cursor will automatically detect and display available commands from all locations, making them instantly accessible across your workflow.

## Creating commands

1. Create a `.cursor/commands` directory in your project root
2. Add `.md` files with descriptive names (e.g., `review-code.md`, `write-tests.md`)
3. Write plain Markdown content describing what the command should do
4. Commands will automatically appear in the chat when you type `/`

Here's an example of how your commands directory structure might look:

```bash
.cursor/
└── commands/
    ├── address-github-pr-comments.md
    ├── code-review-checklist.md
    ├── create-pr.md
    ├── light-review-existing-diffs.md
    ├── onboard-new-developer.md
    ├── run-all-tests-and-fix.md
    ├── security-audit.md
    └── setup-new-feature.md
```

## Team commands

Team commands are available on Team and Enterprise plans.

Team admins can create server-enforced custom commands that are automatically available to all team members. This makes it easy to share standardized prompts and workflows across your entire organization.

### Creating team commands

1. Navigate to the [Team Content dashboard](https://cursor.com/dashboard?tab=team-content\&section=commands)
2. Click to create a new command
3. Provide:
   - **Name**: The command name that will appear after the `/` prefix
   - **Description** (optional): Helpful context about what the command does
   - **Content**: The Markdown content that defines the command's behavior
4. Save the command

Once created, team commands are immediately available to all team members when they type `/` in the chat input box. Team members don't need to manually sync or download anything - the commands are automatically synchronized.

### Benefits of team commands

- **Centralized management**: Update commands once and changes are instantly available to all team members
- **Standardization**: Ensure everyone uses consistent workflows and best practices
- **Easy sharing**: No need to distribute files or coordinate updates across the team
- **Access control**: Only team admins can create and modify team commands

## Parameters

You can provide additional context to a command in the Agent chat input. Anything you type after the command name is included in the model prompt alongside your provided input. For example:

```text
/commit and /pr these changes to address DX-523
```

## Examples

Try these commands in your projects to get a feel for how they work.

### Code review checklist

```markdown
# Code Review Checklist

## Overview
Comprehensive checklist for conducting thorough code reviews to ensure quality, security, and maintainability.

## Review Categories

### Functionality
- [ ] Code does what it's supposed to do
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] No obvious bugs or logic errors

### Code Quality
- [ ] Code is readable and well-structured
- [ ] Functions are small and focused
- [ ] Variable names are descriptive
- [ ] No code duplication
- [ ] Follows project conventions

### Security
- [ ] No obvious security vulnerabilities
- [ ] Input validation is present
- [ ] Sensitive data is handled properly
- [ ] No hardcoded secrets
```

### Security audit

```markdown
# Security Audit

## Overview
Comprehensive security review to identify and fix vulnerabilities in the codebase.

## Steps
1. **Dependency audit**
   - Check for known vulnerabilities
   - Update outdated packages
   - Review third-party dependencies

2. **Code security review**
   - Check for common vulnerabilities
   - Review authentication/authorization
   - Audit data handling practices

3. **Infrastructure security**
   - Review environment variables
   - Check access controls
   - Audit network security

## Security Checklist
- [ ] Dependencies updated and secure
- [ ] No hardcoded secrets
- [ ] Input validation implemented
- [ ] Authentication secure
- [ ] Authorization properly configured
```

### Setup new feature

```markdown
# Setup New Feature

## Overview
Systematically set up a new feature from initial planning through to implementation structure.

## Steps
1. **Define requirements**
   - Clarify feature scope and goals
   - Identify user stories and acceptance criteria
   - Plan technical approach

2. **Create feature branch**
   - Branch from main/develop
   - Set up local development environment
   - Configure any new dependencies

3. **Plan architecture**
   - Design data models and APIs
   - Plan UI components and flow
   - Consider testing strategy

## Feature Setup Checklist
- [ ] Requirements documented
- [ ] User stories written
- [ ] Technical approach planned
- [ ] Feature branch created
- [ ] Development environment ready
```

### Create pull request

```markdown
# Create PR

## Overview
Create a well-structured pull request with proper description, labels, and reviewers.

## Steps
1. **Prepare branch**
   - Ensure all changes are committed
   - Push branch to remote
   - Verify branch is up to date with main

2. **Write PR description**
   - Summarize changes clearly
   - Include context and motivation
   - List any breaking changes
   - Add screenshots if UI changes

3. **Set up PR**
   - Create PR with descriptive title
   - Add appropriate labels
   - Assign reviewers
   - Link related issues

## PR Template
- [ ] Feature A
- [ ] Bug fix B
- [ ] Unit tests pass
- [ ] Manual testing completed
```

### Run tests and fix failures

```markdown
# Run All Tests and Fix Failures

## Overview
Execute the full test suite and systematically fix any failures, ensuring code quality and functionality.

## Steps
1. **Run test suite**
   - Execute all tests in the project
   - Capture output and identify failures
   - Check both unit and integration tests

2. **Analyze failures**
   - Categorize by type: flaky, broken, new failures
   - Prioritize fixes based on impact
   - Check if failures are related to recent changes

3. **Fix issues systematically**
   - Start with the most critical failures
   - Fix one issue at a time
   - Re-run tests after each fix
```

### Onboard new developer

```markdown
# Onboard New Developer

## Overview
Comprehensive onboarding process to get a new developer up and running quickly.

## Steps
1. **Environment setup**
   - Install required tools
   - Set up development environment
   - Configure editor and extensions
   - Set up git and SSH keys

2. **Project familiarization**
   - Review project structure
   - Understand architecture
   - Read key documentation
   - Set up local database

## Onboarding Checklist
- [ ] Development environment ready
- [ ] All tests passing
- [ ] Can run application locally
- [ ] Database set up and working
- [ ] First PR submitted
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)
