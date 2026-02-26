# Setup

Cloud agents run on an isolated Ubuntu machine. We recommend configuring this environment so that the agent has access to similar tools a human developer.

Go to [cursor.com/onboard](https://cursor.com/onboard) to configure your environment.

## Environment Options

There are two main ways to configure the environment for your cloud agent:

1. Let Cursor's agent set up its own environment at [cursor.com/onboard](https://cursor.com/onboard). After the agent is done, you will have the option to create a snapshot of its virtual machine that can be reused for future agents.
2. Manually configure the environment with a Dockerfile. If you choose this option, you can specify the Dockerfile in a `.cursor/environment.json` file.

Both options generate an environment, and also allow you to specify an update command that will be run before the agent starts to ensure that its dependencies are up to date (e.g. `npm install`, `pip install`, etc.).

### Agent-driven setup (recommended)

You will be asked to connect your GitHub or GitLab account and select the repository you want to work on.

Then, you provide Cursor with the environment variables and secrets it will need to install dependencies and run the code.

Finally, after Cursor has installed the dependencies and verified the code is working, you can save a snapshot of its virtual machine to be reused for future agents.

### Manual setup with Dockerfile (advanced)

For advanced cases, configure the environment with a Dockerfile:

- Create a Dockerfile to install system-level dependencies, use specific compiler versions, install debuggers, or switch the base OS image
- Do not `COPY` the full project; Cursor manages the workspace and checks out the correct commit
- Take a snapshot manually after configuration
- Edit `.cursor/environment.json` directly to configure runtime settings

You configure the environment with a Dockerfile; you do not get direct access to the remote machine.

### Computer use limitation

Computer use is not currently supported for repos with Dockerfiles or a snapshot configured via `environment.json`. Support for this is coming soon.

## Update command

When a new machine boots, Cursor starts from the base environment, then runs the `update` command (called `install` in `environment.json`).

For most repos, `install` is `npm install`, `bazel build`, or a similar dependency setup command.

To keep startup fast, Cursor caches disk state after `install` runs. Write `install` so it can run multiple times safely. Only disk state persists from `install`; processes started during `install` are not kept alive for agent runtime.

## Startup commands

After `install`, the machine starts and runs the `start` command, then any configured `terminals`. Use this to start processes that should stay alive while the agent runs.

You can skip `start` in many repos. If your environment depends on Docker, add `sudo service docker start` in `start`.

`terminals` are for app code processes. These terminals run in a `tmux` session shared by you and the agent.

## Environment variables and secrets

Cloud agents need environment variables and secrets such as API keys and database credentials.

### Recommended: use the Secrets tab in Cursor settings

The easiest way to manage secrets is through [cursor.com](https://cursor.com/dashboard?tab=cloud-agents).

Add secrets as key-value pairs. Secrets are:

- Encrypted at rest with KMS
- Exposed to cloud agents as environment variables
- Shared across cloud agents for your workspace or team

As an additional level of security, you have the option to specify secrets as redacted. Redacted secrets are scanned in commits the agent makes to prevent the agent from accidentally committing secrets to the repository. They are also redacted in the tool call results so they are not exposed to the agent, or stored in the chat transcript.

### Monorepos with multiple `.env` files

If your monorepo has multiple `.env.local` files:

- Add values from all `.env.local` files to the same Secrets tab
- Use unique variable names when keys overlap, such as `NEXTJS_*` and `CONVEX_*`
- Reference those variables from each app as needed

If you include `.env.local` files while taking a snapshot, they can be saved and available to cloud agents. The Secrets tab remains the recommended approach for security and management.

## The environment.json spec

Your `environment.json` can look like this:

```json
{
  "build": {
    "dockerfile": "Dockerfile",
    "context": ".."
  },
  "install": "npm install",
  "terminals": [
    {
      "name": "Run Next.js",
      "command": "npm run dev"
    }
  ]
}
```

### Important path behavior

The `dockerfile` and `context` paths in `build` are relative to `.cursor`.
The `install` command runs from your project root.

The full schema is [defined here](https://www.cursor.com/schemas/environment.schema.json).


---

## Sitemap

[Overview of all docs pages](/llms.txt)
