# Network access

Control which network resources your Cloud Agents can reach. These settings are available on the [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents) for individual users and team admins.

## Access modes

Three modes control outbound network access for Cloud Agents:

| Mode                         | Behavior                                                                                                                                                                                                                            |
| :--------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Allow all network access** | Cloud Agents can reach any external host. No domain restrictions apply.                                                                                                                                                             |
| **Default + allowlist**      | Cloud Agents can reach the [default domains](https://cursor.com/docs/agent/terminal.md#default-network-allowlist) (common package registries, cloud providers, and language toolchains) plus any domains you add to your allowlist. |
| **Allowlist only**           | Cloud Agents can only reach the domains you explicitly add to your allowlist.                                                                                                                                                       |

Even in **Allowlist only** mode, a small set of domains remain accessible so Cloud Agents can function. These include Cursor's own services and source control management (SCM) providers.

## Setting the mode

### User-level settings

Individual users can configure their network access mode from the [Cloud Agents dashboard](https://cursor.com/dashboard?tab=cloud-agents) under the **Security** header → **Network Access Settings**. Your user-level setting applies to all Cloud Agents you create.

When you select a mode that includes an allowlist (**Default + allowlist** or **Allowlist only**), an allowlist configuration section appears below the setting where you can add your custom domains.

### Team-level settings

Team admins can set a default network access mode for the entire team from the same dashboard. The team-level allowlist is the same allowlist that admins configure for the [sandbox default network allowlist](https://cursor.com/docs/agent/terminal.md#default-network-allowlist). There is no separate allowlist to manage; one allowlist controls both Cloud Agent network access and the sandbox defaults.

When a team-level setting exists:

- If a user has configured their own setting, the **user setting takes precedence**.
- If a user has not configured a setting, the **team default applies**.

## Locking the setting (Enterprise)

Locking is available for Enterprise teams only.

Enterprise team admins can lock the network access setting using the **Lock Network Access Policy** option. When locked:

- The team-level setting applies to every member, regardless of their individual preference.
- Users cannot override the locked setting from their own dashboard.

This gives admins full control over Cloud Agent network access across the organization.

## Relationship to sandbox network policy

The "Default" domains in the **Default + allowlist** mode are the same [default network allowlist](https://cursor.com/docs/agent/terminal.md#default-network-allowlist) used by the desktop Agent's sandbox. The team-level allowlist is also shared: when an admin configures an allowlist on the dashboard, it applies to both Cloud Agent network access and the [sandbox network policy](https://cursor.com/docs/agent/terminal.md#sandbox-configuration).


---

## Sitemap

[Overview of all docs pages](/llms.txt)
