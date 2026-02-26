# Cloud Agents

Cloud agents leverage the same [agent fundamentals](https://cursor.com/learn/agents.md) but run in isolated environments in the cloud instead of on your local machine.

## Why use Cloud Agents?

You can run as many agents as you want in parallel, and they do not require your local machine to be connected to the internet.

Because they have access to their own virtual machine, cloud agents can build, test, and interact with the changed software. They can also use computers to control the desktop and browser.

## How to access

You can kick off cloud agents from wherever you work:

1. **Cursor Web**: Start and manage agents from [cursor.com/agents](https://cursor.com/agents) on any device
2. **Cursor Desktop**: Select **Cloud** in the dropdown under the agent input
3. **Slack**: Use the @cursor command to kick off an agent
4. **GitHub**: Comment `@cursor` on a PR or issue to kick off an agent
5. **Linear**: Use the @cursor command to kick off an agent
6. **API**: Use the API to kick off an agent

For a native-feeling mobile experience, install Cursor as a Progressive Web
App (PWA). On **iOS**, open [cursor.com/agents](https://cursor.com/agents) in
Safari, tap the share button, then "Add to Home Screen". On **Android**, open
the URL in Chrome, tap the menu, then "Install App".

### Use Cursor in Slack

Learn more about setting up and using the Slack integration, including
triggering agents and receiving notifications.

## How it works

### GitHub or GitLab connection

Cloud agents clone your repo from GitHub or GitLab and work on a separate branch, then push changes to your repo for handoff.

You need read-write privileges to your repo and any dependent repos or submodules. Support for other providers like Bitbucket is coming later.

## Models

Only [Max Mode](https://cursor.com/docs/context/max-mode.md)-compatible models are available for cloud agents.

## Related pages

- Learn more about [Cloud agent capabilities](https://cursor.com/docs/cloud-agent/capabilities.md).
- Learn more about [Cloud Agent pricing](https://cursor.com/docs/account/pricing.md#cloud-agent).
- Learn more about [Cloud agent security](https://cursor.com/docs/cloud-agent/security.md).
- Learn more about [Cloud agent settings](https://cursor.com/docs/cloud-agent/settings.md).

## Troubleshooting

### Agent runs are not starting

- Ensure you're logged in and have connected your GitHub or GitLab account.
- Check that you have the necessary repository permissions.
- You need to be on a trial or paid plan with usage-based pricing enabled.
- To enable usage-based pricing, go to your [Dashboard](https://www.cursor.com/dashboard?tab=settings) settings tab.

### My secrets aren't available to the cloud agent

- Ensure you've added secrets in [cursor.com/dashboard?tab=cloud-agents](https://cursor.com/dashboard?tab=cloud-agents)
- Secrets are workspace/team-scoped; make sure you're using the correct account
- Try restarting the cloud agent after adding new secrets

### Can't find the Secrets tab

- If you don't see it, ensure you have the necessary permissions

### Do snapshots copy .env.local files?

Snapshots save your base environment configuration (installed packages, system dependencies, etc.).
If you include `.env.local` files during snapshot creation, they will be saved. However, using the Secrets tab
in Cursor Settings is the recommended approach for managing environment variables.

### Slack integration not working

Verify that your workspace admin has installed the Cursor Slack app and that
you have the proper permissions.

## Naming History

Cloud Agents were formerly called Background Agents.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
