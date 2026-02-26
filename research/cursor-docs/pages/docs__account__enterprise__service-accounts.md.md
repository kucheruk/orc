# Service Accounts

Service Accounts are only available on the Enterprise plan. To get access, please ask your account manager or [contact sales](https://cursor.com/contact-sales?source=docs-service-accounts).

Service accounts will roll out to Enterprise accounts starting the week of 12/22.

Service accounts are non-human accounts that enable teams to securely automate Cursor-powered workflows at scale. With service accounts, you can configure Cursor, consume APIs, and invoke [cloud agents](https://cursor.com/docs/cloud-agent.md) without tying critical integrations to individual developers' personal accounts.

## Why use service accounts

As teams find new ways to automate coding tasks with Cursor cloud agents, APIs, and CLI, the need for centralized, secure automation becomes critical. Service accounts address this by:

- **Decoupling from individuals**: Automations continue running even as people and roles change
- **Secure credential management**: Easily rotate API keys without disrupting workflows
- **Centralized access control**: Admins manage all service account permissions in one place
- **Attribution and auditability**: Tie cloud agent runs to the initiating service or system

## Key features

### No additional seat required

Service accounts are included with your Enterprise plan at no extra cost. They do not consume a seat license.

### Usage consumption

Service accounts consume usage from your team's usage pool, just like human users. All usage is tracked and visible in your team's analytics and billing.

### Cloud agent integration

Service accounts can initiate [cloud agent](https://cursor.com/docs/cloud-agent.md) runs programmatically. This enables automation scenarios such as:

- A ticket created in Linear triggering a cloud agent to implement a feature
- An error in Sentry initiating a cloud agent to investigate and fix the issue
- Internal engineering services kicking off migrations or refactoring tasks

### Admin visibility

Cloud agent runs initiated by service accounts are accessible to all team admins. This ensures visibility and oversight of automated workflows across your organization.

### Repository access

Service accounts can initiate cloud agent runs on any repository that has been authorized via the [Cursor GitHub app](https://cursor.com/docs/integrations/github.md).

The GitHub integration must be connected at the team level for service accounts to access repositories. If you have a personal GitHub integration but no team-level integration, service accounts will not be able to initiate cloud agent runs.

To connect GitHub at the team level:

1. Navigate to **Dashboard** → **Settings** → **Integrations**
2. Connect the Cursor GitHub app to your organization
3. Authorize the repositories you want service accounts to access

Repository access is governed by the permissions configured for your team's GitHub app installation.

## Creating a service account

Admins can create and manage service accounts from the [Cursor Dashboard](https://cursor.com/dashboard).

1. Navigate to **Dashboard** → **Settings** → **Service Accounts**
2. Click **New Service Account**
3. Enter a name and optional description for the service account
4. Click **Create**

When you create a service account, an API key is generated. Copy this key immediately—it will only be shown once and cannot be retrieved later.

Store your API key securely. If you lose it, you'll need to rotate it to generate a new one.

## Managing API keys

Each service account can have API keys associated with it. You can:

- **View masked keys**: See the last few characters of each key for identification
- **Rotate keys**: Generate a new key and invalidate the old one
- **Archive service accounts**: Archive a service account and revoke all its API keys

### Rotating an API key

To rotate an API key:

1. Navigate to **Dashboard** → **Settings** → **Service Accounts**
2. Find the service account and click the rotate icon next to its API key
3. Copy the new key immediately

The old key is immediately invalidated. Update any integrations using the old key.

## Using service accounts with the API

Service accounts authenticate using their API key. Use the key in the `Authorization` header when making requests to the [Cloud Agents API](https://cursor.com/docs/cloud-agent/api/endpoints.md):

```bash
curl -X POST https://api.cursor.com/agents \
  -H "Authorization: Bearer YOUR_SERVICE_ACCOUNT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "owner/repo",
    "prompt": "Implement the feature described in issue #123"
  }'
```

See the [Cloud Agents API documentation](https://cursor.com/docs/cloud-agent/api/endpoints.md) for the full API reference.

## Security best practices

- **Rotate keys regularly**: Establish a key rotation schedule for your service accounts
- **Use descriptive names**: Name service accounts after their purpose (e.g., "Linear Integration", "Sentry Auto-Fix")
- **Limit scope**: Create separate service accounts for different automation workflows
- **Monitor usage**: Review service account activity in your team's analytics dashboard
- **Revoke unused accounts**: Archive service accounts that are no longer in use

## Archiving a service account

Archiving a service account:

- Revokes all API keys associated with the account
- Breaks any integrations using those keys
- Preserves the account record for auditability

To archive a service account:

1. Navigate to **Dashboard** → **Settings** → **Service Accounts**
2. Click the archive icon next to the service account
3. Confirm the archive action

Archived accounts can be viewed by clicking **Show Archived** on the Service Accounts page. This helps maintain a complete audit trail of service accounts used by your team.

### Service accounts are available on the Enterprise plan

Contact our team to automate Cursor-powered workflows at scale.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
