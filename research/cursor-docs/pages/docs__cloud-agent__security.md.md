# Security

Cloud Agents are available in Privacy Mode. We never train on your code and only retain code for running the agent. [Learn more about Privacy mode](https://www.cursor.com/privacy-overview).

## Secret protection

Secrets provided to Cloud Agents are encrypted at rest and in transit. They are not visible to anyone other than the Cloud Agent user.

You can classify secrets as "Redacted" for additional protection. Redacted secrets:

- Are scanned in commit messages and files, which are rejected if they contain the secret
- Are redacted from model tool calls, so they are not shown to the models or stored in chat transcripts

This prevents accidental exposure of credentials in version control and model context.

## What you should know

1. Grant read-write privileges to our GitHub app for repos you want to edit. We use this to clone the repo and make changes.
2. Your code runs inside our AWS infrastructure in isolated VMs and is stored on VM disks while the agent is accessible.
3. The agent has internet access by default. You can configure [network egress controls](https://cursor.com/docs/cloud-agent/network-access.md) to restrict the domains the agent can access.
4. The agent auto-runs all terminal commands, letting it iterate on tests. This differs from the foreground agent, which requires user approval for every command. Auto-running introduces data exfiltration risk: attackers could execute prompt injection attacks, tricking the agent to upload code to malicious websites. See [OpenAI's explanation about risks of prompt injection for cloud agents](https://platform.openai.com/docs/codex/agent-network#risks-of-agent-internet-access).
5. If privacy mode is disabled, we collect prompts and dev environments to improve the product.
6. If you disable privacy mode when starting a cloud agent, then enable it during the agent's run, the agent continues with privacy mode disabled until it completes.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
