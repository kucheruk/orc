# Dashboard settings

Workspace admins can configure additional settings from the Cloud Agents tab on the dashboard.

### Defaults Settings

- **Default model** – the model used when a run does not specify one. Pick any model that supports Max Mode.
- **Default repository** – when empty, agents ask the user to choose a repo. Supplying a repo here lets users skip that step.
- **Base branch** – the branch agents fork from when creating pull requests. Leave blank to use the repository’s default branch.

### Network access settings

Control which network resources Cloud Agents can reach. Choose from three modes:

- **Allow all network access** – no domain restrictions.
- **Default + allowlist** – the [default domains](https://cursor.com/docs/agent/terminal.md#default-network-allowlist) plus any domains you add.
- **Allowlist only** – only domains you explicitly add.

Users and team admins can both configure this setting. User settings take precedence over team defaults unless the admin has locked the setting. See [Network Access](https://cursor.com/docs/cloud-agent/network-access.md) for full details.

### Security Settings

All security options require admin privileges.

- **Display agent summary** – controls whether Cursor shows the agent's file-diff images and code snippets. Disable this if you prefer not to expose file paths or code in the sidebar.
- **Display agent summary in external channels** – extends the previous toggle to Slack or any external channel you've connected.
- **Team follow-ups** – controls whether team members can send follow-up messages to cloud agents created by other users on the team. See [team follow-ups](https://cursor.com/docs/cloud-agent/settings.md#team-follow-ups) below.

### Team feature settings

Team admins can enable or disable these features for their team:

- **Long running agents** – controls whether team members can run agents for extended durations. Admins can enable or restrict this capability at the team level.
- **Computer use** – controls whether agents can use computer interaction capabilities (available to enterprise teams only).

Changes save instantly and affect new agents immediately.

### Team follow-ups

Team members can send follow-up messages to cloud agents created by other users on the same team. This is useful when a teammate starts an agent and you need to course-correct, add context, or continue the work while they're unavailable.

Team admins control this behavior from the [Cloud Agents security settings](https://cursor.com/dashboard?tab=cloud-agents) with three options:

| Setting                   | Behavior                                                                                                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Disabled**              | Only the original creator can send follow-ups to their agent. No team follow-ups are allowed.                                                                                              |
| **Service accounts only** | Team members can send follow-ups to agents created by a [service account](https://cursor.com/docs/account/enterprise/service-accounts.md), but not to agents created by other human users. |
| **All**                   | Any team member can send follow-ups to any agent on the team, regardless of who created it.                                                                                                |

### Lateral movement and secret exposure

Enabling team follow-ups means a user can influence the execution of a cloud agent that runs with *another user's* secrets and credentials. A follow-up message can instruct the agent to read environment variables, print secrets to logs, push credentials to an external endpoint, or perform actions using the original creator's access tokens.

A team member with limited permissions could escalate their access by directing an agent that holds a more privileged user's secrets. Treat this setting with the same care you would give shared SSH keys or service credentials.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
