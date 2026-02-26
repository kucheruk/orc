# Cursor Docs Unified Blob

- Generated from: /Users/vetinary/work/orc/research/cursor-docs/urls.txt
- Total URLs in index: 114
- Included pages: 111
- Missing pages: 3

## Missing URLs
- https://cursor.com/es/docs/bugbot.md`
- https://cursor.com/fr/docs/bugbot.md`
- https://cursor.com/ja/docs/bugbot.md`



================================================================================
# SOURCE: https://cursor.com/docs.md
# INDEX: 1/114
================================================================================

# Cursor Documentation

Cursor is an AI editor and coding agent. Describe what you want to build or change in natural language and Cursor will write the code for you.

![Welcome to Cursor, the AI editor and coding agent](/docs-static/images/agent/review.jpg)

## Models

See all models attributes in the [Models](https://cursor.com/docs/models.md) page.

| Model                                                                                         | Provider  | Default context | Max mode | Capabilities            | Notes                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------- | --------- | --------------- | -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Claude 4 Sonnet](https://www.anthropic.com/claude/sonnet)                                    | Anthropic | 200k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Claude 4 Sonnet 1M](https://www.anthropic.com/claude/sonnet)                                 | Anthropic | -               | 1M       | Agent, Thinking, Images | Hidden by default; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                        |
| [Claude 4.5 Haiku](https://www.anthropic.com/claude/haiku)                                    | Anthropic | 200k            | -        | Thinking, Images        | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x                                                                                                                                                                                                                                         |
| [Claude 4.5 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | 200k            | 200k     | Agent, Thinking, Images | Hidden by default; Thinking variant counts as 2 requests in legacy pricing                                                                                                                                                                                                                                                                    |
| [Claude 4.5 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | 200k            | 1M       | Agent, Thinking, Images | Hidden by default; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                          |
| [Claude 4.6 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | 200k            | 1M       | Agent, Thinking, Images | The cost is about 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                       |
| [Claude 4.6 Opus (Fast mode)](https://www.anthropic.com/claude/opus)                          | Anthropic | 200k            | 1M       | Agent, Thinking, Images | Hidden by default; Limited research preview; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                |
| [Claude 4.6 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | 200k            | 1M       | Agent, Thinking, Images | The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                             |
| [Composer 1](https://cursor.com)                                                              | Cursor    | 200k            | -        | Agent, Images           | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Composer 1.5](https://cursor.com)                                                            | Cursor    | 200k            | -        | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 2.5 Flash](https://developers.googleblog.com/en/start-building-with-gemini-25-flash/) | Google    | 200k            | 1M       | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Flash](https://ai.google.dev/gemini-api/docs)                                       | Google    | 200k            | 1M       | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro](https://ai.google.dev/gemini-api/docs)                                         | Google    | 200k            | 1M       | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro Image Preview](https://ai.google.dev/gemini-api/docs)                           | Google    | 200k            | 1M       | Images                  | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (\~$0.134 per 1K/2K image, \~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| [Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs)                                       | Google    | 200k            | 1M       | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [GPT-5](https://openai.com/index/gpt-5/)                                                      | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high                                                                                                                                                                                                                                       |
| [GPT-5 Fast](https://openai.com/index/gpt-5/)                                                 | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast                                                                                                                                                                                                                         |
| [GPT-5 Mini](https://openai.com/index/gpt-5/)                                                 | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5-Codex](https://platform.openai.com/docs/models/gpt-5-codex)                            | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex Max](https://platform.openai.com/docs/models/gpt-5-codex)                      | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5.1 Codex Mini](https://platform.openai.com/docs/models/gpt-5-codex)                     | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex                                                                                                                                                                                                                                               |
| [GPT-5.2](https://openai.com/index/gpt-5/)                                                    | OpenAI    | 272k            | -        | Agent, Thinking, Images | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high                                                                                                                                                                                                                                                        |
| [GPT-5.2 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.3 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high                                                                                                                                                                                                                                                  |
| [Grok Code](https://docs.x.ai/docs/models#models-and-pricing)                                 | xAI       | 256k            | -        | Agent, Thinking         | -                                                                                                                                                                                                                                                                                                                                             |
| Kimi K2.5                                                                                     | Moonshot  | 262k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |

## Learn more

### Get started

Download, install, and start building with Cursor in minutes

### Changelog

Stay up to date with the latest features and improvements

### Concepts

Understand core concepts and features that power Cursor

### Downloads

Get Cursor for your computer

### Forum

For technical queries and to share experiences, visit our forum

### Support

For account and billing questions, email our support team


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/billing.md
# INDEX: 2/114
================================================================================

# Billing

### How do I access billing settings?

Access the billing portal through the [Dashboard](https://cursor.com/dashboard) by clicking "Billing" in your Dashboard. This opens a secure portal for all billing tasks.

### What are Cursor's billing cycles?

Billing cycles run monthly or annually, starting on your subscription date. Teams accounts are charged per seat with pro-rated billing for new members.

### How do seats work for Teams accounts?

Teams accounts charge per seat (one per Team member). When adding members mid-cycle, you're only charged for their remaining time. If a member has used any credits and is removed, their seat remains occupied until the end of the billing cycle - no pro-rated refunds are given. Team admins can manage seats through the dashboard.

### Can I switch between monthly and annual billing?

Yes! Here's how:

**Pro plan**

1. Go to the Cursor [dashboard](https://cursor.com/dashboard)
2. Click "Billing and Invoices" from the left sidebar to reach the billing page
3. Click "Manage subscription"
4. Click "Update subscription"
5. Select "Yearly" or "Monthly", then click "Continue"

**Teams plan**

1. Go to the Cursor [dashboard](https://cursor.com/dashboard)
2. Click "Billing and Invoices" from the left sidebar to reach the billing page
3. Click the "Upgrade Now" button to switch to yearly billing

You can only switch from monthly to yearly billing self-serve. To switch from
yearly to monthly, contact us at [hi@cursor.com](mailto:hi@cursor.com).

### Where can I find my invoices?

Find all billing history in the billing portal. View and download current and past invoices.

### Can I get invoices automatically emailed to me?

Invoices must be downloaded manually from the billing portal. We're developing automatic invoice emails. You'll be able to opt-in once available.

### How do I update my billing information?

Update payment method, company name, address, and tax information through the billing portal. We use Stripe for secure transactions. Changes only affect future invoices, we cannot modify historical invoices.

### How do I cancel my subscription?

Cancel your subscription through the Billing and Invoices page by clicking "Manage Subscription" the "Cancel subscription" button. Access continues until the end of your current billing period.

### I'm having other billing issues. How can I get help?

For billing questions not covered here, email [hi@cursor.com](mailto:hi@cursor.com) from the email linked to your account. Please include your account details and concerns.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/billing/spend-alerts.md
# INDEX: 3/114
================================================================================

# Spend Alerts

Configure email alerts to stay informed about your team's spending and usage.

Spend alerts only trigger based on on-demand spend (Enterprise accounts with pooled usage are [handled differently](https://cursor.com/docs/account/billing/spend-alerts.md#pooled-usage)). Included usage does not count towards spend thresholds.

## Email notifications

Cursor sends email notifications when monthly on-demand spend reaches configurable thresholds:

- Across the full team
- For any individual team member

## Configuring spend alerts

[Media](/docs-static/images/account/billing/spend-alerts/spend_alerts.mp4)

To set up email spend alerts:

1. Go to your [team dashboard](https://cursor.com/dashboard?tab=spending)
2. Click `Add Alert`
3. Select spend alert type (team- or member-level)
4. Set spend thresholds to receive alerts

## Alert behavior

When a threshold is reached, the relevant members receive an email notification with the threshold exceeded and current on-demand spend. Admins can choose whether member-level alerts go to admins, the member, or both.

Spend alerts do not stop Cursor usage.

## Pooled Usage

Enterprise customers with pooled usage can set member-level alerts based on total spend (not just on-demand spend).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/billing/spend-limits.md
# INDEX: 4/114
================================================================================

# Spend Limits

Set spending limits to control costs and prevent unexpected charges. Spend limits help you manage your team's usage and stay within budget.

Spend limits apply to on-demand usage. Included usage in your plan does not count towards spend limits. Enterprise accounts with pooled usage have different behavior.

## Spend limits overview

### Viewing spend limits

View your current spend limits in the [web dashboard](https://cursor.com/dashboard?tab=spending) under the Spending tab.

On-demand usage must be enabled to view and set spend limits.

### Updating spend limits

You can update spending limits at any time:

- **Increase limits**: Takes effect immediately
- **Decrease limits**: Takes effect immediately, but won't affect usage that has already occurred
- **Remove limits**: Set limit to "No Limit" to remove on-demand limits

### Spend limit behavior

When a user's spending limit is reached:

- AI features stop working for that specific user
- Other team members continue unaffected
- The user sees a notification indicating their personal limit was reached
- Usage resumes automatically at the start of the next billing cycle

## Individual plans

Customers with Pro, Pro+, and Ultra subscriptions can set monthly spend limits for on-demand usage.

## Team plans

Customers on Teams subscriptions can set team-level spend limits. Enterprise customers can set both team-level and member-level spend limits.

### Member spend limits (Enterprise-only)

Member spend limits are only available to Enterprise customers.

Set spending limits for each team member to control costs at the user level. There are multiple ways to set limits for different members; Cursor honors the most specific limit:

1. Member overrides (set in the [Members tab](https://cursor.com/dashboard?tab=members))
2. Group overrides (Enterprise-only) (set in the [Groups tab](https://cursor.com/dashboard?tab=members\&subtab=active-directory))
3. Team general spend limit (set in the [Spending tab](https://cursor.com/dashboard?tab=spending))

Enterprise admins can also set individual user limits programmatically using the [Admin API](https://cursor.com/docs/account/teams/admin-api.md#set-user-spend-limit).

#### Pooled Usage (Enterprise-only)

Member spend limits on Enterprise pooled usage accounts apply to total usage, not just on-demand usage.

### Team spend limits

Set a monthly spending limit for your entire team to control overall costs.

Once a team limit is reached, all members consuming on-demand usage will not be able to use AI features.

#### Dynamic Spend Limits

Dynamic Spend Limits is a toggleable setting that automatically adjust the Team spend limit based on team size. As the number of seats in your team grows or shrinks, the Team spend limit will change linearly.

## Related features

- [Spend Alerts](https://cursor.com/docs/account/billing/spend-alerts.md) - Configure email notifications for spending thresholds
- [Admin API](https://cursor.com/docs/account/teams/admin-api.md#set-user-spend-limit) - Programmatically manage user spend limits


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/enterprise/billing-groups.md
# INDEX: 5/114
================================================================================

# Billing Groups

[Billing groups](https://cursor.com/dashboard?tab=members\&subtab=billing-groups) allow Enterprise admins to understand and manage spend across groups of users. This functionality is useful for reporting, internal chargebacks, and budgeting.

## Billing group architecture

Admins can assign each member to a billing group. Members can only be in one billing group at a time. Members not actively assigned in any other billing group are placed in a reserved `Unassigned` group.

All usage is attributed to the user's group at the time it occurs. Historical data does not change when users move between groups, though it can be reassigned only when a group is deleted. In that case, all of its usage is moved to the Unassigned group.

## View billing groups

Enterprise admins can view billing groups in the web dashboard under the `Members & Groups` tab. This table shows each group, how it is configured, the number of members in it, and spend for the period.

![](/docs-static/images/account/enterprise/billing-groups/billing-groups-view.png)

## Create and add members to a billing group

Admins can create billing groups by clicking `Create Group`. After naming the group, there are four ways to assign members to that group:

1. **SCIM**: Sync the billing group with an existing [SCIM group](https://cursor.com/docs/account/teams/scim.md#scim).

2. **API**: Create groups and add members programmatically via the [Admin API](https://cursor.com/docs/account/teams/admin-api.md#billing-groups).

3. **CSV**: Upload a CSV with group names and email addresses of members.

4. **Manual**: Click `Add Members` and manually select `Unassigned` members to be added.

Billing groups synced with SCIM cannot be edited via CSV, API, or manual UI changes. All member assignment for SCIM-synced groups must be handled via SCIM.

## Move members between billing groups

Admins can move members from manual billing groups by clicking on the billing group and selecting `Move`.

- **SCIM**: When members are moved between SCIM groups in your identity provider, the billing group follows those changes automatically.
- **API**: Use the [add members](https://cursor.com/docs/account/teams/admin-api.md#add-members-to-group) and [remove members](https://cursor.com/docs/account/teams/admin-api.md#remove-members-from-group) endpoints to move members programmatically.

## Rename a billing group

Billing groups can be renamed by clicking the gear button on the main menu, or by clicking `Rename` on the page for that specific billing group.

- **API**: Use the [update group](https://cursor.com/docs/account/teams/admin-api.md#update-group) endpoint to rename groups programmatically.

## Delete a billing group

Billing groups can be deleted by clicking the gear button on the main menu, or by clicking `Delete` on the page for that specific billing group.

- **API**: Use the [delete group](https://cursor.com/docs/account/teams/admin-api.md#delete-group) endpoint to delete groups programmatically.

Deleting a billing group is a destructive operation; data cannot be recovered. All historic usage for deleted groups is assigned retroactively to the `Unassigned` group.

### Billing groups are available on the Enterprise plan

Contact our team to learn about spend management and reporting.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/enterprise/service-accounts.md
# INDEX: 6/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/account/pricing.md
# INDEX: 7/114
================================================================================

# Pricing

You can try Cursor for free or purchase an individual or team plan.

## Individual

All individual plans include:

- Unlimited tab completions
- Extended agent usage limits on all models
- Access to Bugbot
- Access to Cloud Agents

Each plan includes usage charged at model inference [API prices](https://cursor.com/docs/models.md#model-pricing):

- Pro includes $20 of API agent usage + generous Auto and Composer usage
- Pro Plus includes $70 of API agent usage + generous Auto and Composer usage
- Ultra includes $400 of API agent usage + generous Auto and Composer usage

We work hard to grant additional bonus capacity beyond the guaranteed included usage. Since different models have different API costs, your model selection affects token output and how quickly your included usage is consumed. You can view usage and token breakdowns on [your dashboard](https://cursor.com/dashboard?tab=usage). Limit notifications are routinely shown in the editor.

To understand how usage is calculated, see our guide on [tokens and pricing](https://cursor.com/learn/tokens-pricing.md).

### How much usage do I need?

For individual plans, here are typical usage levels based on our data:

- **Daily Tab users**: Always stay within $20
- **Limited Agent users**: Often stay within the included $20
- **Daily Agent users**: Typically $60–$100/mo total usage
- **Power users (multiple agents/automation)**: Often $200+/mo total usage

### What happens when I reach my limit?

When you exceed your included monthly usage, you'll be notified in the editor and can choose to:

- **Add on-demand usage**: Continue using Cursor at the same API rates with pay-as-you-go billing
- **Upgrade your plan**: Move to a higher tier for more included usage

On-demand usage is billed monthly at the same rates as your included usage. Requests are never downgraded in quality or speed.

## Teams

There are two teams plans: Teams ($40/user/mo) and Enterprise (Custom).

Team plans provide additional features like:

- Privacy Mode enforcement
- Admin Dashboard with usage stats
- Centralized team billing
- SAML/OIDC SSO

We recommend Teams for any customer that is happy self-serving. We recommend [Enterprise](https://cursor.com/contact-sales) for customers that need priority support, pooled usage, invoicing, SCIM, or advanced security controls.

Learn more about [Teams pricing](https://cursor.com/docs/account/teams/pricing.md).

## Auto

Enabling Auto allows Cursor to select the model best fit for the immediate task and with the highest reliability based on current demand. This feature can detect degraded output performance and automatically switch models to resolve it.

![Model picker](/docs-static/images/models/model-picker.png)

Auto consumes usage at the following API rates:

- **Input + Cache Write**: $1.25 per 1M tokens
- **Output**: $6.00 per 1M tokens
- **Cache Read**: $0.25 per 1M tokens

Both the editor and dashboard will show your usage, which includes Auto. If you prefer to select a model directly, usage is incurred at that model's list API price.

## Max Mode

[Max Mode](https://cursor.com/docs/context/max-mode.md) extends the context window to the maximum a model supports. It uses token-based pricing at the model's API rate plus a 20% upcharge, so it consumes usage faster than the default context window. Max Mode is designed for users who want the best possible experience, regardless of cost.

## Bugbot

Bugbot is a separate product from Cursor subscriptions and has its own pricing plan.

- **Pro** ($40/mo): Unlimited reviews on up to 200 PRs/month, unlimited access to Cursor Ask, integration with Cursor to fix bugs, and access to Bugbot Rules
- **Teams** ($40/user/mo): Unlimited code reviews across all PRs, unlimited access to Cursor Ask, pooled usage across your team, and advanced rules and settings
- **Enterprise** (Custom): Everything in Teams plus advanced analytics and reporting, priority support, and account management

Learn more about [Bugbot pricing](https://cursor.com/bugbot#pricing).

## Cloud Agent

Cloud Agents are charged at API pricing for the selected [model](https://cursor.com/docs/models.md). You'll be asked to set a spend limit for Cloud Agents when you first start using them.

Virtual Machine (VM) compute for cloud agents will be priced in the
future.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/analytics.md
# INDEX: 8/114
================================================================================

# Usage Analytics

Usage Analytics are available for Team and Enterprise customers.

The Cursor [Web Dashboard](https://cursor.com/dashboard?tab=analytics-v2) provides usage analytics so you can understand how your team is using Cursor.

## Data Access and Visibility

Team admins have access to data for themselves and all other users in the team. Team members without admin privileges can see data for themselves and in some cases (like the Usage Leaderboard) for select other users on the team.

Analytics data is collected only from users running client version 1.5 or higher.

### CSV Download

Each chart has a button on the bottom-right corner which allows for CSV download of visible data. Additionally, users can download data for all charts by clicking the download icon in the page header.

### API Access

See our [Admin API documentation](https://cursor.com/docs/account/teams/analytics-api.md) to access analytics data programmatically. Available only for Enterprise customers.

## Filtering Data

Dashboard users can filter usage shown for specific users, [active directory groups](https://cursor.com/docs/account/teams/scim.md#managing-users-and-groups), and dates via the header. Filtering supports up to 10 users and 90 continuous days of data.

Clicking on the gear icon in the header allows users to select timezone as well as whether weekends are shown.

## Tracking AI Code in Git Commits

Cursor keeps a log of the signature of every AI line (Tab or Agent) that is suggested to the user during their chat session.

These lines are stored and later compared to the signatures of each line in subsequent git commits that were written by the same author. Cursor will detect all the line changes (additions or deletions) written by the Cursor Agent or Tab, and attribute the line as being written by AI.

All the AI detection is done on device, and never leaves the user's computer. We store the line counts as metadata and make them available via API or in the Analytics Dashboard.

#### Known Limitations:

- Diff signatures may be invalidated if automated code formatting is modifying lines.

- AI Code Tracking has not been implemented for Background Agents, or the Cursor CLI yet.

- All code signatures are stored on-device. The git commit must be scored on the same machine as the AI code was authored.

## AI Output

### AI Share of Committed Code

![AI Share of Committed Code chart](/docs-static/images/account/team/analytics/ai-share-committed-code.png)

AI Share of Committed Code shows the lines of code changed in commits to your repositories, and what % of that code was generated by Cursor. Users can filter for production branch, which will use:

- The optional default branch set to the git repo

- Fallback to common default branch names such as: `main`, `master`, `production`, `prod`.

We use the following definitions:

- **Cursor AI**: Any line that can be attributed to Cursor Agent or Tab based on diff signatures.

- **Other**: Any line of code that can't be detected as being written by Cursor

### Agent Edits

![Agent Edits chart](/docs-static/images/account/team/analytics/agent-edits.png)

Agent Edits shows the amount of code edited by the Agent, and Cmd+K, and whether those changes were accepted by the user. Viewers can group the data by suggested / accepted or by file extension.

### Tab Completions

![Tab Completions chart](/docs-static/images/account/team/analytics/tab-completions.png)

Tab Completions shows the number of times Tab code has been suggested (and accepted) by users. The unit is Tab suggestions, regardless of lines of code changed in that suggestion.

You can access the number of lines of code suggested by Tab through the [Analytics API](https://cursor.com/docs/account/teams/analytics-api.md).

### Messages Sent

![Messages Sent chart](/docs-static/images/account/team/analytics/messages-sent.png)

Messages Sent shows the number of messages sent by users to Cursor. Users can filter this data by the mode (e.g., Agent, Ask, Cmd+K) or by models used.

## Active Users

![Active Users chart](/docs-static/images/account/team/analytics/active-users.png)

The Active Users chart shows the number of unique active Cursor users in your team across different products. A user is defined as active in a period if they use at least one AI feature (Tab, Agent, Background Agent, CLI). Bugbot users are synced to Github accounts (not Cursor) and therefore not included in the `All` active user rollup.

## Daily Usage

![Daily Usage chart](/docs-static/images/account/team/analytics/daily-usage.png)

The Daily Usage chart visualizes Cursor activity over the preceding 365 days.

Users can toggle to see this view by:

- **All**: shows lines of code edits suggested by AI in Cursor (Tab and Agent).

- **Tab:** shows the number of suggestions made by Tab.

- **Agent:** shows lines of code suggested by Agent.

- **DAU**: shows daily active users across all Cursor products.

Data collection for this chart starts in early September for customers on the 1.5+ desktop release.

## Usage Leaderboard

![Usage Leaderboard chart](/docs-static/images/account/team/analytics/usage-leaderboard.png)

The Usage Leaderboard shows top Cursor users across your team alongside their favorite model and select usage stats for the selected time period.

We provide the following metrics:

- **Chats**: number of messages sent by the user in the chat interface (Agent, Plan Mode, Ask Mode, etc).

- **Tab Completions**: number of Tab suggestions accepted by the user.

- **Agent Lines of Code:** Lines of code written by the Agent and accepted by the user.

The top ten users and any filtered users are always shown. All users in the team are able to view the leaderboard.

## Repository Insights

![Repository Insights chart](/docs-static/images/account/team/analytics/repository-insights.png)

Repository Insights allow you to see how Cursor is used across different repositories. We report on:

- **AI Lines of Code Committed**: Code written by Cursor (Tab and Agent) that was committed by a user.

- **Total Lines of Code Committed**: All code committed by users.

- **Code Committed by AI %**: The % of lines of code committed that were edited by Cursor (Tab and Agent).

Some commits will be associated with `Unknown` repository if the user makes commits to a local git repository that doesn't contain a remote origin, or a remote that couldn't be resolved by Cursor

## Conversation Insights

Conversation Insights is enabled by default for Enterprise customers. You can disable it via **Disable Conversation Insights** in team settings.

Cursor analyzes the code and context in each agent session to understand what kind of work is occurring. This makes Cursor the first self-aware software engineering platform, synthesizing the type of work happening across your team.

Teams no longer need high-toil, lossy analysis of tickets or low-response surveys to understand engineering work. Conversation Insights lets you deeply understand the type of work being done with Cursor.

![Conversation Insights dashboard showing categories and work type charts](/docs-static/images/account/team/analytics/conversation-insights-dashboard.png)

### Classification Dimensions

Conversation Insights classifies work across these dimensions:

- **Category**: Bug Fixing & Debugging, Code Refactoring, Code Explanation, Configuration, New Features, UI/Styling, Architecture, Data/Database, Documentation, DevOps/Deployment, Learning, Testing

- **Work Type**: Maintenance (KTLO), Bug Fixing, New Features

- **Complexity**: Distinguishes between the complexity of tasks teams assign to agents

- **Specificity**: Measures how specific the prompts developers use with agents are

Enterprise customers can extend these default categories or define their own across the organization or within specific teams.

### Compare

Compare allows you to select and compare usage across teams and individual developers within your organization. Use this to identify adoption patterns, find power users, and understand how different groups use Cursor.

### Privacy and Data Handling

All classification runs on-device. Default classifiers ensure no PII or sensitive data leaves the machine. The model outputs are validated against expected values. Any responses that don't match are discarded.

### Pricing

Conversation Insights is free during the preview period. Starting January 1st, 2026, customers will be charged for inference plus a Cursor token fee.

## Cloud Agent Usage

### Agents Created

![Agents Created chart](/docs-static/images/account/team/analytics/agents-created.png)

Agents Created shows Cloud Agent usage by the originating source. Each time a Cloud Agent starts up counts as one Agent.

### Pull Requests

![Pull Requests chart](/docs-static/images/account/team/analytics/pull-requests.png)

Pull Requests shows Pull Requests Opened and Merged that originate from Cloud Agents.

### Lines of Code

![Lines of Code chart](/docs-static/images/account/team/analytics/lines-of-code.png)

Lines of Code shows code written and merged by Cloud Agents.

## Cloud Agent Top Repositories

![Cloud Agent Top Repositories chart](/docs-static/images/account/team/analytics/cloud-agent-top-repositories.png)

Cloud Agent Top Repositories shows repositories by number of Pull Requests opened and merged.

## Top Cloud Agent Users

![Top Cloud Agent Users chart](/docs-static/images/account/team/analytics/top-cloud-agent-users.png)

Top Cloud Agent Users shows top users by number of Agents Created. Viewers can also view data by Pull Requests opened and merged.

## Client Versions

![Client Versions chart](/docs-static/images/account/team/analytics/client-versions.png)

Client Versions shows which versions of the Cursor editor your team is using. Each user's version is the Cursor version they last opened during that day.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/dashboard.md
# INDEX: 9/114
================================================================================

# Dashboard

The dashboard lets you access billing, set up usage-based pricing, and manage your Team.

## Overview

Get a quick summary of your team's activity, usage statistics, and recent changes. The overview page provides at-a-glance insights into your workspace.

![Team dashboard](/docs-static/images/account/team/dashboard.png)

## Settings

![Team settings](/docs-static/images/account/team/settings.png)

Configure team-wide preferences and security settings. The settings page includes:

## Teams & Enterprise Settings

### Privacy Settings

Control data sharing preferences for your team. Configure zero data retention policies with AI providers (OpenAI, Anthropic, Google Vertex AI, xAi Grok) and manage team-wide privacy enforcement.

### Usage-Based Pricing Settings

Enable usage-based pricing and set spending limits. Configure monthly team
spending limits. Control whether only admins can modify these settings.

### Bedrock IAM Role

Configure AWS Bedrock IAM roles for secure cloud integration.

### Single Sign-On (SSO)

Set up SSO authentication for enterprise teams to streamline user access and
improve security.

### Cursor Admin API Keys

Create and manage API keys for programmatic access to Cursor's admin features.

### Active Sessions

Monitor and manage active user sessions across your team.

### Invite Code Management

Create and manage invite codes for adding new team members.

### API Endpoints

Access Cursor's REST API endpoints for programmatic integration. All API endpoints are available on both Team and [Enterprise](https://cursor.com/docs/enterprise.md) plans, except for the [AI Code Tracking API](https://cursor.com/docs/account/teams/ai-code-tracking-api.md) which requires Enterprise plan.

## Enterprise-Only Settings

**Device-level enforcement:** In addition to dashboard settings, enterprises can enforce policies like allowed team IDs and allowed extensions on user devices through MDM. See [Identity and Access Management](https://cursor.com/docs/enterprise/identity-and-access-management.md#mdm-policies) and [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for details.

### Model Access Control

Control which AI models are available to team members. Set restrictions on
specific models or model tiers to manage costs and ensure appropriate usage
across your organization. Learn more in [Model and Integration Management](https://cursor.com/docs/enterprise/model-and-integration-management.md#model-access-control).

### Enhanced Spend Limits

Set individual spending limits for each team member. Configure member-level overrides, group-based limits via directory sync, or default per-member caps.

### Auto Run Configuration

Configure automatic command execution settings. Control which commands can be executed automatically and set security
policies for code execution.

### Repository Blocklist

Prevent access to specific repositories for security or compliance reasons. Learn more in [Model and Integration Management](https://cursor.com/docs/enterprise/model-and-integration-management.md#repository-blocklist).

### MCP Configuration

Configure Model Context Protocol settings.
Manage how models access and process context from your development
environment. Learn more in [Model and Integration Management](https://cursor.com/docs/enterprise/model-and-integration-management.md#mcp-server-trust-management).

### Cursor Ignore Configuration

Set up ignore patterns for files and directories. Control which files and directories are excluded from AI analysis and
suggestions. Learn more in [Security Guardrails](https://cursor.com/docs/enterprise/llm-safety-and-controls.md#cursorignore).

### .cursor Directory Protection

Protect the .cursor directory from unauthorized agent access. Ensure sensitive configuration and cache files remain secure. Learn more in [Security Guardrails](https://cursor.com/docs/enterprise/llm-safety-and-controls.md#cursor-directory-protection).

### AI Code Tracking API

Access detailed AI-generated code analytics for your team's repositories. Retrieve per-commit AI usage metrics and granular accepted AI changes through REST API endpoints. Requires Enterprise team plan. Learn more in [AI Code Tracking API](https://cursor.com/docs/account/teams/ai-code-tracking-api.md).

### Audit Log

View comprehensive, tamper-proof records of security events and administrative actions. Track authentication, team changes, permission updates, API key actions, settings modifications, and more. Requires an Enterprise subscription. Learn more in [Compliance and Monitoring](https://cursor.com/docs/enterprise/compliance-and-monitoring.md#audit-logs).

**SCIM** (System for Cross-domain Identity Management) provisioning is also
available for [Enterprise](https://cursor.com/docs/enterprise.md) plans. See our [SCIM
documentation](https://cursor.com/docs/account/teams/scim.md) for setup instructions.

## Members

Manage your team members, invite new users, and control access permissions. Set role-based permissions and monitor member activity.

![Team members](/docs-static/images/account/team/members.png)

## Audit Log

Track security events, administrative actions, and team changes with comprehensive audit logs. View detailed records of who did what, when, and from where. Audit logs capture authentication events, membership changes, permission updates, API key actions, settings modifications, and more.

![Audit Log](/docs-static/images/account/team/audit-log.png)

**Audit Log** is available exclusively on [Enterprise](https://cursor.com/docs/enterprise.md) plans and can only be viewed by admins.

## Integrations

![Integrations](/docs-static/images/account/team/integrations.png)

Connect Cursor with your favorite tools and services. Configure integrations with version control systems, project management tools, and other developer services.

## Cloud Agents

![Cloud agents](/docs-static/images/account/team/integrations.png)

Monitor and manage cloud agents running in your workspace. View agent status, logs, and resource usage.

## Bugbot

Access automated bug detection and fixing capabilities. Bugbot helps identify and resolve common issues in your codebase automatically.

![Bugbot code review](/docs-static/images/account/team/bugbot.png)

## Active Directory Management

For enterprise teams, manage user authentication and access through Active Directory integration. Configure SSO and user provisioning.

## Usage

Track detailed usage metrics including AI requests, model usage, and resource consumption. Monitor usage across team members and projects.

![Usage](/docs-static/images/account/team/usage.png)

## Billing & Invoices

Manage your subscription, update payment methods, and access billing history. Download invoices and manage usage-based pricing settings.

![Billing](/docs-static/images/account/team/billing.png)


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/members.md
# INDEX: 10/114
================================================================================

# Members & Roles

Cursor teams have three roles:

## Roles

**Members** are the default role with access to Cursor's Pro features.

- Full access to Cursor's Pro features
- No access to billing settings or admin dashboard
- Can see their own usage and remaining usage-based budget

**Admins** control team management and security settings.

- Full access to Pro features
- Add/remove members, modify roles, setup SSO
- Configure usage-based pricing and spending limits
- Access to team analytics

**Unpaid Admins** manage teams without using a paid seat - ideal for IT or finance staff who don't need Cursor access.

- Not billable, no Pro features
- Same administrative capabilities as Admins

Unpaid Admins require at least one paid user on the team.

## Role Comparison

| Capability             |                                       Member                                      |                                       Admin                                       |                                    Unpaid Admin                                   |
| ---------------------- | :-------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------: |
| Use Cursor features    |                                         ✓                                         |                                         ✓                                         |                                                                                   |
| Invite members         |                                         ✓                                         |                                         ✓                                         |                                         ✓                                         |
| Remove members         |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Change user role       |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Admin dashboard        |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Configure SSO/Security |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Manage Billing         |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| View Analytics         |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Manage Access          |                                                                                   |                                         ✓                                         |                                         ✓                                         |
| Set usage controls     | ✓ [\*](https://cursor.com/docs/account/billing/spend-limits.md#team-level-limits) | ✓ [\*](https://cursor.com/docs/account/billing/spend-limits.md#team-level-limits) | ✓ [\*](https://cursor.com/docs/account/billing/spend-limits.md#team-level-limits) |
| Requires paid seat     |                                         ✓                                         |                                         ✓                                         |                                                                                   |

## Managing members

### Add member

Add members in several ways:

1. **Email invitation**

   - Click `Invite Members`
   - Enter email addresses
   - Users receive email invites

2. **Invite link**

   - Click `Invite Members`
   - Copy `Invite Link`
   - Share with team members

3. **SSO**
   - Configure SSO in [admin dashboard](https://cursor.com/docs/account/teams/sso.md)
   - Users auto-join when logging in via SSO email

4. **Domain matching**
   - Teammates with a verified, matching email domain can join your team without an invite
   - Enable this in [team settings](https://cursor.com/dashboard?tab=settings#domain-join)

Invite links have a long expiration date. Anyone with the link can join.
Revoke them regularly, or use [SSO](https://cursor.com/docs/account/teams/sso.md) or [domain restrictions](https://cursor.com/docs/account/teams/members.md#domain-settings) to control access.

### Remove member

Admins can remove members anytime via context menu → "Remove".

**Billing:**

- If a member has used any credits, their seat remains occupied until the end of the billing cycle
- Billing is automatically adjusted with pro-rated credit for removed members applied to the next invoice

**Data deletion:**

- When a user is removed from the team, their data (including Memories and Cloud Agent data) is permanently deleted
- When an entire team is deleted, all associated data is permanently deleted
- There must be at least one Admin and one paid member on the team at all times

### Change role

Admins can change roles for other members by clicking the context menu and then use the "Change role" option.

There must be at least one Admin, and one paid member on the team at all times.

## Domain settings

Admins can configure two domain-based controls in [team settings](https://cursor.com/dashboard?tab=settings#domain-join). Both require at least one verified domain and are available on Team and Enterprise plans for teams not using SCIM provisioning.

### Domain matching

When enabled, anyone with a verified, matching email domain can join your team directly from the dashboard, no invite needed. This is useful for letting teammates self-serve without admins manually sending invitations.

### Restrict invites to verified domains

When enabled, team members can only invite users whose email addresses match a verified domain. Invitations to email addresses outside your verified domains are blocked.

This prevents accidental or unauthorized additions and gives admins tighter control over who joins the team.

These settings are for teams that don't use SCIM provisioning. If your team uses SCIM, member management is handled through your identity provider.

## Security & SSO

SAML 2.0 Single Sign-On (SSO) is available on Team plans. Key features include:

- Configure SSO connections ([learn more](https://cursor.com/docs/account/teams/sso.md))
- Set up domain verification
- Automatic user enrollment
- SSO enforcement options
- Identity provider integration (Okta, etc)

Domain verification is required to enable SSO.

![](/docs-static/images/account/sso-settings.png)

## Usage Controls

Access usage settings to:

- Enable usage-based pricing
- Enable for premium models
- Set admin-only modifications
- Set monthly spending limits
- Monitor team-wide usage

![](/docs-static/images/account/usage-based-pricing.png)

## Billing

When adding team members:

- Each member or admin adds a billable seat (see [pricing](https://cursor.com/pricing))
- New members are charged pro-rata for their remaining time in the billing period
- Unpaid admin seats aren't counted

Mid-month additions charge only for days used. When removing members who have used credits, their seat remains occupied until the end of the billing cycle - no pro-rated refunds are given.

Role changes (e.g., Admin to Unpaid Admin) adjust billing from the change date. Choose monthly or yearly billing.

Monthly/yearly renewal occurs on your original signup date, regardless of member changes.

### Switch to Yearly billing

Save **20%** by switching from monthly to yearly:

1. Go to [Dashboard](https://cursor.com/dashboard)
2. In account section, click "Advanced" then "Upgrade to yearly billing"

You can only switch from monthly to yearly via dashboard. To switch from
yearly to monthly, contact [hi@cursor.com](mailto:hi@cursor.com).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/pricing.md
# INDEX: 11/114
================================================================================

# Team Pricing

There are two teams plans: Teams ($40/user/mo) and Enterprise (Custom).

Team plans provide additional features like:

- Privacy Mode enforcement
- Admin Dashboard with usage stats (also accessible via [Admin API](https://cursor.com/docs/account/teams/admin-api.md))
- Centralized team billing
- SAML/OIDC SSO

We recommend Teams for any customer that is happy self-serving. We recommend [Enterprise](https://cursor.com/docs/enterprise.md) for customers that need priority support, pooled usage, invoicing, SCIM, or advanced security controls. [Contact sales](https://cursor.com/contact-sales) to get started.

## How pricing works

Teams pricing is usage-based. Each seat includes monthly usage, and you can continue using Cursor beyond that with on-demand usage.

### Included usage

Each team seat ($40/mo) comes with **$20/mo of included usage**. This usage:

- Is allocated per user (each user gets their own $20)
- Does not transfer between team members
- Resets at the start of each billing cycle
- Covers all agent requests at public list API prices + Cursor Token Fee

Our [Enterprise plan](https://cursor.com/docs/enterprise.md) offers pooled usage shared between all users in a team. [Get in touch](https://cursor.com/contact-sales) with our team to learn more.

### On-demand usage

On-demand usage allows you to continue using models after your included amount is consumed, billed in arrears.

When exceeding the $20 of included usage, team members automatically continue with **on-demand usage**:

- Billed monthly at the same rates (API prices + Cursor Token Fee)
- No interruption in service or quality
- Tracked per user in your admin dashboard (see [spending data API](https://cursor.com/docs/account/teams/admin-api.md#get-spending-data))
- Can be controlled with spending limits

On-demand usage is enabled by default for the Teams plan.

### Cursor Token Fee

All non-Auto agent requests include a **$0.25 per million tokens** fee. This covers:

- [Semantic search](https://cursor.com/docs/context/semantic-search.md)
- Custom model execution (Tab, Apply, etc.)
- Infrastructure and processing costs

This fee applies to all tokens: input, output, and cached tokens. This applies to [BYOK](https://cursor.com/docs/settings/api-keys.md) as well.

## Active seats

Cursor bills per active user, not pre-allocated seats. Add or remove users anytime and billing will adjust immediately.

Refunds appear as account credit on your next invoice. Your renewal date stays the same.

## Spending controls

Teams can configure monthly team-wide spending limits. You can manage these limits through the dashboard. Per-member spend limits are available on [Enterprise](https://cursor.com/docs/enterprise.md) plans.

Contact `enterprise@cursor.com` for volume discounts on larger teams.

## Model Pricing

All prices are per million tokens. Teams are charged at public list API prices + [Cursor Token Fee](https://cursor.com/docs/account/teams/pricing.md#cursor-token-fee).

| Model                                                                                         | Provider  | Input | Cache write | Cache read | Output | Notes                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------- | --------- | ----- | ----------- | ---------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Claude 4 Sonnet](https://www.anthropic.com/claude/sonnet)                                    | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Claude 4 Sonnet 1M](https://www.anthropic.com/claude/sonnet)                                 | Anthropic | $6    | $7.5        | $0.6       | $22.5  | Hidden by default; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                        |
| [Claude 4.5 Haiku](https://www.anthropic.com/claude/haiku)                                    | Anthropic | $1    | $1.25       | $0.1       | $5     | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x                                                                                                                                                                                                                                         |
| [Claude 4.5 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | Hidden by default; Thinking variant counts as 2 requests in legacy pricing                                                                                                                                                                                                                                                                    |
| [Claude 4.5 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                          |
| [Claude 4.6 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | The cost is about 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                       |
| [Claude 4.6 Opus (Fast mode)](https://www.anthropic.com/claude/opus)                          | Anthropic | $30   | $37.5       | $3         | $150   | Hidden by default; Limited research preview; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                |
| [Claude 4.6 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                             |
| [Composer 1](https://cursor.com)                                                              | Cursor    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Composer 1.5](https://cursor.com)                                                            | Cursor    | $3.5  | -           | $0.35      | $17.5  | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 2.5 Flash](https://developers.googleblog.com/en/start-building-with-gemini-25-flash/) | Google    | $0.3  | -           | $0.03      | $2.5   | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Flash](https://ai.google.dev/gemini-api/docs)                                       | Google    | $0.5  | -           | $0.05      | $3     | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro](https://ai.google.dev/gemini-api/docs)                                         | Google    | $2    | -           | $0.2       | $12    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro Image Preview](https://ai.google.dev/gemini-api/docs)                           | Google    | $2    | -           | $0.2       | $12    | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (\~$0.134 per 1K/2K image, \~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| [Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs)                                       | Google    | $2    | -           | $0.2       | $12    | -                                                                                                                                                                                                                                                                                                                                             |
| [GPT-5](https://openai.com/index/gpt-5/)                                                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high                                                                                                                                                                                                                                       |
| [GPT-5 Fast](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $2.5  | -           | $0.25      | $20    | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast                                                                                                                                                                                                                         |
| [GPT-5 Mini](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5-Codex](https://platform.openai.com/docs/models/gpt-5-codex)                            | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex Max](https://platform.openai.com/docs/models/gpt-5-codex)                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5.1 Codex Mini](https://platform.openai.com/docs/models/gpt-5-codex)                     | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex                                                                                                                                                                                                                                               |
| [GPT-5.2](https://openai.com/index/gpt-5/)                                                    | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high                                                                                                                                                                                                                                                        |
| [GPT-5.2 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.3 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high                                                                                                                                                                                                                                                  |
| [Grok Code](https://docs.x.ai/docs/models#models-and-pricing)                                 | xAI       | $0.2  | -           | $0.02      | $1.5   | -                                                                                                                                                                                                                                                                                                                                             |
| Kimi K2.5                                                                                     | Moonshot  | $0.6  | -           | $0.1       | $3     | Hidden by default                                                                                                                                                                                                                                                                                                                             |


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/scim.md
# INDEX: 12/114
================================================================================

# SCIM

## Overview

SCIM 2.0 provisioning automatically manages your team members and directory groups through your identity provider. Available on Enterprise plans with SSO enabled, [contact sales](https://cursor.com/contact-sales?source=docs-scim) to get access.

## Prerequisites

- Cursor Enterprise plan
- SSO must be configured first - **SCIM requires an active SSO connection**
- Admin access to your identity provider (Okta, Azure AD, etc.)
- Admin access to your Cursor organization

## How it works

### User provisioning

Users are automatically added to Cursor when assigned to the SCIM application in your identity provider. When unassigned, they're removed. Changes sync in real-time.

### Directory groups

Directory groups and their membership sync from your identity provider. Group and user management must be done through your identity provider - Cursor displays this information as read-only.

### Spend management

Set different per-user spend limits for each directory group. Directory group limits take precedence over team-level limits. Users in multiple groups receive the highest applicable spend limit.

## Setup

### Ensure SSO is configured

SCIM requires SSO to be set up first. If you haven't configured SSO yet,
follow the [SSO setup guide](https://cursor.com/docs/account/teams/sso.md) before proceeding.

### Access Active Directory Management

Navigate to
[cursor.com/dashboard?tab=members\&subtab=active-directory](https://www.cursor.com/dashboard?tab=members\&subtab=active-directory)
with an admin account, or go to your dashboard settings and select the "Members
& Groups" tab followed by the "Directory Groups" subtab.

### Start SCIM setup

Once SSO is verified, you'll see a link for step-by-step SCIM setup. Click
this to begin the configuration wizard.

### Configure SCIM in your identity provider

In your identity provider: - Create or configure your SCIM application - Use
the SCIM endpoint and token provided by Cursor - Enable user and push group
provisioning - Test the connection

### Configure spend limits (optional)

Back in Cursor's Active Directory Management page: - View your synchronized
directory groups - Set per-user spend limits for specific groups as needed -
Review which limits apply to users in multiple groups

### Identity provider setup

For provider-specific setup instructions:

### Identity Provider Guides

Setup instructions for Okta, Azure AD, Google Workspace, and more.

## Managing users and groups

All user and group management must be done through your identity provider.
Changes made in your identity provider will automatically sync to Cursor, but
you cannot modify users or groups directly in Cursor.

### User management

- Add users by assigning them to your SCIM application in your identity provider
- Remove users by unassigning them from the SCIM application
- User profile changes (name, email) sync automatically from your identity provider

### Group management

- Directory groups are automatically synced from your identity provider
- Group membership changes are reflected in real-time
- Use groups to organize users and set different spend limits

### Spend limits

- Set different per-user limits for each directory group
- Users inherit the highest spend limit from their groups
- Group limits override the default team-wide per-user limit

## FAQ

### Why isn't SCIM management showing up in my dashboard?

Ensure SSO is properly configured and working before setting up SCIM. SCIM requires an active SSO connection to function.

### Why aren't users syncing?

Verify that users are assigned to the SCIM application in your identity provider. Users must be explicitly assigned to appear in Cursor.

### Why aren't groups appearing?

Check that push group provisioning is enabled in your identity provider's SCIM settings. Group sync must be configured separately from user sync.

### Why aren't spend limits applying?

Confirm users are properly assigned to the expected groups in your identity provider. Group membership determines which spend limits apply.

### Can I manage SCIM users and groups directly in Cursor?

No. All user and group management must be done through your identity provider. Cursor displays this information as read-only.

### How quickly do changes sync?

Changes made in your identity provider sync to Cursor in real-time. There may be a brief delay for large bulk operations.

### Can I sync user roles from my IdP?

No. Currently, the SCIM integration doesn't support role mapping and all users are provisioned as Members. Any role updates need to be done in the Cursor dashboard.

### Why are there users on my Members dashboard that aren't in the provisioned IdP groups?

When SCIM is set up, existing users are not automatically removed from Cursor. You can either remove them manually, or sync them with SCIM once and deprovision them from your IdP to have them removed from Cursor.

### Why don't the users from my synced groups match the users on the Cursor Members dashboard?

Once a user account is provisioned, they won't appear on the Cursor Members Dashboard until they sign in for the first time.

### SCIM is available on the Enterprise plan

Contact our team to request access.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/setup.md
# INDEX: 13/114
================================================================================

# Get Started

## Cursor for Teams

Cursor works for individuals and teams. The Teams plan provides tools for organizations: SSO, team management, access controls, and usage analytics.

## Creating a Team

Create a team by following these steps:

### Set up Teams plan

To create a Team, follow these steps:

1. **For new users**: Visit [cursor.com/team/new-team](https://cursor.com/team/new-team) to create a new account and team
2. **For existing users**: Go to your [dashboard](https://cursor.com/docs/account/teams/dashboard.md) and click "Upgrade to Teams"

### Enter Team details

Select a Team name and billing cycle

![Create new team](/docs-static/images/account/team/new-team.png)

### Invite members

Invite team members. User counts are prorated - you only pay for the time users are members.

You can opt in to domain matching so teammates with verified, matching email domains can join your team without an invite. Configure it in [team settings](https://cursor.com/dashboard?tab=settings#domain-join).

![Invite members](/docs-static/images/account/invite-members.png)

### Enable SSO (optional)

Enable [SSO](https://cursor.com/docs/account/teams/sso.md) for security and automated onboarding.

![SSO settings](/docs-static/images/account/sso-settings.png)

## FAQ

### My team uses ZScalar / a proxy / a VPN, will Cursor work?

Cursor uses HTTP/2 by default. Some proxies and VPNs block this.

Go to `Cursor Settings` > `Network`, then set `HTTP Compatibility Mode` to `HTTP/1.1`.

### How can I purchase licenses for my company?

Cursor bills per active user, not seats. Add or remove users anytime - new members are charged pro-rata for their remaining time. If a removed user has used any credits, their seat remains occupied until the end of the billing cycle.

Your renewal date stays the same.

### How can I set up a team when I'm not using Cursor?

Set yourself as an [Unpaid Admin](https://cursor.com/docs/account/teams/members.md) to manage without a license.

Teams need at least one paid member. You can set up, invite a member, then change your role before billing.

### How can I add Cursor to my company's MDM?

Download links for all platforms are available at [cursor.com/downloads](https://cursor.com/downloads).

MDM instructions:

- [Omnissa Workspace ONE](https://docs.omnissa.com/bundle/MobileApplicationManagementVSaaS/page/DeployInternalApplications.html) (formerly VMware)
- [Microsoft Intune (Windows)](https://learn.microsoft.com/en-us/mem/intune-service/apps/apps-win32-app-management)
- [Microsoft Intune (Mac)](https://learn.microsoft.com/en-us/mem/intune-service/apps/lob-apps-macos-dmg)
- [Kandji MDM](https://support.kandji.io/kb/custom-apps-overview)

### Can I be a member of more than one team?

No, a Cursor account cannot be a member of more than one team at a time. If you need to switch teams, you'll need to leave your current team first before joining another.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/teams/sso.md
# INDEX: 14/114
================================================================================

# SSO

## Overview

SAML 2.0 SSO is available at no additional cost on Teams and Enterprise plans. Use your existing identity provider (IdP) to authenticate team members without separate Cursor accounts.

![](/docs-static/images/account/sso-settings.png)

## Prerequisites

- Cursor Team plan
- Admin access to your identity provider (e.g., Okta)
- Admin access to your Cursor organization

## Configuration Steps

### Sign in to your Cursor account

Navigate to [cursor.com/dashboard?tab=settings](https://www.cursor.com/dashboard?tab=settings) with an admin account.

### Locate the SSO configuration

Find the "Single Sign-On (SSO)" section and expand it.

### Begin the setup process

Click the "SSO Provider Connection settings" button to start SSO setup and follow the wizard.

### Configure your identity provider

In your identity provider (e.g., Okta):

- Create new SAML application
- Configure SAML settings using Cursor's information
- Set up Just-in-Time (JIT) provisioning

### Verify domain

Verify the domain of your users in Cursor by clicking the "Domain verification settings" button.

### Identity Provider Setup Guides

For provider-specific setup instructions:

### Identity Provider Guides

Setup instructions for Okta, Azure AD, Google Workspace, and more.

## Additional Settings

- Manage SSO enforcement through admin dashboard
- New users auto-enroll when signing in through SSO
- Handle user management through your identity provider

## Multiple domains

To handle multiple domains in your organization:

1. **Verify each domain separately** in Cursor through the domain verification settings
2. **Configure each domain** in your identity provider
3. Each domain needs to go through the verification process independently

## Troubleshooting

If issues occur:

- Verify domain is verified in Cursor
- Ensure SAML attributes are properly mapped
- Check SSO is enabled in admin dashboard
- Match first and last names between identity provider and Cursor
- Check provider-specific guides above
- Contact [hi@cursor.com](mailto:hi@cursor.com) if issues persist


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/account/update-access.md
# INDEX: 15/114
================================================================================

# Update Access

Cursor has three update channels.

### Default

The default update channel with tested releases.

- Stable releases
- Bug fixes from pre-release testing
- Default for all users
- Only option for team users

Team and Enterprise accounts use Default mode.

### Early Access

Pre-release versions with new features.

Early Access builds may have bugs or stability issues.

- Access to features in development
- May contain bugs
- Not available for team accounts

### Nightly

Bleeding-edge builds with the latest experimental features.

Nightly builds are the least stable and may have bugs.

- First access to experimental features
- Updated frequently
- May contain breaking changes
- Not available for team accounts

## Change update channel

1. **Open settings**: Press Cmd+Shift+J
2. **Go to Beta**: Select Beta in the sidebar
3. **Select channel**: Choose Default, Early Access, or Nightly

![Early access settings](/docs-static/images/account/early-access.png)

Report Early Access issues on the [Forum](https://forum.cursor.com).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/browser.md
# INDEX: 16/114
================================================================================

# Browser

Agent can control a web browser to test applications, visually edit layouts and styles, audit accessibility, convert designs into code, and more. With full access to console logs and network traffic, Agent can debug issues and automate comprehensive testing workflows.

![Agent can control a web browser to test applications, audit accessibility, convert designs into code, and more.](/docs-static/images/agent/browser.jpg)

For enterprise customers, browser controls are governed by MCP allowlist or denylist.

## Native integration

Agent displays browser actions like screenshots and actions in the chat, as well as the browser window itself either in a separate window or an inline pane.

We've optimized the browser tools to be more efficient and reduce token usage, as well as:

- **Efficient log handling**: Browser logs are written to files that Agent can grep and selectively read. Instead of summarizing verbose output after every action, Agent reads only the relevant lines it needs. This preserves full context while minimizing token usage.
- **Visual feedback with images**: Screenshots are integrated directly with the file reading tool, so Agent actually sees the browser state as images rather than relying on text descriptions. This enables better understanding of visual layouts and UI elements.
- **Smart prompting**: Agent receives additional context about browser logs, including total line counts and preview snippets, helping it make informed decisions about what to inspect.
- **Development server awareness**: Agent is prompted to detect running development servers and use the correct ports instead of starting duplicate servers or guessing port numbers.

You can use Browser without installing or configuring any external tools.

## Browser capabilities

Agent has access to the following browser tools:

### Navigate

Visit URLs and browse web pages. Agent can navigate anywhere on the web by visiting URLs, following links, going back and forward in history, and refreshing pages.

### Click

Interact with buttons, links, and form elements. Agent can identify and interact with page elements, performing click, double-click, right-click, and hover actions on any visible element.

### Type

Enter text into input fields and forms. Agent can fill out forms, submit data, and interact with form fields, search boxes, and text areas.

### Scroll

Navigate through long pages and content. Agent can scroll to reveal additional content, find specific elements, and explore lengthy documents.

### Screenshot

Capture visual representations of web pages. Screenshots help Agent understand page layout, verify visual elements, and provide you with confirmation of browser actions.

### Console Output

Read browser console messages, errors, and logs. Agent can monitor JavaScript errors, debugging output, and network warnings to troubleshoot issues and verify page behavior.

### Network Traffic

Monitor HTTP requests and responses made by the page. Agent can track API calls, analyze request payloads, check response status codes, and diagnose network-related issues. This is currently only available in the Agent panel, coming soon to the layout.

## Design sidebar

The browser includes a design sidebar for modifying your site directly in Cursor. Design and code simultaneously with real-time visual adjustments.

![Browser design sidebar showing layout controls, positioning, and CSS properties for a selected element.](/docs-static/images/agent/browser-design-sidebar.png)

### Visual editing capabilities

The sidebar provides powerful visual editing controls:

- **Position and layout**: Move and rearrange elements on the page. Change flex direction, alignment, and grid layouts.
- **Dimensions**: Adjust width, height, padding, and margins with precise pixel values.
- **Colors**: Update colors from your design system or add new gradients. Access color tokens through a visual picker.
- **Appearance**: Experiment with shadows, opacity, and border radius using visual sliders.
- **Theme testing**: Test your designs across light and dark themes instantly.

### Applying changes

When your visual adjustments match your vision, click the apply button to trigger an agent that updates your codebase. The agent translates your visual changes into the appropriate code modifications.

You can also select multiple elements across your site and describe changes in text. Agents kick off in parallel, and your changes appear live on the page after hot-reload.

## Session persistence

Browser state persists between Agent sessions based on your workspace. This means:

- **Cookies**: Authentication cookies and session data remain available across browser sessions
- **Local Storage**: Data stored in `localStorage` and `sessionStorage` persists
- **IndexedDB**: Database content is retained between sessions

The browser context is isolated per workspace, ensuring that different projects maintain separate storage and cookie states.

## Use cases

### Web development workflow

Browser integrates into web development workflows alongside tools like Figma and Linear. See the [Web Development cookbook](https://cursor.com/docs/cookbook/web-development.md) for a complete guide on using Browser with design systems, project management tools, and component libraries.

### Accessibility improvements

Agent can audit and improve web accessibility to meet WCAG compliance standards.

@browser Check color contrast ratios, verify semantic HTML and ARIA labels, test keyboard navigation, and identify missing alt text

### Automated testing

Agent can execute comprehensive test suites and capture screenshots for visual regression testing.

@browser Fill out forms with test data, click through workflows, test responsive designs, validate error messages, and monitor console for JavaScript errors

### Design to code

Agent can convert designs into working code with responsive layouts.

@browser Analyze this design mockup, extract colors and typography, and generate pixel-perfect HTML and CSS code

### Adjusting UI design from screenshots

Agent can refine existing interfaces by identifying visual discrepancies and updating component styles.

@browser Compare current UI against this design screenshot and adjust spacing, colors, and typography to match

## Security

Browser runs as a secure web view and is controlled using an MCP server running as an extension. Multiple layers protect you from unauthorized access and malicious actions.
Cursor's Browser integrations have also been reviewed by multiple external security auditors.

### Authentication and isolation

The browser implements several security measures:

- **Token authentication**: Agent layout generates a random authentication token before each browser session starts
- **Tab isolation**: Each browser tab receives a unique random ID to prevent cross-tab interference
- **Session-based security**: Tokens regenerate for each new browser session

### Tool approval

Browser tools require your approval by default. Review each action before Agent executes it. This prevents unexpected navigation, data submission, or script execution.

You can configure approval settings in Agent Settings. Available modes:

| Mode                     | Description                                                                 |
| :----------------------- | :-------------------------------------------------------------------------- |
| **Manual approval**      | Review and approve each browser action individually (recommended)           |
| **Allow-listed actions** | Actions matching your allow list run automatically; others require approval |
| **Auto-run**             | All browser actions execute immediately without approval (use with caution) |

### Allow and block lists

Browser tools integrate with Cursor's [security guardrails](https://cursor.com/docs/agent/security.md). Configure which browser actions run automatically:

- **Allow list**: Specify trusted actions that skip approval prompts
- **Block list**: Define actions that should always be blocked
- Access settings through: `Cursor Settings` → `Chat` → `Auto-Run`

The allow/block list system provides best-effort protection. AI behavior can be unpredictable due to prompt injection and other issues. Review auto-approved actions regularly.

Never use auto-run mode with untrusted code or unfamiliar websites. Agent could execute malicious scripts or submit sensitive data without your knowledge.

### Browser context

The browser opens as a pane within Cursor, giving Agent full control through MCP tools.

## Recommended models

We recommend using Sonnet 4.5, GPT-5, and Auto for the best performance.

## Enterprise usage

For enterprise customers, browser functionality is managed through toggling availability under MCP controls. Admins have granular controls over each MCP server, as well as over browser access.

### Enabling browser for enterprise

To enable browser capabilities for your enterprise team:

1. Navigate to your [Settings Dashboard](https://cursor.com/dashboard?tab=settings)
2. Go to **MCP Configuration**
3. Toggle "browser features"

Once configured, users in your organization will have access to browser tools based on your MCP allowlist or denylist settings.

### Origin allowlist

Enterprise administrators can configure an origin allowlist that restricts which sites the agent can automatically navigate to and where MCP tools can run. This provides granular control over browser access for security and compliance.

The Browser Origin Allowlist feature must be enabled for your organization before it appears in your dashboard. Contact your Cursor account team to request access.

#### Configuration

To configure the origin allowlist:

1. Navigate to your [Admin Dashboard](https://cursor.com/dashboard?tab=settings)
2. Go to **MCP Configuration**
3. Ensure **Enable Browser Automation Features (v2.0+)** is enabled
4. Under **Browser Origin Allowlist (v2.1+)**, click **Add Origin**
5. Enter the origins you want to allow (e.g., `*`, `http://localhost:3000`, `https://internal.example.com`)

Leave the allowlist empty to allow all origins. Each origin should be added separately using the Add Origin button.

![MCP Configuration showing Browser Origin Allowlist settings with Add Origin button](/docs-static/images/agent/browser-origin-allowlist.png)

#### Behavior

When an origin allowlist is configured:

- **Automatic navigation**: The agent can only use the `browser_navigate` tool to visit URLs matching origins in the allowlist
- **MCP tool execution**: MCP tools can only run on origins that are in the allowlist
- **Manual navigation**: Users can still manually navigate the browser to any URL, including origins outside the allowlist (useful for viewing documentation or inspecting external sites)
- **Tool restrictions**: Once the browser is on an origin not in the allowlist, browser tools (click, type, navigate) are blocked, even if the user navigated there manually

#### Edge cases

The origin allowlist provides best-effort protection. Be aware of these behaviors:

- **Link navigation**: If the agent clicks a link on an allowed domain that navigates to a non-allowed origin, the navigation will succeed
- **Redirects**: If the agent navigates to an allowed origin that subsequently redirects to a non-allowed origin, the redirect will be permitted
- **JavaScript navigation**: Client-side navigation (via `window.location` or similar) from an allowed origin to a non-allowed origin will succeed

The origin allowlist restricts automatic agent navigation but cannot prevent all navigation paths. Review your allowlist regularly and consider the security implications of allowing access to domains that may redirect or link to external sites.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/hooks.md
# INDEX: 17/114
================================================================================

# Hooks

Hooks let you observe, control, and extend the agent loop using custom scripts. Hooks are spawned processes that communicate over stdio using JSON in both directions. They run before or after defined stages of the agent loop and can observe, block, or modify behavior.

[Media](/docs-static/images/agent/hooks.mp4)

With hooks, you can:

- Run formatters after edits
- Add analytics for events
- Scan for PII or secrets
- Gate risky operations (e.g., SQL writes)
- Control subagent (Task tool) execution
- Inject context at session start

Looking for ready-to-use integrations? See [Partner Integrations](https://cursor.com/docs/agent/hooks.md#partner-integrations) for security, governance, and secrets management solutions from our ecosystem partners.

Cursor supports loading hooks from third-party tools like Claude Code. See [Third Party Hooks](https://cursor.com/docs/agent/third-party-hooks.md) for details on compatibility and configuration.

## Agent and Tab Support

Hooks work with both **Cursor Agent** (Cmd+K/Agent Chat) and **Cursor Tab** (inline completions), but they use different hook events:

**Agent (Cmd+K/Agent Chat)** uses the standard hooks:

- `sessionStart` / `sessionEnd` - Session lifecycle management
- `preToolUse` / `postToolUse` / `postToolUseFailure` - Generic tool use hooks (fires for all tools)
- `subagentStart` / `subagentStop` - Subagent (Task tool) lifecycle
- `beforeShellExecution` / `afterShellExecution` - Control shell commands
- `beforeMCPExecution` / `afterMCPExecution` - Control MCP tool usage
- `beforeReadFile` / `afterFileEdit` - Control file access and edits
- `beforeSubmitPrompt` - Validate prompts before submission
- `preCompact` - Observe context window compaction
- `stop` - Handle agent completion
- `afterAgentResponse` / `afterAgentThought` - Track agent responses

**Tab (inline completions)** uses specialized hooks:

- `beforeTabFileRead` - Control file access for Tab completions
- `afterTabFileEdit` - Post-process Tab edits

These separate hooks allow different policies for autonomous Tab operations versus user-directed Agent operations.

## Quickstart

Create a `hooks.json` file. You can create it at the project level (`<project>/.cursor/hooks.json`) or in your home directory (`~/.cursor/hooks.json`). Project-level hooks apply only to that specific project, while home directory hooks apply globally.

### User hooks (\~/.cursor/)

For user-level hooks that apply globally, create `~/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": "./hooks/format.sh" }]
  }
}
```

Create your hook script at `~/.cursor/hooks/format.sh`:

```bash
#!/bin/bash
# Read input, do something, exit 0
cat > /dev/null
exit 0
```

Make it executable:

```bash
chmod +x ~/.cursor/hooks/format.sh
```

### Project hooks (.cursor/)

For project-level hooks that apply to a specific repository, create `<project>/.cursor/hooks.json`:

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [{ "command": ".cursor/hooks/format.sh" }]
  }
}
```

Note: Project hooks run from the **project root**, so use `.cursor/hooks/format.sh` (not `./hooks/format.sh`).

Create your hook script at `<project>/.cursor/hooks/format.sh`:

```bash
#!/bin/bash
# Read input, do something, exit 0
cat > /dev/null
exit 0
```

Make it executable:

```bash
chmod +x .cursor/hooks/format.sh
```

Restart Cursor. Your hook now runs after every file edit.

## Hook Types

Hooks support two execution types: command-based (default) and prompt-based (LLM-evaluated).

### Command-Based Hooks

Command hooks execute shell scripts that receive JSON input via stdin and return JSON output via stdout.

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "./scripts/approve-network.sh",
        "timeout": 30,
        "matcher": "curl|wget|nc"
      }
    ]
  }
}
```

**Exit code behavior:**

- Exit code `0` - Hook succeeded, use the JSON output
- Exit code `2` - Block the action (equivalent to returning `permission: "deny"`)
- Other exit codes - Hook failed, action proceeds (fail-open by default)

### Prompt-Based Hooks

Prompt hooks use an LLM to evaluate a natural language condition. They're useful for policy enforcement without writing custom scripts.

```json
{
  "hooks": {
    "beforeShellExecution": [
      {
        "type": "prompt",
        "prompt": "Does this command look safe to execute? Only allow read-only operations.",
        "timeout": 10
      }
    ]
  }
}
```

**Features:**

- Returns structured `{ ok: boolean, reason?: string }` response
- Uses a fast model for quick evaluation
- `$ARGUMENTS` placeholder is auto-replaced with hook input JSON
- If `$ARGUMENTS` is absent, hook input is auto-appended
- Optional `model` field to override the default LLM model

## Examples

The examples below use `./hooks/...` paths, which work for **user hooks** (`~/.cursor/hooks.json`) where scripts run from `~/.cursor/`. For **project hooks** (`<project>/.cursor/hooks.json`), use `.cursor/hooks/...` paths instead since scripts run from the project root.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "command": "./hooks/session-init.sh"
      }
    ],
    "sessionEnd": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./hooks/audit.sh"
      },
      {
        "command": "./hooks/block-git.sh"
      }
    ],
    "beforeMCPExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterShellExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterMCPExecution": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "afterFileEdit": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeSubmitPrompt": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "preCompact": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "stop": [
      {
        "command": "./hooks/audit.sh"
      }
    ],
    "beforeTabFileRead": [
      {
        "command": "./hooks/redact-secrets-tab.sh"
      }
    ],
    "afterTabFileEdit": [
      {
        "command": "./hooks/format-tab.sh"
      }
    ]
  }
}
```

```sh title="audit.sh"
#!/bin/bash

# audit.sh - Hook script that writes all JSON input to /tmp/agent-audit.log
# This script is designed to be called by Cursor's hooks system for auditing purposes

# Read JSON input from stdin
json_input=$(cat)

# Create timestamp for the log entry
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Create the log directory if it doesn't exist
mkdir -p "$(dirname /tmp/agent-audit.log)"

# Write the timestamped JSON entry to the audit log
echo "[$timestamp] $json_input" >> /tmp/agent-audit.log

# Exit successfully
exit 0
```

```sh title="block-git.sh"
#!/bin/bash

# Hook to block git commands and redirect to gh tool usage
# This hook implements the beforeShellExecution hook from the Cursor Hooks Spec

# Initialize debug logging
echo "Hook execution started" >> /tmp/hooks.log

# Read JSON input from stdin
input=$(cat)
echo "Received input: $input" >> /tmp/hooks.log

# Parse the command from the JSON input
command=$(echo "$input" | jq -r '.command // empty')
echo "Parsed command: '$command'" >> /tmp/hooks.log

# Check if the command contains 'git' or 'gh'
if [[ "$command" =~ git[[:space:]] ]] || [[ "$command" == "git" ]]; then
    echo "Git command detected - blocking: '$command'" >> /tmp/hooks.log
    # Block the git command and provide guidance to use gh tool instead
    cat << EOF
{
  "continue": true,
  "permission": "deny",
  "user_message": "Git command blocked. Please use the GitHub CLI (gh) tool instead.",
  "agent_message": "The git command '$command' has been blocked by a hook. Instead of using raw git commands, please use the 'gh' tool which provides better integration with GitHub and follows best practices. For example:\n- Instead of 'git clone', use 'gh repo clone'\n- Instead of 'git push', use 'gh repo sync' or the appropriate gh command\n- For other git operations, check if there's an equivalent gh command or use the GitHub web interface\n\nThis helps maintain consistency and leverages GitHub's enhanced tooling."
}
EOF
elif [[ "$command" =~ gh[[:space:]] ]] || [[ "$command" == "gh" ]]; then
    echo "GitHub CLI command detected - asking for permission: '$command'" >> /tmp/hooks.log
    # Ask for permission for gh commands
    cat << EOF
{
  "continue": true,
  "permission": "ask",
  "user_message": "GitHub CLI command requires permission: $command",
  "agent_message": "The command '$command' uses the GitHub CLI (gh) which can interact with your GitHub repositories and account. Please review and approve this command if you want to proceed."
}
EOF
else
    echo "Non-git/non-gh command detected - allowing: '$command'" >> /tmp/hooks.log
    # Allow non-git/non-gh commands
    cat << EOF
{
  "continue": true,
  "permission": "allow"
}
EOF
fi
```

### TypeScript stop automation hook

Choose TypeScript when you need typed JSON, durable file I/O, and HTTP calls in the same hook. This Bun-powered `stop` hook tracks per-conversation failure counts on disk, forwards structured telemetry to an internal API, and can automatically schedule a retry when the agent fails twice in a row.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "stop": [
      {
        "command": "bun run .cursor/hooks/track-stop.ts --stop"
      }
    ]
  }
}
```

```ts title=".cursor/hooks/track-stop.ts"
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { stdin } from 'bun';

type StopHookInput = {
  conversation_id: string;
  generation_id: string;
  model: string;
  status: 'completed' | 'aborted' | 'error';
  loop_count: number;
};

type StopHookOutput = {
  followup_message?: string;
};

type MetricsEntry = {
  lastStatus: StopHookInput['status'];
  errorCount: number;
  lastUpdatedIso: string;
};

type MetricsStore = Record<string, MetricsEntry>;

const STATE_DIR = '.cursor/hooks/state';
const METRICS_PATH = `${STATE_DIR}/agent-metrics.json`;
const TELEMETRY_URL = Bun.env.AGENT_TELEMETRY_URL;

async function parseHookInput<T>(): Promise<T> {
  const text = await stdin.text();
  return JSON.parse(text) as T;
}

async function readMetrics(): Promise<MetricsStore> {
  try {
    return JSON.parse(await readFile(METRICS_PATH, 'utf8')) as MetricsStore;
  } catch {
    return {};
  }
}

async function writeMetrics(store: MetricsStore) {
  await mkdir(STATE_DIR, { recursive: true });
  await writeFile(METRICS_PATH, JSON.stringify(store, null, 2), 'utf8');
}

async function sendTelemetry(payload: StopHookInput, entry: MetricsEntry) {
  if (!TELEMETRY_URL) return;
  await fetch(TELEMETRY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      conversationId: payload.conversation_id,
      generationId: payload.generation_id,
      model: payload.model,
      status: payload.status,
      errorCount: entry.errorCount,
      loopCount: payload.loop_count,
      timestamp: entry.lastUpdatedIso
    })
  });
}

async function main() {
  const payload = await parseHookInput<StopHookInput>();
  const metrics = await readMetrics();
  const entry =
    metrics[payload.conversation_id] ?? {
      lastStatus: payload.status,
      errorCount: 0,
      lastUpdatedIso: ''
    };

  entry.lastStatus = payload.status;
  entry.lastUpdatedIso = new Date().toISOString();
  entry.errorCount = payload.status === 'error' ? entry.errorCount + 1 : 0;

  metrics[payload.conversation_id] = entry;
  await writeMetrics(metrics);
  await sendTelemetry(payload, entry);

  const response: StopHookOutput = {};
  if (entry.errorCount >= 2 && payload.loop_count < 4) {
    response.followup_message =
      'Automated retry triggered after two failures. Double-check credentials before running again.';
  }

  process.stdout.write(JSON.stringify(response) + '\n');
}

main().catch(error => {
  console.error('[stop hook] failed', error);
  process.stdout.write('{}\n');
});
```

Set `AGENT_TELEMETRY_URL` to the internal endpoint that should receive run summaries.

### Python manifest guard hook

Python shines when you need rich parsing libraries. This hook uses `pyyaml` to inspect Kubernetes manifests before `kubectl apply` runs; Bash would struggle to parse multi-document YAML safely.

```json title="hooks.json"
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      {
        "command": "python3 .cursor/hooks/kube_guard.py"
      }
    ]
  }
}
```

```python title=".cursor/hooks/kube_guard.py"
#!/usr/bin/env python3
import json
import shlex
import sys
from pathlib import Path

import yaml

SENSITIVE_NAMESPACES = {"prod", "production"}

def main() -> None:
    payload = json.load(sys.stdin)
    command = payload.get("command", "")
    cwd = Path(payload.get("cwd") or ".")
    response = {"continue": True, "permission": "allow"}

    try:
        args = shlex.split(command)
    except ValueError:
        print(json.dumps(response))
        return

    if len(args) < 2 or args[0] != "kubectl" or args[1] != "apply" or "-f" not in args:
        print(json.dumps(response))
        return

    f_index = args.index("-f")
    if f_index + 1 >= len(args):
        print(json.dumps(response))
        return

    manifest_arg = args[f_index + 1]
    manifest_path = (cwd / manifest_arg).resolve()

    if not manifest_path.exists():
        print(json.dumps(response))
        return

    cli_namespace = None
    for i, arg in enumerate(args):
        if arg in ("-n", "--namespace") and i + 1 < len(args):
            cli_namespace = args[i + 1]
        elif arg.startswith("--namespace="):
            cli_namespace = arg.split("=", 1)[1]
        elif arg.startswith("-n="):
            cli_namespace = arg.split("=", 1)[1]

    try:
        documents = list(yaml.safe_load_all(manifest_path.read_text()))
    except (OSError, yaml.YAMLError) as exc:
        sys.stderr.write(f"Failed to read/parse {manifest_path}: {exc}\n")
        print(json.dumps(response))
        return

    if cli_namespace in SENSITIVE_NAMESPACES or any(
        (doc or {}).get("metadata", {}).get("namespace") in SENSITIVE_NAMESPACES
        for doc in documents
    ):
        response.update(
            {
                "permission": "ask",
                "user_message": "kubectl apply to prod requires manual approval.",
                "agent_message": f"{manifest_path.name} includes protected namespaces; confirm with your team before continuing.",
            }
        )

    print(json.dumps(response))

if __name__ == "__main__":
    main()
```

Install PyYAML (for example, `pip install pyyaml`) wherever your hook scripts run so the parser import succeeds.

## Partner Integrations

We partner with ecosystem vendors who have built hooks support with Cursor. These integrations cover security scanning, governance, secrets management, and more.

### MCP governance and visibility

| Partner                                                                                 | Description                                                                                                                                   |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| [MintMCP](https://www.mintmcp.com/blog/mcp-governance-cursor-hooks)                     | Build a complete inventory of MCP servers, monitor tool usage patterns, and scan responses for sensitive data before it reaches the AI model. |
| [Oasis Security](https://www.oasis.security/blog/cursor-oasis-governing-agentic-access) | Enforce least-privilege policies on AI agent actions and maintain full audit trails across enterprise systems.                                |
| [Runlayer](https://www.runlayer.com/blog/cursor-hooks)                                  | Wrap MCP tools and integrate with their MCP broker for centralized control and visibility over agent-to-tool interactions.                    |

### Code security and best practices

| Partner                                                          | Description                                                                                                                             |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Corridor](https://corridor.dev/blog/corridor-cursor-hooks/)     | Get real-time feedback on code implementation and security design decisions as code is being written.                                   |
| [Semgrep](https://semgrep.dev/blog/2025/cursor-hooks-mcp-server) | Automatically scan AI-generated code for vulnerabilities with real-time feedback to regenerate code until security issues are resolved. |

### Dependency security

| Partner                                                                                                             | Description                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| [Endor Labs](https://www.endorlabs.com/learn/bringing-malware-detection-into-ai-coding-workflows-with-cursor-hooks) | Intercept package installations and scan for malicious dependencies, preventing supply chain attacks before they enter your codebase. |

### Agent security and safety

| Partner                                                          | Description                                                                                                                             |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| [Snyk](https://snyk.io/blog/evo-agent-guard-cursor-integration/) | Review agent actions in real-time with Evo Agent Guard, detecting and preventing issues like prompt injection and dangerous tool calls. |

### Secrets management

| Partner                                                                 | Description                                                                                                                                                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [1Password](https://marketplace.1password.com/integration/cursor-hooks) | Validate that environment files from 1Password Environments are properly mounted before shell commands execute, enabling just-in-time secrets access without writing credentials to disk. |

For more details about our hooks partners, see the [Hooks for security and platform teams](/blog/hooks-partners) blog post.

## Configuration

Define hooks in a `hooks.json` file. Configuration can exist at multiple levels; higher-priority sources override lower ones:

```sh
~/.cursor/
├── hooks.json
└── hooks/
    ├── audit.sh
    └── block-git.sh
```

- **Enterprise** (MDM-managed, system-wide):
  - macOS: `/Library/Application Support/Cursor/hooks.json`
  - Linux/WSL: `/etc/cursor/hooks.json`
  - Windows: `C:\\ProgramData\\Cursor\\hooks.json`
- **Team** (Cloud-distributed, enterprise only):
  - Configured in the [web dashboard](https://cursor.com/dashboard?tab=team-content\&section=hooks) and synced to all team members automatically
- **Project** (Project-specific):
  - `<project-root>/.cursor/hooks.json`
  - Project hooks run in any trusted workspace and are checked into version control with your project
- **User** (User-specific):
  - `~/.cursor/hooks.json`

Priority order (highest to lowest): Enterprise → Team → Project → User

The `hooks` object maps hook names to arrays of hook definitions. Each definition currently supports a `command` property that can be a shell string, an absolute path, or a relative path. The working directory depends on the hook source:

- **Project hooks** (`.cursor/hooks.json` in a repository): Run from the **project root**
- **User hooks** (`~/.cursor/hooks.json`): Run from `~/.cursor/`
- **Enterprise hooks** (system-wide config): Run from the enterprise config directory
- **Team hooks** (cloud-distributed): Run from the managed hooks directory

For project hooks, use paths like `.cursor/hooks/script.sh` (relative to project root), not `./hooks/script.sh` (which would look for `<project>/hooks/script.sh`).

### Configuration file

This example shows a user-level hooks file (`~/.cursor/hooks.json`). For project-level hooks, change paths like `./hooks/script.sh` to `.cursor/hooks/script.sh`:

```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [{ "command": "./session-init.sh" }],
    "sessionEnd": [{ "command": "./audit.sh" }],
    "preToolUse": [
      {
        "command": "./hooks/validate-tool.sh",
        "matcher": "Shell|Read|Write"
      }
    ],
    "postToolUse": [{ "command": "./hooks/audit-tool.sh" }],
    "subagentStart": [{ "command": "./hooks/validate-subagent.sh" }],
    "subagentStop": [{ "command": "./hooks/audit-subagent.sh" }],
    "beforeShellExecution": [{ "command": "./script.sh" }],
    "afterShellExecution": [{ "command": "./script.sh" }],
    "afterMCPExecution": [{ "command": "./script.sh" }],
    "afterFileEdit": [{ "command": "./format.sh" }],
    "preCompact": [{ "command": "./audit.sh" }],
    "stop": [{ "command": "./audit.sh", "loop_limit": 10 }],
    "beforeTabFileRead": [{ "command": "./redact-secrets-tab.sh" }],
    "afterTabFileEdit": [{ "command": "./format-tab.sh" }]
  }
}
```

The Agent hooks (`sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`) apply to Cmd+K and Agent Chat operations. The Tab hooks (`beforeTabFileRead`, `afterTabFileEdit`) apply specifically to inline Tab completions.

### Global Configuration Options

| Option    | Type   | Default | Description           |
| --------- | ------ | ------- | --------------------- |
| `version` | number | `1`     | Config schema version |

### Per-Script Configuration Options

| Option       | Type                      | Default          | Description                                                                                                                              |
| ------------ | ------------------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `command`    | string                    | required         | Script path or command                                                                                                                   |
| `type`       | `"command"` \| `"prompt"` | `"command"`      | Hook execution type                                                                                                                      |
| `timeout`    | number                    | platform default | Execution timeout in seconds                                                                                                             |
| `loop_limit` | number \| null            | `5`              | Per-script loop limit for stop/subagentStop hooks. `null` means no limit. Default is `5` for Cursor hooks, `null` for Claude Code hooks. |
| `matcher`    | object                    | -                | Filter criteria for when hook runs                                                                                                       |

### Matcher Configuration

Matchers let you filter when a hook runs. Which field the matcher applies to depends on the hook:

```json
{
  "hooks": {
    "preToolUse": [
      {
        "command": "./validate-shell.sh",
        "matcher": "Shell"
      }
    ],
    "subagentStart": [
      {
        "command": "./validate-explore.sh",
        "matcher": "explore|shell"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./approve-network.sh",
        "matcher": "curl|wget|nc "
      }
    ]
  }
}
```

- **subagentStart**: The matcher runs against the **subagent type** (e.g. `explore`, `shell`, `generalPurpose`). Use it to run hooks only when a specific kind of subagent is started. The example above runs `validate-explore.sh` only for explore or shell subagents.
- **beforeShellExecution**: The matcher runs against the **shell command** string. Use it to run hooks only when the command matches a pattern (e.g. network calls, file deletions). The example above runs `approve-network.sh` only when the command contains `curl`, `wget`, or `nc `.

**Available matchers by hook:**

- **preToolUse** (and other tool hooks): Filter by tool type — `Shell`, `Read`, `Write`, `Grep`, `Delete`, `MCP`, `Task`, etc.
- **subagentStart**: Filter by subagent type — `generalPurpose`, `explore`, `shell`, etc.
- **beforeShellExecution**: Filter by the shell command text; the matcher is matched against the full command string.

## Team Distribution

Hooks can be distributed to team members using project hooks (via version control), MDM tools, or Cursor's cloud distribution system.

### Project Hooks (Version Control)

Project hooks are the simplest way to share hooks with your team. Place a `hooks.json` file at `<project-root>/.cursor/hooks.json` and commit it to your repository. When team members open the project in a trusted workspace, Cursor automatically loads and runs the project hooks.

Project hooks:

- Are stored in version control alongside your code
- Automatically load for all team members in trusted workspaces
- Can be project-specific (e.g., enforce formatting standards for a particular codebase)
- Require the workspace to be trusted to run (for security)

### MDM Distribution

Distribute hooks across your organization using Mobile Device Management (MDM) tools. Place the `hooks.json` file and hook scripts in the target directories on each machine.

**User home directory** (per-user distribution):

- `~/.cursor/hooks.json`
- `~/.cursor/hooks/` (for hook scripts)

**Global directories** (system-wide distribution):

- macOS: `/Library/Application Support/Cursor/hooks.json`
- Linux/WSL: `/etc/cursor/hooks.json`
- Windows: `C:\\ProgramData\\Cursor\\hooks.json`

Note: MDM-based distribution is fully managed by your organization. Cursor does not deploy or manage files through your MDM solution. Ensure your internal IT or security team handles configuration, deployment, and updates in accordance with your organization's policies.

### Cloud Distribution (Enterprise Only)

Enterprise teams can use Cursor's native cloud distribution to automatically sync hooks to all team members. Configure hooks in the [web dashboard](https://cursor.com/dashboard?tab=team-content\&section=hooks). Cursor automatically delivers configured hooks to all client machines when team members log in.

Cloud distribution provides:

- Automatic synchronization to all team members (every thirty minutes)
- Operating system targeting for platform-specific hooks
- Centralized management through the dashboard

Enterprise administrators can create, edit, and manage team hooks from the dashboard without requiring access to individual machines.

## Reference

### Common schema

#### Input (all hooks)

All hooks receive a base set of fields in addition to their hook-specific fields:

```json
{
  "conversation_id": "string",
  "generation_id": "string",
  "model": "string",
  "hook_event_name": "string",
  "cursor_version": "string",
  "workspace_roots": ["<path>"],
  "user_email": "string | null",
  "transcript_path": "string | null"
}
```

| Field             | Type           | Description                                                                                               |
| ----------------- | -------------- | --------------------------------------------------------------------------------------------------------- |
| `conversation_id` | string         | Stable ID of the conversation across many turns                                                           |
| `generation_id`   | string         | The current generation that changes with every user message                                               |
| `model`           | string         | The model configured for the composer that triggered the hook                                             |
| `hook_event_name` | string         | Which hook is being run                                                                                   |
| `cursor_version`  | string         | Cursor application version (e.g. "1.7.2")                                                                 |
| `workspace_roots` | string\[]      | The list of root folders in the workspace (normally just one, but multiroot workspaces can have multiple) |
| `user_email`      | string \| null | Email address of the authenticated user, if available                                                     |
| `transcript_path` | string \| null | Path to the main conversation transcript file (null if transcripts disabled)                              |

### Hook events

#### preToolUse

Called before any tool execution. This is a generic hook that fires for all tool types (Shell, Read, Write, MCP, Task, etc.). Use matchers to filter by specific tools.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm install", "working_directory": "/project" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "model": "claude-sonnet-4-20250514",
  "agent_message": "Installing dependencies..."
}

// Output
{
  "decision": "allow" | "deny",
  "reason": "<reason shown to agent if denied>",
  "updated_input": { "command": "npm ci" }
}
```

| Output Field    | Type              | Description                             |
| --------------- | ----------------- | --------------------------------------- |
| `decision`      | string            | `"allow"` to proceed, `"deny"` to block |
| `reason`        | string (optional) | Explanation shown to agent when denied  |
| `updated_input` | object (optional) | Modified tool input to use instead      |

#### postToolUse

Called after successful tool execution. Useful for auditing and analytics.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm test" },
  "tool_output": "All tests passed",
  "tool_use_id": "abc123",
  "cwd": "/project",
  "duration": 5432,
  "model": "claude-sonnet-4-20250514"
}

// Output
{
  "updated_mcp_tool_output": { "modified": "output" }
}
```

| Input Field   | Type   | Description                    |
| ------------- | ------ | ------------------------------ |
| `duration`    | number | Execution time in milliseconds |
| `tool_output` | string | Full output from the tool      |

| Output Field              | Type              | Description                                                    |
| ------------------------- | ----------------- | -------------------------------------------------------------- |
| `updated_mcp_tool_output` | object (optional) | For MCP tools only: replaces the tool output seen by the model |

#### postToolUseFailure

Called when a tool fails, times out, or is denied. Useful for error tracking and recovery logic.

```json
// Input
{
  "tool_name": "Shell",
  "tool_input": { "command": "npm test" },
  "tool_use_id": "abc123",
  "cwd": "/project",
  "error_message": "Command timed out after 30s",
  "failure_type": "timeout" | "error" | "permission_denied",
  "duration": 5000,
  "is_interrupt": false
}

// Output
{
  // No output fields currently supported
}
```

| Input Field     | Type    | Description                                                       |
| --------------- | ------- | ----------------------------------------------------------------- |
| `error_message` | string  | Description of the failure                                        |
| `failure_type`  | string  | Type of failure: `"error"`, `"timeout"`, or `"permission_denied"` |
| `duration`      | number  | Time in milliseconds until the failure occurred                   |
| `is_interrupt`  | boolean | Whether this failure was caused by a user interrupt/cancellation  |

#### subagentStart

Called before spawning a subagent (Task tool). Can allow or deny subagent creation.

```json
// Input
{
  "subagent_type": "generalPurpose",
  "prompt": "Explore the authentication flow",
  "model": "claude-sonnet-4-20250514"
}

// Output
{
  "decision": "allow" | "deny",
  "reason": "<reason if denied>"
}
```

#### subagentStop

Called when a subagent completes or errors. Can trigger follow-up actions.

```json
// Input
{
  "subagent_type": "generalPurpose",
  "status": "completed" | "error",
  "result": "<subagent output>",
  "duration": 45000,
  "agent_transcript_path": "/path/to/subagent/transcript.txt"
}

// Output
{
  "followup_message": "<auto-continue with this message>"
}
```

| Input Field             | Type           | Description                                                                        |
| ----------------------- | -------------- | ---------------------------------------------------------------------------------- |
| `subagent_type`         | string         | Type of subagent: `generalPurpose`, `explore`, `shell`, etc.                       |
| `status`                | string         | `"completed"` or `"error"`                                                         |
| `result`                | string         | Output/result from the subagent                                                    |
| `duration`              | number         | Execution time in milliseconds                                                     |
| `agent_transcript_path` | string \| null | Path to the subagent's own transcript file (separate from the parent conversation) |

The `followup_message` field enables loop-style flows where subagent completion triggers the next iteration.

#### beforeShellExecution / beforeMCPExecution

Called before any shell command or MCP tool is executed. Return a permission decision.

`beforeMCPExecution` uses **fail-closed** behavior. If the hook script fails to execute (crashes, times out, or returns invalid JSON), the MCP tool call will be blocked. This ensures MCP operations cannot bypass configured hooks.

```json
// beforeShellExecution input
{
  "command": "<full terminal command>",
  "cwd": "<current working directory>",
  "timeout": 30
}

// beforeMCPExecution input
{
  "tool_name": "<tool name>",
  "tool_input": "<json params>"
}
// Plus either:
{ "url": "<server url>" }
// Or:
{ "command": "<command string>" }

// Output
{
  "permission": "allow" | "deny" | "ask",
  "user_message": "<message shown in client>",
  "agent_message": "<message sent to agent>"
}
```

#### afterShellExecution

Fires after a shell command executes; useful for auditing or collecting metrics from command output.

```json
// Input
{
  "command": "<full terminal command>",
  "output": "<full terminal output>",
  "duration": 1234
}
```

| Field      | Type   | Description                                                                              |
| ---------- | ------ | ---------------------------------------------------------------------------------------- |
| `command`  | string | The full terminal command that was executed                                              |
| `output`   | string | Full output captured from the terminal                                                   |
| `duration` | number | Duration in milliseconds spent executing the shell command (excludes approval wait time) |

#### afterMCPExecution

Fires after an MCP tool executes; includes the tool's input parameters and full JSON result.

```json
// Input
{
  "tool_name": "<tool name>",
  "tool_input": "<json params>",
  "result_json": "<tool result json>",
  "duration": 1234
}
```

| Field         | Type   | Description                                                                         |
| ------------- | ------ | ----------------------------------------------------------------------------------- |
| `tool_name`   | string | Name of the MCP tool that was executed                                              |
| `tool_input`  | string | JSON params string passed to the tool                                               |
| `result_json` | string | JSON string of the tool response                                                    |
| `duration`    | number | Duration in milliseconds spent executing the MCP tool (excludes approval wait time) |

#### afterFileEdit

Fires after the Agent edits a file; useful for formatters or accounting of agent-written code.

```json
// Input
{
  "file_path": "<absolute path>",
  "edits": [{ "old_string": "<search>", "new_string": "<replace>" }]
}
```

#### beforeReadFile

Called before Agent reads a file. Use for access control to block sensitive files from being sent to the model.

This hook uses **fail-closed** behavior. If the hook script fails to execute (crashes, times out, or returns invalid JSON), the file read will be blocked. This provides security guarantees for sensitive file access.

```json
// Input
{
  "file_path": "<absolute path>",
  "content": "<file contents>",
  "attachments": [
    {
      "type": "file" | "rule",
      "filePath": "<absolute path>"
    }
  ]
}

// Output
{
  "permission": "allow" | "deny",
  "user_message": "<message shown when denied>"
}
```

| Input Field   | Type   | Description                                    |
| ------------- | ------ | ---------------------------------------------- |
| `file_path`   | string | Absolute path to the file being read           |
| `content`     | string | Full contents of the file                      |
| `attachments` | array  | Context attachments associated with the prompt |

| Output Field   | Type              | Description                             |
| -------------- | ----------------- | --------------------------------------- |
| `permission`   | string            | `"allow"` to proceed, `"deny"` to block |
| `user_message` | string (optional) | Message shown to user when denied       |

#### beforeTabFileRead

Called before Tab (inline completions) reads a file. Enable redaction or access control before Tab accesses file contents.

**Key differences from `beforeReadFile`:**

- Only triggered by Tab, not Agent
- Does not include `attachments` field (Tab doesn't use prompt attachments)
- Useful for applying different policies to autonomous Tab operations

```json
// Input
{
  "file_path": "<absolute path>",
  "content": "<file contents>"
}

// Output
{
  "permission": "allow" | "deny"
}
```

#### afterTabFileEdit

Called after Tab (inline completions) edits a file. Useful for formatters or auditing of Tab-written code.

**Key differences from `afterFileEdit`:**

- Only triggered by Tab, not Agent
- Includes detailed edit information: `range`, `old_line`, and `new_line` for precise edit tracking
- Useful for fine-grained formatting or analysis of Tab edits

```json
// Input
{
  "file_path": "<absolute path>",
  "edits": [
    {
      "old_string": "<search>",
      "new_string": "<replace>",
      "range": {
        "start_line_number": 10,
        "start_column": 5,
        "end_line_number": 10,
        "end_column": 20
      },
      "old_line": "<line before edit>",
      "new_line": "<line after edit>"
    }
  ]
}

// Output
{
  // No output fields currently supported
}
```

#### beforeSubmitPrompt

Called right after user hits send but before backend request. Can prevent submission.

```json
// Input
{
  "prompt": "<user prompt text>",
  "attachments": [
    {
      "type": "file" | "rule",
      "filePath": "<absolute path>"
    }
  ]
}

// Output
{
  "continue": true | false,
  "user_message": "<message shown to user when blocked>"
}
```

| Output Field   | Type              | Description                                          |
| -------------- | ----------------- | ---------------------------------------------------- |
| `continue`     | boolean           | Whether to allow the prompt submission to proceed    |
| `user_message` | string (optional) | Message shown to the user when the prompt is blocked |

#### afterAgentResponse

Called after the agent has completed an assistant message.

```json
// Input
{
  "text": "<assistant final text>"
}
```

#### afterAgentThought

Called after the agent completes a thinking block. Useful for observing the agent's reasoning process.

```json
// Input
{
  "text": "<fully aggregated thinking text>",
  "duration_ms": 5000
}

// Output
{
  // No output fields currently supported
}
```

| Field         | Type              | Description                                            |
| ------------- | ----------------- | ------------------------------------------------------ |
| `text`        | string            | Fully aggregated thinking text for the completed block |
| `duration_ms` | number (optional) | Duration in milliseconds for the thinking block        |

#### stop

Called when the agent loop ends. Can optionally auto-submit a follow-up user message to keep iterating.

```json
// Input
{
  "status": "completed" | "aborted" | "error",
  "loop_count": 0
}
```

```json
// Output
{
  "followup_message": "<message text>"
}
```

- The optional `followup_message` is a string. When provided and non-empty, Cursor will automatically submit it as the next user message. This enables loop-style flows (e.g., iterate until a goal is met).
- The `loop_count` field indicates how many times the stop hook has already triggered an automatic follow-up for this conversation (starts at 0). To prevent infinite loops, a maximum of 5 auto follow-ups is enforced.

#### sessionStart

Called when a new composer conversation is created. Use this hook to set up session-specific environment variables, inject additional context, or block session creation based on custom policies.

```json
// Input
{
  "session_id": "<unique session identifier>",
  "is_background_agent": true | false,
  "composer_mode": "agent" | "ask" | "edit"
}
```

```json
// Output
{
  "env": { "<key>": "<value>" },
  "additional_context": "<context to add to conversation>",
  "continue": true | false,
  "user_message": "<message shown if blocked>"
}
```

| Input Field           | Type              | Description                                                         |
| --------------------- | ----------------- | ------------------------------------------------------------------- |
| `session_id`          | string            | Unique identifier for this session (same as `conversation_id`)      |
| `is_background_agent` | boolean           | Whether this is a background agent session vs interactive session   |
| `composer_mode`       | string (optional) | The mode the composer is starting in (e.g., "agent", "ask", "edit") |

| Output Field         | Type               | Description                                                                                         |
| -------------------- | ------------------ | --------------------------------------------------------------------------------------------------- |
| `env`                | object (optional)  | Environment variables to set for this session. Available to all subsequent hook executions          |
| `additional_context` | string (optional)  | Additional context to add to the conversation's initial system context                              |
| `continue`           | boolean (optional) | Whether to continue with session creation. If false, the session will not be created. Default: true |
| `user_message`       | string (optional)  | Message to show to the user if `continue` is false                                                  |

#### sessionEnd

Called when a composer conversation ends. This is a fire-and-forget hook useful for logging, analytics, or cleanup tasks. The response is logged but not used.

```json
// Input
{
  "session_id": "<unique session identifier>",
  "reason": "completed" | "aborted" | "error" | "window_close" | "user_close",
  "duration_ms": 45000,
  "is_background_agent": true | false,
  "final_status": "<status string>",
  "error_message": "<error details if reason is 'error'>"
}
```

```json
// Output
{
  // No output fields - fire and forget
}
```

| Input Field           | Type              | Description                                                                               |
| --------------------- | ----------------- | ----------------------------------------------------------------------------------------- |
| `session_id`          | string            | Unique identifier for the session that is ending                                          |
| `reason`              | string            | How the session ended: "completed", "aborted", "error", "window\_close", or "user\_close" |
| `duration_ms`         | number            | Total duration of the session in milliseconds                                             |
| `is_background_agent` | boolean           | Whether this was a background agent session                                               |
| `final_status`        | string            | Final status of the session                                                               |
| `error_message`       | string (optional) | Error message if reason is "error"                                                        |

#### preCompact

Called before context window compaction/summarization occurs. This is an observational hook that cannot block or modify the compaction behavior. Useful for logging when compaction happens or notifying users.

```json
// Input
{
  "trigger": "auto" | "manual",
  "context_usage_percent": 85,
  "context_tokens": 120000,
  "context_window_size": 128000,
  "message_count": 45,
  "messages_to_compact": 30,
  "is_first_compaction": true | false
}
```

```json
// Output
{
  "user_message": "<message to show when compaction occurs>"
}
```

| Input Field             | Type    | Description                                                |
| ----------------------- | ------- | ---------------------------------------------------------- |
| `trigger`               | string  | What triggered the compaction: "auto" or "manual"          |
| `context_usage_percent` | number  | Current context window usage as a percentage (0-100)       |
| `context_tokens`        | number  | Current context window token count                         |
| `context_window_size`   | number  | Maximum context window size in tokens                      |
| `message_count`         | number  | Number of messages in the conversation                     |
| `messages_to_compact`   | number  | Number of messages that will be summarized                 |
| `is_first_compaction`   | boolean | Whether this is the first compaction for this conversation |

| Output Field   | Type              | Description                                        |
| -------------- | ----------------- | -------------------------------------------------- |
| `user_message` | string (optional) | Message to show to the user when compaction occurs |

## Environment Variables

Hook scripts receive environment variables when executed:

| Variable             | Description                                  | Always Present        |
| -------------------- | -------------------------------------------- | --------------------- |
| `CURSOR_PROJECT_DIR` | Workspace root directory                     | Yes                   |
| `CURSOR_VERSION`     | Cursor version string                        | Yes                   |
| `CURSOR_USER_EMAIL`  | Authenticated user email                     | If logged in          |
| `CURSOR_CODE_REMOTE` | Remote-aware project path                    | For remote workspaces |
| `CLAUDE_PROJECT_DIR` | Alias for project dir (Claude compatibility) | Yes                   |

Session-scoped environment variables from `sessionStart` hooks are passed to all subsequent hook executions within that session.

## Troubleshooting

**How to confirm hooks are active**

There is a Hooks tab in Cursor Settings to debug configured and executed hooks, as well as a Hooks output channel to see errors.

**If hooks are not working**

- Restart Cursor to ensure the hooks service is running.
- Check that relative paths are correct for your hook source:
  - For **project hooks**, paths are relative to the **project root** (e.g., `.cursor/hooks/script.sh`)
  - For **user hooks**, paths are relative to `~/.cursor/` (e.g., `./hooks/script.sh` or `hooks/script.sh`)

**Exit code blocking**

Exit code `2` from command hooks blocks the action (equivalent to returning `decision: "deny"`). This matches Claude Code behavior for compatibility.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/modes.md
# INDEX: 18/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/agent/overview.md
# INDEX: 19/114
================================================================================

# Cursor Agent

Agent is Cursor's assistant that can complete complex coding tasks independently, run terminal commands, and edit code. Access in sidepane with Cmd+I.

Learn more about [how agents work](https://cursor.com/learn/agents.md) and help you build faster.

## How Agent works

An agent is built on three components:

1. **Instructions**: The system prompt and [rules](https://cursor.com/docs/context/rules.md) that guide agent behavior
2. **Tools**: File editing, codebase search, terminal execution, and more
3. **User messages**: Your prompts and follow-ups that direct the work

Cursor's agent orchestrates these components for each model we support, tuning instructions and tools specifically for every frontier model. As new models are released, you can focus on building software while Cursor handles the model-specific optimizations.

## Tools

Tools are the building blocks of Agent. They are used to search your codebase and the web to find relevant information, make edits to your files, run terminal commands, and more.

To understand how tool calling works under the hood, see our [tool calling fundamentals](https://cursor.com/learn/tool-calling.md).

There is no limit on the number of tool calls Agent can make during a task.

### Semantic search

Perform semantic searches within your [indexed codebase](https://cursor.com/docs/context/semantic-search.md). Finds code by meaning, not just exact matches.

### Search files and folders

Search for files by name, read directory structures, and find exact keywords or patterns within files.

### Web

Generate search queries and perform web searches.

### Fetch Rules

Retrieve specific [rules](https://cursor.com/docs/context/rules.md) based on type and description.

### Read files

Intelligently read the content of a file. Also supports image files (.png, .jpg, .gif, .webp, .svg) and includes them in the conversation context for analysis by vision-capable models.

### Edit files

Suggest edits to files and [apply](https://cursor.com/docs/agent/apply.md) them automatically.

### Run shell commands

Execute terminal commands and monitor output. By default, Cursor uses the first terminal profile available.

To set your preferred terminal profile:

1. Open Command Palette (`Cmd/Ctrl+Shift+P`)
2. Search for "Terminal: Select Default Profile"
3. Choose your desired profile

### Browser

Control a browser to take screenshots, test applications, and verify visual changes. Agent can navigate pages, interact with elements, and capture the current state for analysis. See the [Browser documentation](https://cursor.com/docs/agent/browser.md) for details.

### Image generation

Generate images from text descriptions or reference images. Useful for creating UI mockups, product assets, and visualizing architecture diagrams. Images are saved to your project's `assets/` folder by default and shown inline in chat.

### Ask questions

Ask clarifying questions during a task. While waiting for your response, the agent continues reading files, making edits, or running commands. Your answer is incorporated as soon as it arrives.

## Message summarization

As conversations grow longer, Cursor automatically summarizes and manages context to keep your chats efficient. Learn how to use the context menu and understand how files are condensed to fit within model context windows.

### Using the /summarize command

You can manually trigger summarization using the `/summarize` command in chat. This command helps manage context when conversations become too long, allowing you to continue working efficiently without losing important information.

New to Cursor? Learn more about [Context](https://cursor.com/learn/context.md).

## Checkpoints

Checkpoints are automatic snapshots of Agent's changes to your codebase, letting you undo modifications if needed. Restore from the `Restore Checkpoint` button on previous requests or the + button when hovering over a message.

Checkpoints are stored locally and separate from Git. Only use them for undoing Agent changes—use Git for permanent version control.

## Export & Share

Export Agent chats as markdown files via the context menu → "Export Chat", or share them as read-only links. Shared chats let recipients view and fork the conversation to continue in their own Cursor.

Sharing requires a paid plan. Common secrets are auto-redacted and sharing is disabled in Privacy Mode.

## Queued messages

Queue follow-up messages while Agent is working on the current task. Your instructions wait in line and execute automatically when ready.

[Media](/docs-static/images/agent/planning/agent-queue.mp4)

### Using the queue

1. While Agent is working, type your next instruction
2. Press Enter to add it to the queue
3. Messages appear in order below the active task
4. Drag to reorder queued messages as needed
5. Agent processes them sequentially after finishing

### Keyboard shortcuts

While Agent is working:

- Press Enter to queue your message (it waits until Agent finishes the current task)
- Press Cmd+Enter to send immediately, bypassing the queue

### Immediate messaging

When you use Cmd+Enter to send immediately, your message is appended to the most recent user message in the chat and processed right away without waiting in the queue.

- Your message attaches to tool results and sends immediately
- This creates a more responsive experience for urgent follow-ups
- Use this when you need to interrupt or redirect Agent's current work


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/review.md
# INDEX: 20/114
================================================================================

# Review

When Agent generates code changes, they're presented in a review interface that shows additions and deletions with color-coded lines. This allows you to examine and control which changes are applied to your codebase.

The review interface displays code changes in a familiar diff format:

## Diffs

| Type              | Meaning                    | Example                          |
| :---------------- | :------------------------- | :------------------------------- |
| **Added lines**   | New code additions         | + const newVariable = 'hello';   |
| **Deleted lines** | Code removals              | - const oldVariable = 'goodbye'; |
| **Context lines** | Unchanged surrounding code |  function example()              |

## Agent Review

Agent Review runs Cursor Agent in a specialized mode focused on catching bugs in your diffs. This tool analyzes proposed changes line-by-line and flags issues before you merge.

> **Want automatic reviews on your PRs?**\
> Check out [Bugbot](https://cursor.com/docs/bugbot.md), which applies advanced analysis to catch issues early and suggest improvements automatically on every pull request.

There are two ways to use Agent Review: in the agent diff and in the source control tab.

### Agent diff

Review the output of an agent diff: after a response, click **Review**, then click **Find Issues** to analyze the proposed edits and suggest follow-ups.

![Review input interface](/docs-static/images/agent/review/diff-review.png)

### Source control

Review all changes against your main branch: open the Source Control tab and run Agent Review to review all local changes compared to your main branch.

### Billing

Running Agent Review triggers an agent run and is billed as a usage-based request.

### Settings

You can configure Agent Review in the Cursor settings.

| Setting                     | Description                                                  |
| --------------------------- | ------------------------------------------------------------ |
| **Auto-run on commit**      | Scan your code for bugs automatically after each commit      |
| **Include submodules**      | Include changes from Git submodules in the review            |
| **Include untracked files** | Include untracked files (not yet added to Git) in the review |

## Review UI

After generation completes, you'll see a prompt to review all changes before proceeding. This gives you an overview of what will be modified.

![Review input interface](/docs-static/images/chat/review/input-review.png)

### File-by-file

A floating review bar appears at the bottom of your screen, allowing you to:

- **Accept** or **reject** changes for the current file
- Navigate to the **next file** with pending changes

  [Media](/docs-static/images/chat/review/review-bar.mp4)

  Your browser does not support the video tag.

### Selective acceptance

For fine-grained control:

- To accept most changes: reject unwanted lines, then click **Accept all**
- To reject most changes: accept wanted lines, then click **Reject all**


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/security.md
# INDEX: 21/114
================================================================================

# Agent Security

AI can behave unexpectedly due to prompt injection, hallucinations, and other issues. We protect users with guardrails that limit what agents can do. By default, sensitive actions require your manual approval. This document explains our guardrails and what they mean for you.

These controls and behaviors are our defaults. We recommend keeping them enabled.

## First-party tool calls

Cursor includes tools that help agents write code: reading files, editing files, running terminal commands, searching the web, and more.

Reading files and searching code don't require approval. Use [.cursorignore](https://cursor.com/docs/context/ignore-files.md) to block agent access to specific files. Actions that could expose sensitive data require your explicit approval.

Agents can modify workspace files without approval, except for configuration files. Changes save immediately to disk. Always use version control so you can revert changes. Configuration files (like workspace settings) need your approval first.

**Warning:** If you have auto-reload enabled, agent changes might execute before you can review them.

Terminal commands need your approval by default. Review every command before letting the agent run it.

You can enable auto-approval if you accept the risk. We have an [allowlist](https://cursor.com/docs/agent/tools.md) feature, but it's not a security guarantee. The allowlist is best-effort—bypasses are possible. Never use "Run Everything" mode, which skips all safety checks.

## Third-party tool calls

You can connect external tools using [MCP](https://cursor.com/docs/context/mcp.md). All MCP connections need your approval. After you approve an MCP connection, each tool call still needs individual approval before running.

## Network requests

Attackers could use network requests to steal data. Our tools only make network requests to:

- GitHub
- Direct link retrieval
- Web search providers

Agents cannot make arbitrary network requests with default settings.

## Workspace trust

Cursor supports [workspace trust](https://code.visualstudio.com/docs/editing/workspaces/workspace-trust), but it's disabled by default. When enabled, it prompts you to choose between normal or restricted mode for new workspaces. Restricted mode breaks AI features. For untrusted repos, use a basic text editor instead.

To enable workspace trust:

1. Open your user settings.json file
2. Add the following configuration:

   ```json
   "security.workspace.trust.enabled": true
   ```

Organizations can enforce this setting through MDM solutions.

## Responsible disclosure

Found a vulnerability? Email [security-reports@cursor.com](mailto:security-reports@cursor.com) with details and steps to reproduce.

We acknowledge vulnerability reports within 5 business days. For critical incidents, we notify all users via email.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/terminal.md
# INDEX: 22/114
================================================================================

# Terminal

Agent runs shell commands directly in your terminal, with safe sandbox execution on macOS and Linux. Command history persists across sessions. Click skip to interrupt running commands with `Ctrl+C`.

## Sandbox

Sandbox is available on macOS (>v2.0) and Linux (>= v6.2). Windows users can use WSL2 for sandboxed command execution.

Auto mode is not currently compatible with Sandbox.

By default, Agent runs terminal commands in a restricted environment that blocks unauthorized file access and network activity. Commands execute automatically while staying confined to your workspace.

- **macOS**: Implemented using `sandbox-exec` (seatbelt)
- **Linux**: Implemented using Landlock v3 (kernel 6.2+), seccomp, and user namespaces

[Media](/docs-static/images/agent/sandbox.mp4)

### Linux Requirements

Linux sandbox requires:

- **Kernel 6.2 or later** with Landlock v3 support (`CONFIG_SECURITY_LANDLOCK=y`)
- **Unprivileged user namespaces** enabled (most modern distributions have this by default)

If your Linux kernel doesn't meet these requirements, Agent will fall back to asking for approval before running commands.

### How the sandbox works

The sandbox prevents unauthorized access while allowing workspace operations:

| Access Type         | Description                                                                                                                          |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------- |
| **File access**     | Read access to the filesystemRead and write access to workspace directories                                                          |
| **Network access**  | Blocked by default. Configure with [`sandbox.json`](https://cursor.com/docs/agent/terminal.md#sandbox-configuration) or in settings. |
| **Temporary files** | Full access to `/tmp/` or equivalent system temp directories                                                                         |

The `.cursor` configuration directory stays protected regardless of allowlist settings.

### Allowlist

Commands on the allowlist skip sandbox restrictions and run immediately. You can add commands to the allowlist by choosing "Add to allowlist" when prompted after a sandboxed command fails.

When a sandboxed command fails due to restrictions, you can:

| Option               | Description                                                          |
| :------------------- | :------------------------------------------------------------------- |
| **Skip**             | Cancel the command and let Agent try something else                  |
| **Run**              | Execute the command without sandbox restrictions                     |
| **Add to allowlist** | Run without restrictions and automatically approve it for future use |

#### Default network allowlist

When network access is enabled, outbound connections are restricted to a curated set of domains. These cover common package registries, cloud providers, and language toolchains so most development workflows work without extra configuration.

### View default allowed domains

```
*.cloudflarestorage.com
*.docker.com
*.docker.io
*.googleapis.com
*.githubusercontent.com
*.gvt1.com
*.public.blob.vercel-storage.com
*.yarnpkg.com
alpinelinux.org
anaconda.com
apache.org
apt.llvm.org
archive.ubuntu.com
archlinux.org
awscli.amazonaws.com
azure.com
binaries.prisma.sh
bitbucket.org
centos.org
cloudflarestorage.com
cocoapods.org
codeload.github.com
cpan.org
crates.io
debian.org
dl.google.com
docker.com
docker.io
dot.net
dotnet.microsoft.com
eclipse.org
fedoraproject.org
files.pythonhosted.org
gcr.io
ghcr.io
github.com
gitlab.com
golang.org
google.com
goproxy.io
gradle.org
haskell.org
hashicorp.com
hex.pm
index.crates.io
java.com
java.net
json-schema.org
json.schemastore.org
k8s.io
launchpad.net
maven.org
mcr.microsoft.com
metacpan.org
microsoft.com
mise.run
nodejs.org
npm.duckdb.org
npmjs.com
npmjs.org
nuget.org
oracle.com
packagecloud.io
packages.microsoft.com
packagist.org
pkg.go.dev
playwright.azureedge.net
ppa.launchpad.net
proxy.golang.org
pub.dev
public.blob.vercel-storage.com
public.ecr.aws
pypa.io
pypi.org
pypi.python.org
pythonhosted.org
quay.io
registry.npmjs.org
ruby-lang.org
rubygems.org
rubyonrails.org
rustup.rs
rvm.io
security.ubuntu.com
sh.rustup.rs
sourceforge.net
spring.io
static.crates.io
static.rust-lang.org
sum.golang.org
swift.org
ubuntu.com
visualstudio.com
yarnpkg.com
ziglang.org
```

## Sandbox Configuration

You can customize sandbox behavior with a `sandbox.json` file to control network access, filesystem paths, and more.

Customizing the sandbox requires Cursor version v2.5 or later.

### File locations

Place `sandbox.json` in either or both of these locations:

| Location                           | Scope                       | Priority |
| :--------------------------------- | :-------------------------- | :------- |
| `~/.cursor/sandbox.json`           | All workspaces (per-user)   | Lower    |
| `<workspace>/.cursor/sandbox.json` | Single workspace (per-repo) | Higher   |

Both files are optional. When both exist, they are merged with per-repo settings taking priority. Enterprise team-admin policies and Cursor's hardcoded security rules layer on top and cannot be weakened by either file.

### Quick start

#### Allow specific domains

```json
{
  "networkPolicy": {
    "default": "deny",
    "allow": [
      "registry.npmjs.org",
      "pypi.org",
      "*.githubusercontent.com"
    ]
  }
}
```

Network traffic is denied by default. Only the listed domains are reachable.

#### Allow all network

```json
{
  "networkPolicy": {
    "default": "allow"
  }
}
```

All outbound network traffic is permitted inside the sandbox.

#### Full example

A full-stack web project where the agent needs to install packages, pull container images, access a database on the local network, and read a shared design-tokens repo:

```json
{
  "networkPolicy": {
    "default": "deny",
    "allow": [
      "registry.npmjs.org",
      "registry.yarnpkg.com",
      "pypi.org",
      "files.pythonhosted.org",
      "*.docker.io",
      "ghcr.io",
      "*.googleapis.com"
    ],
    "deny": [
      "*.internal.corp.example.com"
    ]
  },
  "additionalReadwritePaths": [
    "/home/me/.docker"
  ],
  "additionalReadonlyPaths": [
    "/opt/shared/design-tokens"
  ],
  "enableSharedBuildCache": true
}
```

This lets the agent:

- Install npm/pip packages and pull Docker images.
- Hit Google Cloud APIs.
- Block access to internal corporate services.
- Write to `~/.docker` for container operations.
- Read (but not modify) a shared design-tokens directory.
- Share npm/pip/cargo caches between sandboxed and unsandboxed runs.

### Schema reference

All fields are optional. Missing fields use the defaults shown below.

#### Top-level fields

| Field                      | Type       | Default                 | Description                                                                                                                                                                     |
| :------------------------- | :--------- | :---------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `type`                     | string     | `"workspace_readwrite"` | Sandbox mode. `"workspace_readwrite"` gives read/write access in the workspace. `"workspace_readonly"` restricts to read-only. `"insecure_none"` disables the sandbox entirely. |
| `additionalReadwritePaths` | `string[]` | `[]`                    | Extra paths the agent can read and write. Only applies when `type` is `"workspace_readwrite"`.                                                                                  |
| `additionalReadonlyPaths`  | `string[]` | `[]`                    | Extra paths the agent can read.                                                                                                                                                 |
| `disableTmpWrite`          | `boolean`  | `false`                 | When `true`, removes default write access to `/tmp` and system temp directories.                                                                                                |
| `enableSharedBuildCache`   | `boolean`  | `false`                 | Redirects build-tool caches (npm, cargo, pip, etc.) to a shared tmpdir so sandboxed and unsandboxed commands share the same caches.                                             |

#### `networkPolicy` object

| Field     | Type                  | Default  | Description                                                                                   |
| :-------- | :-------------------- | :------- | :-------------------------------------------------------------------------------------------- |
| `default` | `"allow"` \| `"deny"` | `"deny"` | Action when no allow/deny rule matches.                                                       |
| `allow`   | `string[]`            | `[]`     | Patterns to allow. Supports exact domains, wildcards, and CIDR notation.                      |
| `deny`    | `string[]`            | `[]`     | Patterns to deny. Highest priority; always blocks, even if a pattern also appears in `allow`. |

### Network pattern syntax

The `allow` and `deny` arrays accept three pattern formats:

| Format       | Example                | Matches                                                        |
| :----------- | :--------------------- | :------------------------------------------------------------- |
| Exact domain | `"registry.npmjs.org"` | That exact host                                                |
| Wildcard     | `"*.example.com"`      | Any subdomain of `example.com`, including `example.com` itself |
| CIDR         | `"10.0.0.0/8"`         | Any IP in that range                                           |

**Key rules:**

- Deny always beats allow. If a host matches both lists, it is blocked.
- Private/RFC 1918 addresses (`10.x`, `172.16.x`, `192.168.x`, `127.x`) and cloud metadata endpoints (`169.254.169.254`) are blocked by default to prevent SSRF.
- IPv6 private addresses (`::1`, `fe80::/10`, `fc00::/7`) are also blocked.
- URL paths are ignored; matching is domain/IP only.

### How policies merge

When multiple policy sources exist, they merge in priority order:

```
per-user  <  per-repo  <  team-admin  <  hardcoded
(lowest)                                (highest)
```

Merge rules:

- **Paths** (`additionalReadwritePaths`, `additionalReadonlyPaths`): unioned across all sources.
- **Network allow lists**: unioned, unless a team-admin allowlist is present (which replaces the union).
- **Network deny lists**: always unioned.
- **`networkPolicy.default`**: `"deny"` wins over `"allow"`.
- **Restrictive booleans** (`disableTmpWrite`, `networkPolicyStrict`): `true` wins.

### Protected paths

Certain paths are always write-protected, regardless of your `sandbox.json` configuration:

- `.cursor/*.json`, `.cursor/**/*.json`, `.cursor/.workspace-trusted`
- `.claude/*.json`, `.claude/**/*.json`
- `.vscode/**`
- `.code-workspace`
- `.git/hooks/**`, `.git/config`, `.git/info/attributes`
- `.cursorignore`

The following `.cursor` subdirectories **are** writable: `rules/`, `commands/`, `worktrees/`, `skills/`, `agents/`.

SSL certificate paths and `~/.ssh` are always readable.

## Editor Configuration

Configure how Agent runs terminal commands in the editor by navigating to Settings -> Cursor Settings -> Agents -> Auto-Run.

| Editor Setting               | Description                                                                                                                                                                                                                                                                                                                                                                                                                |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Run Mode**            | Choose how Agent runs tools like command execution, MCP, and file writes. Users can select from three options: • **Run in Sandbox**: Tools and commands will auto-run in sandbox where possible. Available on macOS and Linux. • **Ask Every Time**: All tools and commands require user approval before running. • **Run Everything**: The agent runs all tools and commands automatically without asking for user input. |
| **Auto-Run Network Access**  | Choose how sandboxed commands access the network: - **sandbox.json Only**: Network is limited to domains in your `sandbox.json` allowlist. No Cursor defaults are added. - **sandbox.json + Defaults**: Your allowlist plus Cursor's built-in defaults (common package managers, etc.). This is the default. - **Allow All**: All network access is allowed in the sandbox, regardless of `sandbox.json`.                  |
| **Command Allowlist**        | Commands that can run automatically outside of the sandbox.                                                                                                                                                                                                                                                                                                                                                                |
| **MCP Allowlist**            | MCP tools that can run automatically outside of the sandbox.                                                                                                                                                                                                                                                                                                                                                               |
| **Browser Protection**       | Prevent Agent from automatically running [Browser](https://cursor.com/docs/agent/browser.md) tools.                                                                                                                                                                                                                                                                                                                        |
| **File-Deletion Protection** | Prevent Agent from deleting files automatically.                                                                                                                                                                                                                                                                                                                                                                           |
| **Dotfile Protection**       | Prevent Agent from modifying dot files like .gitignore automatically.                                                                                                                                                                                                                                                                                                                                                      |
| **External-File Protection** | Prevent Agent from creating or modifying files outside of the workspace automatically.                                                                                                                                                                                                                                                                                                                                     |

## Enterprise Controls

Only available for Enterprise subscriptions.

Enterprise admins can override editor configurations or change which settings are visible for end users. Navigate to Settings -> Auto-Run in the [web dashboard](https://cursor.com/dashboard?tab=settings) to view and change these settings.

| Admin Setting                  | Description                                                                                                                                                                                                     |
| :----------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Run Controls**          | Enable controls for auto-run and sandbox mode. If disabled, the default behavior for all end users is that commands will auto-run in the sandbox when available, otherwise they will ask for permission to run. |
| **Sandboxing Mode**            | Control whether sandbox is available for end users. When enabled, commands will run automatically in the sandbox even if they are not on the allowlist.                                                         |
| **Sandbox Networking**         | Choose whether commands that run in the sandbox have network access.                                                                                                                                            |
| **Delete File Protection**     | Prevent Agent from deleting files automatically.                                                                                                                                                                |
| **MCP Tool Protection**        | When enabled, prevents the agent from automatically running MCP tools.                                                                                                                                          |
| **Terminal Command Allowlist** | Specify which terminal commands can run automatically without sandboxing. If empty, all commands require manual approval. When sandbox is enabled, commands not on this list will auto-run in sandbox mode.     |
| **Enable Run Everything**      | Give end users the ability to enable the `Run Everything` Auto-Run-Mode.                                                                                                                                        |

## Linux AppArmor configuration

On Linux, the sandbox uses user namespaces, which some distributions restrict through AppArmor. The Cursor desktop package ships with the required AppArmor profile, so no extra setup is needed for local installations.

Remote environments and the standalone [agent-cli](https://cursor.com/docs/agent/agent-cli.md) don't include this profile. If sandbox creation fails with a permissions error related to user namespaces, install the AppArmor configuration package for your distribution:

**Debian / Ubuntu (.deb)**:

```bash
curl -fsSL https://downloads.cursor.com/lab/enterprise/cursor-sandbox-apparmor_0.2.0_all.deb -o cursor-sandbox-apparmor.deb
sudo dpkg -i cursor-sandbox-apparmor.deb
```

**RHEL / Fedora (.rpm)**:

```bash
curl -fsSL https://downloads.cursor.com/lab/enterprise/cursor-sandbox-apparmor-0.2.0-1.noarch.rpm -o cursor-sandbox-apparmor.rpm
sudo rpm -i cursor-sandbox-apparmor.rpm
```

After installing, restart Cursor or your agent-cli session for the sandbox to work.

## Troubleshooting

Some shell themes (for example, Powerlevel9k/Powerlevel10k) can interfere with
the inline terminal output. If your command output looks truncated or
misformatted, disable the theme or switch to a simpler prompt when Agent runs.

### Disable heavy prompts for Agent sessions

Use the `CURSOR_AGENT` environment variable in your shell config to detect when
the Agent is running and skip initializing fancy prompts/themes.

```zsh
# ~/.zshrc — disable Powerlevel10k when Cursor Agent runs
if [[ -n "$CURSOR_AGENT" ]]; then
  # Skip theme initialization for better compatibility
else
  [[ -r ~/.p10k.zsh ]] && source ~/.p10k.zsh
fi
```

```bash
# ~/.bashrc — fall back to a simple prompt in Agent sessions
if [[ -n "$CURSOR_AGENT" ]]; then
  PS1='\u@\h \W \$ '
fi
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/agent/third-party-hooks.md
# INDEX: 23/114
================================================================================

# Third Party Hooks

Cursor supports loading hooks from third-party tools, enabling compatibility with existing hook configurations from other AI coding assistants.

## Claude Code Hooks

Cursor can load and execute hooks configured for Claude Code, allowing you to use the same hook scripts across both tools.

### Requirements

To enable Claude Code hooks compatibility:

1. **Enable Third-party skills** in Cursor Settings → Features → Third-party skills
2. The feature must be enabled for your account

### Configuration Locations

Claude Code hooks are loaded from these locations (in priority order):

| Location          | Path                          | Description                            |
| ----------------- | ----------------------------- | -------------------------------------- |
| **Project local** | `.claude/settings.local.json` | Project-specific, gitignored overrides |
| **Project**       | `.claude/settings.json`       | Project-level hooks, checked into repo |
| **User**          | `~/.claude/settings.json`     | User-level hooks, apply globally       |

### Priority Order

When hooks are configured in multiple locations, they are merged in this priority order (highest to lowest):

1. Enterprise hooks (managed deployment)
2. Team hooks (dashboard-configured)
3. Project hooks (`.cursor/hooks.json`)
4. User hooks (`~/.cursor/hooks.json`)
5. Claude project local (`.claude/settings.local.json`)
6. Claude project (`.claude/settings.json`)
7. Claude user (`~/.claude/settings.json`)

Higher-priority hooks run first, and any hook can block execution for lower-priority hooks.

### Claude Code Hook Format

Claude Code hooks use a similar but slightly different format. Cursor automatically maps Claude hook names to their Cursor equivalents.

**Example Claude Code settings.json:**

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Shell",
        "hooks": [
          {
            "type": "command",
            "command": "./hooks/validate-shell.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "./hooks/audit.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Step Mapping

Claude Code hook names are automatically mapped to Cursor hook names:

| Claude Code Hook   | Cursor Hook          |
| ------------------ | -------------------- |
| `PreToolUse`       | `preToolUse`         |
| `PostToolUse`      | `postToolUse`        |
| `UserPromptSubmit` | `beforeSubmitPrompt` |
| `Stop`             | `stop`               |
| `SubagentStop`     | `subagentStop`       |
| `SessionStart`     | `sessionStart`       |
| `SessionEnd`       | `sessionEnd`         |
| `PreCompact`       | `preCompact`         |

### Exit Code Behavior

Both Cursor and Claude Code hooks support exit code `2` to block an action. This provides consistent behavior when sharing hooks between tools:

```bash
#!/bin/bash
# Block dangerous commands
if [[ "$COMMAND" == *"rm -rf"* ]]; then
  echo '{"decision": "deny", "reason": "Destructive command blocked"}'
  exit 2
fi
echo '{"decision": "allow"}'
exit 0
```

- **Exit code 0**: Hook succeeded, use the JSON output
- **Exit code 2**: Block the action (equivalent to `decision: "deny"`)
- **Other exit codes**: Hook failed, action proceeds (fail-open)

### Migration from Claude Code

If you have existing Claude Code hooks, you can:

1. **Keep using Claude Code config files**: Enable third-party skills and your existing `.claude/settings.json` hooks will work automatically
2. **Migrate to Cursor format**: Copy your hooks to `.cursor/hooks.json` using the Cursor format for full feature support

**Cursor format equivalent:**

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "command": "./hooks/validate-shell.sh",
        "matcher": "Shell"
      }
    ],
    "postToolUse": [
      {
        "command": "./hooks/audit.sh"
      }
    ]
  }
}
```

## Supported Features

When using Claude Code hooks in Cursor, the following features are supported:

| Claude Code Event   | Cursor Mapping       | Supported |
| ------------------- | -------------------- | --------- |
| `PreToolUse`        | `preToolUse`         | Yes       |
| `PostToolUse`       | `postToolUse`        | Yes       |
| `Stop`              | `stop`               | Yes       |
| `SubagentStop`      | `subagentStop`       | Yes       |
| `SessionStart`      | `sessionStart`       | Yes       |
| `SessionEnd`        | `sessionEnd`         | Yes       |
| `PreCompact`        | `preCompact`         | Yes       |
| `UserPromptSubmit`  | `beforeSubmitPrompt` | Yes       |
| `Notification`      | -                    | No        |
| `PermissionRequest` | -                    | No        |

**Additional supported features:**

| Feature                                 | Supported |
| --------------------------------------- | --------- |
| Command-based hooks (`type: "command"`) | Yes       |
| Prompt-based hooks (`type: "prompt"`)   | Yes       |
| Exit code 2 blocking                    | Yes       |
| Tool matchers (regex patterns)          | Yes       |
| Timeout configuration                   | Yes       |

### Tool Name Mapping

Claude Code tool names are mapped to Cursor tool names:

| Claude Code Tool | Cursor Tool | Supported |
| ---------------- | ----------- | --------- |
| `Bash`           | `Shell`     | Yes       |
| `Read`           | `Read`      | Yes       |
| `Write`          | `Write`     | Yes       |
| `Edit`           | `Write`     | Yes       |
| `Grep`           | `Grep`      | Yes       |
| `Task`           | `Task`      | Yes       |
| `Glob`           | -           | No        |
| `WebFetch`       | -           | No        |
| `WebSearch`      | -           | No        |

### Limitations

Some features are only available when using the native Cursor format:

- `subagentStart` hook (Claude Code only has `SubagentStop`)
- Loop limit configuration (`loop_limit`)
- Team/Enterprise hook distribution via dashboard

## Troubleshooting

**Claude Code hooks not loading**

1. Verify "Third-party skills" is enabled in Cursor Settings
2. Check that your `.claude/settings.json` file is valid JSON
3. Restart Cursor after enabling the setting

**Hooks running but not blocking**

1. Ensure your hook script exits with code `2` to block actions
2. Check the JSON output format matches the expected schema
3. View the Hooks output channel in Cursor for error details

**Different behavior between Cursor and Claude Code**

Some behavior differences may exist due to different execution environments. Test your hooks in both tools to ensure compatibility.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/bugbot.md
# INDEX: 24/114
================================================================================

# Bugbot

Bugbot reviews pull requests and identifies bugs, security issues, and code quality problems.

On Teams and Individual Plans, Bugbot includes a free tier: every user gets a limited number of free PR reviews each month. When you reach the limit, reviews pause until your next billing cycle. You can start a 14‑day free Bugbot Pro trial for unlimited reviews (subject to standard abuse guardrails).

[Bugbot leaving comments on a PR](/docs-static/images/bugbot/bugbot-report-cropped.mp4)

## How it works

Bugbot analyzes PR diffs and leaves comments with explanations and fix suggestions. It runs automatically on each PR update or manually when triggered.

- Runs **automatic reviews** on every PR update
- **Manual trigger** by commenting `cursor review` or `bugbot run` on any PR
- **Uses existing PR comments as context**: reads GitHub PR comments (top‑level and inline) to avoid duplicate suggestions and build on prior feedback
- **Fix in Cursor** links open issues directly in Cursor
- **Fix in Web** links open issues directly in [cursor.com/agents](https://cursor.com/agents)

## Setup

### GitHub.com

Requires Cursor admin access and GitHub org admin access.

1. Go to [cursor.com/dashboard](https://cursor.com/dashboard?tab=integrations)
2. Navigate to the Integrations tab
3. Click `Connect GitHub` (or `Manage Connections` if already connected)
4. Follow the GitHub installation flow
5. Return to the dashboard to enable Bugbot on specific repositories

[Bugbot GitHub setup](/docs-static/images/bugbot/bugbot-install.mp4)

### GitLab.com

Requires Cursor admin access and GitLab maintainer access.

GitLab integration requires a **paid GitLab plan** (Premium or Ultimate). Project access tokens, which are required for this integration, are not available on GitLab Free.

1. Go to [cursor.com/dashboard](https://cursor.com/dashboard?tab=integrations)
2. Navigate to the Integrations tab
3. Click `Connect GitLab` (or `Manage Connections` if already connected)
4. Follow the GitLab installation flow
5. Return to the dashboard to enable Bugbot on specific repositories

[Bugbot GitLab setup](/docs-static/images/bugbot/bugbot-gitlab.mp4)

### GitHub Enterprise Server

### Prerequisites

- Running a supported version of GitHub Enterprise Server (v3.8 or later recommended)
- Admin privileges on your GHES instance

### Networking

GHES requires secure inbound access for PR reviews and outbound access for webhook notifications.

#### IP Whitelisting (Recommended)

Add these IP addresses to your allowlist:

```text
184.73.225.134
3.209.66.12
52.44.113.131
```

If you need other connection options beyond IP whitelisting see the [FAQ](https://cursor.com/docs/bugbot.md#faq) section.

### Register the Cursor Enterprise App

1. Go to [Cursor Dashboard](https://cursor.com/dashboard?tab=integrations) → **Advanced** → **GitHub Enterprise Server**
2. Enter the **base URL** of your GHES instance (e.g., `https://git.yourcompany.com`)
3. Enter the name of the **Organization** that will own the application
   - This should be your company's Organization inside your GHES installation
   - You need administrator privileges for this Organization
   - Other Organizations can access the app once registered
   - Leave blank to use your user account (not recommended)
4. Click **Register**
5. Choose a name for the Cursor Enterprise Application (default recommended)
6. The app will appear under your available GitHub Apps in your GHES instance
7. Return to the dashboard to enable Bugbot on specific repositories

### GitLab Self-Hosted

GitLab integration requires a **paid GitLab plan** (Premium or Ultimate). Project access tokens, which are required for this integration, are not available on GitLab Free.

### Networking

- GitLab self-hosted requires secure inbound access for PR reviews and outbound access for webhook notifications.
- You need admin privileges on your GitLab instance to create the application.

#### IP Whitelisting (Recommended)

Add these IP addresses to your allowlist:

```text
184.73.225.134
3.209.66.12
52.44.113.131
```

If you need other connection options beyond IP whitelisting see the [FAQ](https://cursor.com/docs/bugbot.md#faq) section.

### Create GitLab Application

1. In your GitLab instance, create a new application (Instance level preferred)
2. Set the redirect URI to `https://cursor.com/gitlab-connected`
3. Configure the application:
   - **Trusted**: `true`
   - **Confidential**: `true`
   - **Scopes**: `api` and `write_repository`
4. After creation, you'll receive an **Application ID** and **Secret**

### Register with Cursor

1. Go to [cursor.com/dashboard](https://cursor.com/dashboard?tab=integrations) → **Advanced** → **GitLab Self-Hosted**
2. Enter your GitLab instance **hostname**
3. Paste the **Application ID** and **Secret**
4. Click **Register**
5. Select your GitLab instance from the dropdown
6. Click **Connect** to complete the installation
7. Enable Bugbot on specific repositories from the [Bugbot tab in the dashboard](https://cursor.com/dashboard?tab=bugbot)

## Configuration

### Individual

### Repository settings

Enable or disable Bugbot per repository from your installations list. Bugbot runs only on PRs you author.

### Personal settings

- Run **only when mentioned** by commenting `cursor review` or `bugbot run`
- Run **only once** per PR, skipping subsequent commits

### Team

### Repository settings

Team admins can enable Bugbot per repository, configure allow/deny lists for reviewers, and set:

- Run **only once** per PR per installation, skipping subsequent commits

Bugbot runs for all contributors to enabled repositories, regardless of team membership.

### Personal settings

Team members can override settings for their own PRs:

- Run **only when mentioned** by commenting `cursor review` or `bugbot run`
- Run **only once** per PR, skipping subsequent commits
- **Enable reviews on draft PRs** to include draft pull requests in automatic reviews

## Analytics

![Bugbot dashboard](/docs-static/images/bugbot/bugbot-dashboard.png)

## Rules

Create `.cursor/BUGBOT.md` files to provide project-specific context for reviews. Bugbot always includes the root `.cursor/BUGBOT.md` file and any additional files found while traversing upward from changed files.

```bash
project/
  .cursor/BUGBOT.md          # Always included (project-wide rules)
  backend/
    .cursor/BUGBOT.md        # Included when reviewing backend files
    api/
      .cursor/BUGBOT.md      # Included when reviewing API files
  frontend/
    .cursor/BUGBOT.md        # Included when reviewing frontend files
```

### Team rules

Team admins can create rules from the [Bugbot dashboard](https://cursor.com/dashboard?tab=bugbot) that apply to all repositories in the team. These rules are available to every enabled repository, making it easy to enforce organization-wide standards.

When both Team Rules and project rule files (`.cursor/BUGBOT.md`) exist, Bugbot uses both. They are applied in this order: Team Rules → project BUGBOT.md (including nested files) → User Rules.

### Examples

### Security: Flag any use of eval() or exec()

```text
If any changed file contains the string pattern /\beval\s*\(|\bexec\s*\(/i, then:
- Add a blocking Bug with title "Dangerous dynamic execution" and body:
  "Usage of eval/exec was found. Replace with safe alternatives or justify with a detailed comment and tests."
- Assign the Bug to the PR author.
- Apply label "security".
```

### OSS licenses: Prevent importing disallowed licenses

```text
If the PR modifies dependency files (package.json, pnpm-lock.yaml, yarn.lock, requirements.txt, go.mod, Cargo.toml), then:
- Run the built-in License Scan.
- If any new or upgraded dependency has license in {GPL-2.0, GPL-3.0, AGPL-3.0}, then:
  - Add a blocking Bug titled "Disallowed license detected"
  - Include the offending package names, versions, and licenses in the Bug body
  - Apply labels "compliance" and "security"
```

### Language standards: Flag React componentWillMount usage

```text
For files matching **/*.{js,jsx,ts,tsx} in React projects:
If a changed file contains /componentWillMount\s*\(/, then:
- Add a blocking Bug titled "Deprecated React lifecycle method"
- Body: "Replace componentWillMount with constructor or useEffect. See React docs."
- Suggest an autofix snippet that migrates side effects to useEffect.
```

### Standards: Require tests for backend changes

```text
If the PR modifies files in {server/**, api/**, backend/**} and there are no changes in {**/*.test.*, **/__tests__/**, tests/**}, then:
- Add a blocking Bug titled "Missing tests for backend changes"
- Body: "This PR modifies backend code but includes no accompanying tests. Please add or update tests."
- Apply label "quality"
```

### Style: Disallow TODO comments

```text
If any changed file contains /(?:^|\s)(TODO|FIXME)(?:\s*:|\s+)/, then:
- Add a non-blocking Bug titled "TODO/FIXME comment found"
- Body: "Replace TODO/FIXME with a tracked issue reference, e.g., `TODO(#1234): ...`, or remove it."
- If the TODO already references an issue pattern /#\d+|[A-Z]+-\d+/, mark the Bug as resolved automatically.
```

## Autofix

Bugbot Autofix automatically spawns a [Cloud Agent](https://cursor.com/docs/cloud-agent.md#overview) to fix bugs found during PR reviews.

### How it works

When Bugbot finds bugs during a PR review, it can automatically:

1. Spawn a Cloud Agent to analyze and fix the reported issues
2. Push fixes to the existing branch or a new branch (depending on your settings)
3. Post a comment on the original PR with the results

![Bugbot Autofix comment on a PR](/docs-static/images/bugbot/bugbot-autofix-comment.png)

### Configuration

Configure autofix behavior from the [Bugbot dashboard](https://cursor.com/dashboard?tab=bugbot).

### Individual

Individual users can configure their autofix preference in their personal Bugbot settings:

- **Use Installation Default** — Follow your organization's settings
- **Off** — autofix is disabled; use manual "Fix in Cursor" or "Fix in Web" links
- **Create New Branch** (Recommended) — Push fixes to a new branch
- **Commit to Existing Branch** — Push fixes to your branch (max 3 attempts per PR to prevent loops)

User settings override team defaults for your own PRs.

### Team

Team admins can set a default autofix mode for all team members in a GitHub organization:

- **Off** — autofix is disabled by default
- **Create New Branch** (Recommended) — Push fixes to a new branch for team members
- **Commit to Existing Branch** — Push fixes directly to the PR branch (max 3 attempts per PR to prevent loops)

Individual team members can override these defaults in their personal settings.

Autofix uses your **Default agent model** from [Settings → Models](https://cursor.com/dashboard?tab=settings). If you haven't set a personal model preference, autofix falls back to your team's default model (if you're on a team) or the system default.

### Requirements

Autofix requires:

- [Usage-based pricing](https://cursor.com/docs/account/usage.md) enabled
- Storage enabled (not in Legacy Privacy Mode)

### Billing

Autofix uses Cloud Agent credits and is billed at your plan rates. Cloud Agent billing follows your existing [pricing plan](https://cursor.com/docs/account/pricing.md).

## Admin Configuration API

Team admins can use the Bugbot Admin API to manage repositories and control which users can use Bugbot. Use it to automate repository management, enable Bugbot across multiple repositories, or integrate user provisioning with internal tools.

### Authentication

All endpoints require a team Admin API Key passed as a Bearer token:

```bash
Authorization: Bearer $API_KEY
```

To create an API key:

1. Visit the [Settings tab in the Cursor dashboard](https://cursor.com/dashboard?tab=settings)
2. Under **Advanced**, click **New Admin API Key**
3. Save the API key

All endpoints are rate-limited to 60 requests per minute per team.

### Enabling or disabling repositories

Use the `/bugbot/repo/update` endpoint to toggle Bugbot on or off for a repository:

```bash
curl -X POST https://api.cursor.com/bugbot/repo/update \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repoUrl": "https://github.com/your-org/your-repo",
    "enabled": true
  }'
```

**Parameters:**

- `repoUrl` (string, required): The full URL of the repository
- `enabled` (boolean, required): `true` to enable Bugbot, `false` to disable it

The dashboard UI may take a moment to reflect changes made through the API due to caching. The API response shows the current state in the database.

### Listing repositories

Use the `/bugbot/repos` endpoint to list all repositories with their Bugbot settings for your team:

```bash
curl https://api.cursor.com/bugbot/repos \
  -H "Authorization: Bearer $API_KEY"
```

The response includes each repository's enabled status, manual-only setting, and timestamps.

### Managing user access

Use the `/bugbot/user/update` endpoint to control which GitHub or GitLab users can use your team's Bugbot licenses. Enterprises use this to integrate Bugbot provisioning with internal access-request tools.

#### Prerequisites

Before calling this endpoint, enable an allowlist or blocklist mode in your [team Bugbot settings](https://cursor.com/dashboard?tab=bugbot):

- **Allowlist mode ("Only...")**: Only users on the list can use Bugbot
- **Blocklist mode ("Everyone but...")**: All users can use Bugbot except those on the list

If neither mode is enabled, the API returns an error.

#### Adding or removing a user

```bash
curl -X POST https://api.cursor.com/bugbot/user/update \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "octocat",
    "allow": true
  }'
```

**Parameters:**

- `username` (string, required): The GitHub or GitLab username (case-insensitive)
- `allow` (boolean, required): Whether to grant or revoke access

How `allow` behaves depends on the active mode:

| Mode      | `allow: true`                                | `allow: false`                             |
| --------- | -------------------------------------------- | ------------------------------------------ |
| Allowlist | Adds user to list (can use Bugbot)           | Removes user from list (cannot use Bugbot) |
| Blocklist | Removes user from blocklist (can use Bugbot) | Adds user to blocklist (cannot use Bugbot) |

**Response:**

```json
{
  "outcome": "success",
  "message": "Updated team-level allowlist for @octocat",
  "updatedTeamSettings": true,
  "updatedInstallations": 0
}
```

The allowlist is stored at the team level and applies across all GitHub and GitLab installations owned by that team. Usernames are normalized to lowercase.

#### Example: provisioning users through an internal tool

Connect this API to an internal access-request portal. When an employee requests Bugbot access, the portal calls the API to add them. When they leave or lose access, it calls the API to remove them.

**Grant access:**

```bash
curl -X POST https://api.cursor.com/bugbot/user/update \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"username": "employee-github-name", "allow": true}'
```

**Revoke access:**

```bash
curl -X POST https://api.cursor.com/bugbot/user/update \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"username": "employee-github-name", "allow": false}'
```

## Pricing

Bugbot offers two tiers: **Free** and **Pro**.

### Free tier

On Teams and Individual Cursor plans, every user gets a limited number of free PR reviews each month. For teams, each team member gets their own free reviews. When you reach the limit, reviews pause until your next billing cycle. You can upgrade anytime to a paid Bugbot plan for unlimited reviews.

### Pro tier

### Individuals

### Flat rate

$40 per month for unlimited Bugbot reviews on up to 200 PRs per month across all repositories.

### Getting started

Subscribe through your account settings.

### Teams

### Per-user billing

Teams pay $40 per user per month for unlimited reviews.

We count a user as someone who authored PRs reviewed by Bugbot in a month.

All licenses are relinquished at the start of each billing cycle, and will be assigned out on a first-come, first-served basis. If a user doesn't author any PRs reviewed by Bugbot in a month, the seat can be used by another user.

### Seat limits

Team admins can set maximum Bugbot seats per month to control costs.

### Getting started

Subscribe through your team dashboard to enable billing.

### Abuse guardrails

In order to prevent abuse, we have a pooled cap of 200 pull requests per month for every Bugbot license. If you need more than 200 pull requests per month, please contact us at [hi@cursor.com](mailto:hi@cursor.com) and we'll be happy to help you out.

For example, if your team has 100 users, your organization will initially be able to review 20,000 pull requests per month. If you reach that limit naturally, please reach out to us and we'll be happy to increase the limit.

## Troubleshooting

If Bugbot isn't working:

1. **Enable verbose mode** by commenting `cursor review verbose=true` or `bugbot run verbose=true` for detailed logs and request ID
2. **Check permissions** to verify Bugbot has repository access
3. **Verify installation** to confirm the GitHub app is installed and enabled

Include the request ID from verbose mode when reporting issues.

## FAQ

### Does Bugbot read GitHub PR comments?

Yes. Bugbot reads both top‑level and inline GitHub pull request comments and includes them as context during reviews. This helps avoid duplicate suggestions and allows Bugbot to build on prior feedback from reviewers.

### Is Bugbot privacy-mode compliant?

Yes, Bugbot follows the same privacy compliance as Cursor and processes data identically to other Cursor requests.

### What happens when I hit the free tier limit?

When you reach your monthly free tier limit, Bugbot reviews pause until your next billing cycle. You can start a 14‑day free Bugbot Pro trial for unlimited reviews (subject to standard abuse guardrails).

### How do I give Bugbot access to my GitLab or GitHub Enterprise Server instance?

Self-hosted instances require secure inbound access for PR reviews and outbound access for webhook notifications. Bugbot supports multiple networking configurations:

### 1. IP Whitelisting (Recommended)

Add these IP addresses to your instance's allowlist:

```text
184.73.225.134
3.209.66.12
52.44.113.131
```

**Best for:** Most self-hosted environments

**Security:** HTTPS encryption, optional IP allowlisting, service account access tokens

### 2. PrivateLink (AWS) or Private Service Connect (GCP)

Available with Enterprise Bugbot. Allow Cursor to access your instance over a private network connection. [Contact your Cursor representative](https://cursor.com/contact-sales?source=bugbot) for setup.

**Best for:** Instances behind a firewall on a private network in AWS, Azure, or GCP

**Security:** HTTPS encryption with optional mTLS, PrivateLink/Service Connect, VPC allowlisting, service account access tokens

**Drawbacks:** Only supports public clouds with private networking connections between VPCs

### 3. Reverse Proxy

Available with Enterprise Bugbot. Run a reverse proxy on-premises that establishes a long-lived websocket connection to Cursor's servers. Network requests are forwarded through to your instance. Requires no inbound network access. [Contact your Cursor representative](https://cursor.com/contact-sales?source=bugbot) for setup.

**Best for:** Environments without inbound network access

**Security:** HTTPS encryption, service account access tokens

**Drawbacks:** Introduces additional complexity, maintenance requirements, and potential security considerations compared to more direct connection methods


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/cookbook/code-review.md
# INDEX: 25/114
================================================================================

# Code Review with Cursor CLI

This tutorial shows you how to set up code review using Cursor CLI in GitHub Actions. The workflow will analyze pull requests, identify issues, and post feedback as comments.

For most users, we recommend using [Bugbot](https://cursor.com/docs/bugbot.md) instead. Bugbot
provides managed automated code review with no setup required. This CLI
approach is useful to explore capabilities and for advanced customization.

### Example: Full workflow file

**Example: `.github/workflows/cursor-code-review.yml`**

```yaml
name: Code Review

on:
pull_request:
types: [opened, synchronize, reopened, ready_for_review]

permissions:
pull-requests: write
contents: read
issues: write

jobs:
code-review:
runs-on: ubuntu-latest # Skip automated code review for draft PRs
if: github.event.pull_request.draft == false
steps: - name: Checkout repository
uses: actions/checkout@v4
with:
fetch-depth: 0
ref: ${{ github.event.pull_request.head.sha }}

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git identity
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Perform automated code review
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          MODEL: gpt-5.2
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BLOCKING_REVIEW: ${{ vars.BLOCKING_REVIEW || 'false' }}
        run: |
          agent --force --model "$MODEL" --output-format=text --print 'You are operating in a GitHub Actions runner performing automated code review. The gh CLI is available and authenticated via GH_TOKEN. You may comment on pull requests.

          Context:
          - Repo: ${{ github.repository }}
          - PR Number: ${{ github.event.pull_request.number }}
          - PR Head SHA: ${{ github.event.pull_request.head.sha }}
          - PR Base SHA: ${{ github.event.pull_request.base.sha }}
          - Blocking Review: ${{ env.BLOCKING_REVIEW }}

          Objectives:
          1) Re-check existing review comments and reply resolved when addressed.
          2) Review the current PR diff and flag only clear, high-severity issues.
          3) Leave very short inline comments (1-2 sentences) on changed lines only and a brief summary at the end.

          Procedure:
          - Get existing comments: gh pr view --json comments
          - Get diff: gh pr diff
          - Get changed files with patches to compute inline positions: gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/files --paginate --jq '.[] | {filename,patch}'
          - Compute exact inline anchors for each issue (file path + diff position). Comments MUST be placed inline on the changed line in the diff, not as top-level comments.
          - Detect prior top-level "no issues" style comments authored by this bot (match bodies like: "✅ no issues", "No issues found", "LGTM").
          - If CURRENT run finds issues and any prior "no issues" comments exist:
            - Prefer to remove them to avoid confusion:
              - Try deleting top-level issue comments via: gh api -X DELETE repos/${{ github.repository }}/issues/comments/<comment_id>
              - If deletion isn't possible, minimize them via GraphQL (minimizeComment) or edit to prefix "[Superseded by new findings]".
            - If neither delete nor minimize is possible, reply to that comment: "⚠️ Superseded: issues were found in newer commits".
          - If a previously reported issue appears fixed by nearby changes, reply: ✅ This issue appears to be resolved by the recent changes
          - Analyze ONLY for:
            - Null/undefined dereferences
            - Resource leaks (unclosed files or connections)
            - Injection (SQL/XSS)
            - Concurrency/race conditions
            - Missing error handling for critical operations
            - Obvious logic errors with incorrect behavior
            - Clear performance anti-patterns with measurable impact
            - Definitive security vulnerabilities
          - Avoid duplicates: skip if similar feedback already exists on or near the same lines.

          Commenting rules:
          - Max 10 inline comments total; prioritize the most critical issues
          - One issue per comment; place on the exact changed line
          - All issue comments MUST be inline (anchored to a file and line/position in the PR diff)
          - Natural tone, specific and actionable; do not mention automated or high-confidence
          - Use emojis: 🚨 Critical 🔒 Security ⚡ Performance ⚠️ Logic ✅ Resolved ✨ Improvement

          Submission:
          - If there are NO issues to report and an existing top-level comment indicating "no issues" already exists (e.g., "✅ no issues", "No issues found", "LGTM"), do NOT submit another comment. Skip submission to avoid redundancy.
          - If there are NO issues to report and NO prior "no issues" comment exists, submit one brief summary comment noting no issues.
          - If there ARE issues to report and a prior "no issues" comment exists, ensure that prior comment is deleted/minimized/marked as superseded before submitting the new review.
          - If there ARE issues to report, submit ONE review containing ONLY inline comments plus an optional concise summary body. Use the GitHub Reviews API to ensure comments are inline:
            - Build a JSON array of comments like: [{ "path": "<file>", "position": <diff_position>, "body": "..." }]
            - Submit via: gh api repos/${{ github.repository }}/pulls/${{ github.event.pull_request.number }}/reviews -f event=COMMENT -f body="$SUMMARY" -f comments='[$COMMENTS_JSON]'
          - Do NOT use: gh pr review --approve or --request-changes

          Blocking behavior:
          - If BLOCKING_REVIEW is true and any 🚨 or 🔒 issues were posted: echo "CRITICAL_ISSUES_FOUND=true" >> $GITHUB_ENV
          - Otherwise: echo "CRITICAL_ISSUES_FOUND=false" >> $GITHUB_ENV
          - Always set CRITICAL_ISSUES_FOUND at the end
          '

      - name: Check blocking review results
        if: env.BLOCKING_REVIEW == 'true'
        run: |
          echo "Checking for critical issues..."
          echo "CRITICAL_ISSUES_FOUND: ${CRITICAL_ISSUES_FOUND:-unset}"

          if [ "${CRITICAL_ISSUES_FOUND:-false}" = "true" ]; then
            echo "❌ Critical issues found and blocking review is enabled. Failing the workflow."
            exit 1
          else
            echo "✅ No blocking issues found."
          fi

```

![Automated code review in action showing inline comments on a pull request](/docs-static/images/cli/cookbook/code-review/comment.png)

## Configure authentication

[Set up your API key and repository secrets](https://cursor.com/docs/cli/github-actions.md#authentication) to authenticate Cursor CLI in GitHub Actions.

## Set up agent permissions

Create a configuration file to control what actions the agent can perform. This prevents unintended operations like pushing code or creating pull requests.

Create `.cursor/cli.json` in your repository root:

```json
{
  "permissions": {
    "deny": [
      "Shell(git push)",
      "Shell(gh pr create)",
      "Write(**)"
    ]
  }
}
```

This configuration allows the agent to read files and use the GitHub CLI for comments, but prevents it from making changes to your repository. See the [permissions reference](https://cursor.com/docs/cli/reference/permissions.md) for more configuration options.

## Build the GitHub Actions workflow

Now let's build the workflow step by step.

### Set up the workflow trigger

Create `.github/workflows/cursor-code-review.yml` and configure it to run on pull requests:

```yaml
name: Cursor Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

jobs:
  code-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write

    steps:
```

### Checkout the repository

Add the checkout step to access the pull request code:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 0
    ref: ${{ github.event.pull_request.head.sha }}
```

### Install Cursor CLI

Add the CLI installation step:

```yaml
- name: Install Cursor CLI
  run: |
    curl https://cursor.com/install -fsS | bash
    echo "$HOME/.cursor/bin" >> $GITHUB_PATH
```

For local testing on Windows, use PowerShell: `irm 'https://cursor.com/install?win32=true' | iex`

### Configure the review agent

Before implementing the full review step, let's understand the anatomy of our review prompt. This section outlines how we want the agent to behave:

**Objective**:
We want the agent to review the current PR diff and flag only clear, high-severity issues, then leave very short inline comments (1-2 sentences) on changed lines only with a brief summary at the end. This keeps the signal-to-noise ratio balanced.

**Format**:
We want comments that are short and to the point. We use emojis to make scanning comments easier, and we want a high-level summary of the full review at the end.

**Submission**:
When the review is done, we want the agent to include a short comment based on what was found during the review. The agent should submit one review containing inline comments plus a concise summary.

**Edge cases**:
We need to handle: - Existing comments being resolved: The agent should mark them as done when addressed - Avoid duplicates: The agent should skip commenting if similar feedback already exists on or near the same lines

**Final prompt**:
The complete prompt combines all these behavioral requirements to create focused, actionable feedback

Now let's implement the review agent step:

```yaml
- name: Perform code review
  env:
    CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
    GH_TOKEN: ${{ github.token }}
  run: |
    agent --force --model "$MODEL" --output-format=text --print "You are operating in a GitHub Actions runner performing automated code review. The gh CLI is available and authenticated via GH_TOKEN. You may comment on pull requests.

    Context:
    - Repo: ${{ github.repository }}
    - PR Number: ${{ github.event.pull_request.number }}
    - PR Head SHA: ${{ github.event.pull_request.head.sha }}
    - PR Base SHA: ${{ github.event.pull_request.base.sha }}

    Objectives:
    1) Re-check existing review comments and reply resolved when addressed
    2) Review the current PR diff and flag only clear, high-severity issues
    3) Leave very short inline comments (1-2 sentences) on changed lines only and a brief summary at the end

    Procedure:
    - Get existing comments: gh pr view --json comments
    - Get diff: gh pr diff
    - If a previously reported issue appears fixed by nearby changes, reply: ✅ This issue appears to be resolved by the recent changes
    - Avoid duplicates: skip if similar feedback already exists on or near the same lines

    Commenting rules:
    - Max 10 inline comments total; prioritize the most critical issues
    - One issue per comment; place on the exact changed line
    - Natural tone, specific and actionable; do not mention automated or high-confidence
    - Use emojis: 🚨 Critical 🔒 Security ⚡ Performance ⚠️ Logic ✅ Resolved ✨ Improvement

    Submission:
    - Submit one review containing inline comments plus a concise summary
    - Use only: gh pr review --comment
    - Do not use: gh pr review --approve or --request-changes"
```

```text
.
├── .cursor/
│   └── cli.json
├── .github/
│   └── workflows/
│       └── cursor-code-review.yml
```

## Test your reviewer

Create a test pull request to verify the workflow works and the agent posts review comments with emoji feedback.

![Pull request showing automated review comments with emojis and inline feedback on specific lines](/docs-static/images/cli/cookbook/code-review/github-actions.png)

## Next steps

You now have a working automated code review system. Consider these enhancements:

- Set up additional workflows for [fixing CI failures](https://cursor.com/docs/cli/cookbook/fix-ci.md)
- Configure different review levels for different branches
- Integrate with your team's existing code review process
- Customize the agent's behavior for different file types or directories

### Advanced: Blocking reviews

You can configure the workflow to fail if critical issues are found, preventing the pull request from being merged until addressed.

**Add blocking behavior to the prompt**

First, update your review agent step to include the `BLOCKING_REVIEW` environment variable and add this blocking behavior to the prompt:

```
Blocking behavior:
- If BLOCKING_REVIEW is true and any 🚨 or 🔒 issues were posted: echo "CRITICAL_ISSUES_FOUND=true" >> $GITHUB_ENV
- Otherwise: echo "CRITICAL_ISSUES_FOUND=false" >> $GITHUB_ENV
- Always set CRITICAL_ISSUES_FOUND at the end
```

**Add the blocking check step**

Then add this new step after your code review step:

```yaml
- name: Check blocking review results
  if: env.BLOCKING_REVIEW == 'true'
  run: |
    echo "Checking for critical issues..."
    echo "CRITICAL_ISSUES_FOUND: ${CRITICAL_ISSUES_FOUND:-unset}"

    if [ "${CRITICAL_ISSUES_FOUND:-false}" = "true" ]; then
      echo "❌ Critical issues found and blocking review is enabled. Failing the workflow."
      exit 1
    else
      echo "✅ No blocking issues found."
    fi
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/cookbook/fix-ci.md
# INDEX: 26/114
================================================================================

# Fix CI Failures with Cursor CLI

Fix CI failures using Cursor CLI in GitHub Actions. This workflow analyzes failures, makes targeted fixes, and creates a fix branch with a quick-create PR link.

This workflow monitors a specific workflow by name. Update the `workflows` list to match your actual CI workflow name.

**Example: `.github/workflows/fix-ci.yml`**

```yaml
name: Fix CI Failures

on:
  workflow_run:
    workflows: [Test]
    types: [completed]

permissions:
  contents: write
  pull-requests: write
  actions: read

jobs:
  attempt-fix:
    if: >-
      ${{ github.event.workflow_run.conclusion == 'failure' && github.event.workflow_run.name != 'Fix CI Failures' }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git identity
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Fix CI failure
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          MODEL: gpt-5.2
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BRANCH_PREFIX: ci-fix
        run: |
          agent -p "You are operating in a GitHub Actions runner.

          The GitHub CLI is available as `gh` and authenticated via `GH_TOKEN`. Git is available. You have write access to repository contents and can comment on pull requests, but you must not create or edit PRs directly.

          # Context:
          - Repo: ${{ github.repository }}
          - Owner: ${{ github.repository_owner }}
          - Workflow Run ID: ${{ github.event.workflow_run.id }}
          - Workflow Run URL: ${{ github.event.workflow_run.html_url }}
          - Fix Branch Prefix: ${{ env.BRANCH_PREFIX }}

          # Goal:
          - Implement an end-to-end CI fix flow driven by the failing PR, creating a separate persistent fix branch and proposing a quick-create PR back into the original PR's branch.

          # Requirements:
          1) Identify the PR associated with the failed workflow run and determine its base and head branches. Let HEAD_REF be the PR's head branch (the contributor/origin branch).
          2) Maintain a persistent fix branch for this PR head using the Fix Branch Prefix from Context. Create it if missing, update it otherwise, and push changes to origin.
          3) Attempt to resolve the CI failure by making minimal, targeted edits consistent with the repo's style. Keep changes scoped and safe.
          4) You do NOT have permission to create PRs. Instead, post or update a single natural-language PR comment (1–2 sentences) that briefly explains the CI fix and includes an inline compare link to quick-create a PR.

          # Inputs and conventions:
          - Use `gh api`, `gh run view`, `gh pr view`, `gh pr diff`, `gh pr list`, `gh run download`, and git commands as needed to discover the failing PR and branches.
          - Avoid duplicate comments; if a previous bot comment exists, update it instead of posting a new one.
          - If no actionable fix is possible, make no changes and post no comment.

          # Deliverables when updates occur:
          - Pushed commits to the persistent fix branch for this PR head.
          - A single natural-language PR comment on the original PR that includes the inline compare link above.
          " --force --model "$MODEL" --output-format=text
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/cookbook/secret-audit.md
# INDEX: 27/114
================================================================================

# Secret Audit with Cursor CLI

Audit your repository for security vulnerabilities and secrets exposure using Cursor CLI. This workflow scans for potential secrets, detects risky workflow patterns, and proposes security fixes.

**Example: `.github/workflows/secret-audit.yml`**

```yaml
name: Secrets Audit

on:
  schedule:
    - cron: "0 4 * * *"
  workflow_dispatch:

permissions:
  contents: write
  pull-requests: write
  actions: read

jobs:
  secrets-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git identity
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Scan and propose hardening
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          MODEL: gpt-5.2
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BRANCH_PREFIX: audit
        run: |
          agent -p "You are operating in a GitHub Actions runner.

          The GitHub CLI is available as `gh` and authenticated via `GH_TOKEN`. Git is available. You have write access to repository contents and can comment on pull requests, but you must not create or edit PRs directly.

          # Context:
          - Repo: ${{ github.repository }}
           - Hardening Branch Prefix: ${{ env.BRANCH_PREFIX }}

          # Goal:
          - Perform a repository secrets exposure and workflow hardening audit on a schedule, and propose minimal safe fixes.

          # Requirements:
          1) Scan for potential secrets in tracked files and recent history; support allowlist patterns if present (e.g., .gitleaks.toml).
          2) Detect risky workflow patterns: unpinned actions, overbroad permissions, unsafe pull_request_target usage, secrets in forked PR contexts, deprecated insecure commands, missing permissions blocks.
          3) Maintain a persistent branch for this run using the Hardening Branch Prefix from Context. Create it if missing, update it otherwise, and push changes to origin.
          4) Propose minimal edits: redact literals where safe, add ignore rules, pin actions to SHA, reduce permissions, add guardrails to workflows, and add a SECURITY_LOG.md summarizing changes and remediation guidance.
          5) Push to origin.
          6) If there is at least one open PR in the repo, post or update a single natural-language comment (1–2 sentences) on the most recently updated open PR that briefly explains the hardening changes and includes an inline compare link to quick-create a PR.
          7) Avoid duplicate comments; update an existing bot comment if present. If no changes or no open PRs, post nothing.

          # Inputs and conventions:
          - Use `gh` to list PRs and to post comments. Avoid duplicate comments.

          # Deliverables when updates occur:
           - Pushed commits to the persistent hardening branch for this run.
          - A single natural-language PR comment with the compare link above (only if an open PR exists).
          " --force --model "$MODEL" --output-format=text
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/cookbook/translate-keys.md
# INDEX: 28/114
================================================================================

# Translate Keys with Cursor CLI

Manage translation keys for internationalization using Cursor CLI. This workflow detects new or changed i18n keys in pull requests and fills missing translations without overwriting existing ones.

**Example: `.github/workflows/translate-keys.yml`**

```yaml
name: Translate Keys

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: write
  pull-requests: write

jobs:
  i18n:
    if: ${{ !startsWith(github.head_ref, 'translate/') }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git identity
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Propose i18n updates
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          MODEL: gpt-5.2
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BRANCH_PREFIX: translate
        run: |
          agent -p "You are operating in a GitHub Actions runner.

          The GitHub CLI is available as `gh` and authenticated via `GH_TOKEN`. Git is available. You have write access to repository contents and can comment on pull requests, but you must not create or edit PRs directly.

          # Context:
          - Repo: ${{ github.repository }}
          - PR Number: ${{ github.event.pull_request.number }}
          - Head Ref: ${{ github.head_ref }}
          - Translate Branch Prefix: ${{ env.BRANCH_PREFIX }}

          # Goal:
          - Detect i18n keys added or changed in the PR and fill only missing locales in message files. Never overwrite existing translations.

          # Requirements:
          1) Determine changed keys by inspecting the PR diff (source files and messages files).
          2) Compute missing keys per locale using the source/canonical locale as truth.
          3) Add entries only for missing keys. Preserve all existing values untouched.
          4) Validate JSON formatting and schemas.
          5) Maintain a persistent translate branch for this PR head using the Translate Branch Prefix from Context. Create it if missing, update it otherwise, and push changes to origin.
          6) Post or update a single PR comment on the original PR written in natural language (1–2 sentences) that briefly explains what was updated and why, and includes an inline compare link to quick-create a PR.
          7) Avoid duplicate comments; update a previous bot comment if present.
          8) If no changes are necessary, make no commits and post no comment.

          # Inputs and conventions:
          - Use `gh pr diff` and git history to detect changes.

          # Deliverables when updates occur:
          - Pushed commits to the persistent translate branch for this PR head.
          - A single natural-language PR comment on the original PR with the compare link above.
          " --force --model "$MODEL" --output-format=text
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/cookbook/update-docs.md
# INDEX: 29/114
================================================================================

# Update Docs with Cursor CLI

Update documentation using Cursor CLI in GitHub Actions. Two approaches: full agent autonomy or deterministic workflow with agent-only file modifications.

**Example: `.github/workflows/update-docs.yml`**

```yaml
name: Update Docs

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

permissions:
  contents: write
  pull-requests: write

jobs:
  docs:
    if: ${{ !startsWith(github.head_ref, 'docs/') }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install Cursor CLI
        run: |
          curl https://cursor.com/install -fsS | bash
          echo "$HOME/.cursor/bin" >> $GITHUB_PATH

      - name: Configure git
        run: |
          git config user.name "Cursor Agent"
          git config user.email "cursoragent@cursor.com"

      - name: Update docs
        env:
          MODEL: gpt-5.2
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          BRANCH_PREFIX: docs
        run: |
          agent -p "You are operating in a GitHub Actions runner.

          The GitHub CLI is available as `gh` and authenticated via `GH_TOKEN`. Git is available. You have write access to repository contents and can comment on pull requests, but you must not create or edit PRs.

          # Context:
          - Repo: ${{ github.repository }}
          - Owner: ${{ github.repository_owner }}
          - PR Number: ${{ github.event.pull_request.number }}
          - Base Ref: ${{ github.base_ref }}
          - Head Ref: ${{ github.head_ref }}
          - Docs Branch Prefix: ${{ env.BRANCH_PREFIX }}

          # Goal:
          - Implement an end-to-end docs update flow driven by incremental changes to the original PR.

          # Requirements:
          1) Determine what changed in the original PR and, if there have been multiple pushes, compute the incremental diffs since the last successful docs update.
          2) Update only the relevant docs based on those incremental changes.
          3) Maintain the persistent docs branch for this PR head using the Docs Branch Prefix from Context. Create it if missing, update it otherwise, and push changes to origin.
          4) You do NOT have permission to create PRs. Instead, post or update a single natural-language PR comment (1–2 sentences) that briefly explains the docs updates and includes an inline compare link to quick-create a PR

          # Inputs and conventions:
          - Use `gh pr diff` and git history to detect changes and derive incremental ranges since the last docs update.
          - Do not attempt to create or edit PRs directly. Use the compare link format above.
          - Keep changes minimal and consistent with repo style. If no doc updates are necessary, make no changes and post no comment.

          # Deliverables when updates occur:
          - Pushed commits to the persistent docs branch for this PR head.
          - A single natural-language PR comment on the original PR that includes the inline compare link above. Avoid posting duplicates; update a previous bot comment if present.
          " --force --model "$MODEL" --output-format=text
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/github-actions.md
# INDEX: 30/114
================================================================================

# GitHub Actions

Use Cursor CLI in GitHub Actions and other CI/CD systems to automate development tasks.

## GitHub Actions integration

Basic setup:

```yaml
- name: Install Cursor CLI
  run: |
    curl https://cursor.com/install -fsS | bash
    echo "$HOME/.cursor/bin" >> $GITHUB_PATH

- name: Run Cursor Agent
  env:
    CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
  run: |
    agent -p "Your prompt here" --model gpt-5.2
```

For Windows runners, use PowerShell: `irm 'https://cursor.com/install?win32=true' | iex`

## Cookbook examples

See our cookbook examples for practical workflows: [updating documentation](https://cursor.com/docs/cli/cookbook/update-docs.md) and [fixing CI issues](https://cursor.com/docs/cli/cookbook/fix-ci.md).

## Other CI systems

Use Cursor CLI in any CI/CD system with:

- **Shell script execution** (bash, zsh, etc.)
- **Environment variables** for API key configuration
- **Internet connectivity** to reach Cursor's API

## Autonomy levels

Choose your agent's autonomy level:

### Full autonomy approach

Give the agent complete control over git operations, API calls, and external interactions. Simpler setup, requires more trust.

**Example:** In our [Update Documentation](https://cursor.com/docs/cli/cookbook/update-docs.md) cookbook, the first workflow lets the agent:

- Analyze PR changes
- Create and manage git branches
- Commit and push changes
- Post comments on pull requests
- Handle all error scenarios

```yaml
- name: Update docs (full autonomy)
  run: |
    agent -p "You have full access to git, GitHub CLI, and PR operations. 
    Handle the entire docs update workflow including commits, pushes, and PR comments."
```

### Restricted autonomy approach

We recommend using this approach with **permission-based restrictions** for
production CI workflows. This gives you the best of both worlds: the agent can
intelligently handle complex analysis and file modifications while critical
operations remain deterministic and auditable.

Limit agent operations while handling critical steps in separate workflow steps. Better control and predictability.

**Example:** The second workflow in the same cookbook restricts the agent to only file modifications:

```yaml
- name: Generate docs updates (restricted)
  run: |
    agent -p "IMPORTANT: Do NOT create branches, commit, push, or post PR comments. 
    Only modify files in the working directory. A later workflow step handles publishing."

- name: Publish docs branch (deterministic)
  run: |
    # Deterministic git operations handled by CI
    git checkout -B "docs/${{ github.head_ref }}"
    git add -A
    git commit -m "docs: update for PR"
    git push origin "docs/${{ github.head_ref }}"

- name: Post PR comment (deterministic)
  run: |
    # Deterministic PR commenting handled by CI
    gh pr comment ${{ github.event.pull_request.number }} --body "Docs updated"
```

### Permission-based restrictions

Use [permission configurations](https://cursor.com/docs/cli/reference/permissions.md) to enforce restrictions at the CLI level:

```json
{
  "permissions": {
    "allow": [
      "Read(**/*.md)",
      "Write(docs/**/*)",
      "Shell(grep)",
      "Shell(find)"
    ],
    "deny": ["Shell(git)", "Shell(gh)", "Write(.env*)", "Write(package.json)"]
  }
}
```

## Authentication

### Generate your API key

First, [generate an API key](https://cursor.com/docs/cli/reference/authentication.md#api-key-authentication) from your Cursor dashboard.

### Configure repository secrets

Store your Cursor API key securely in your repository using the GitHub CLI:

```bash
# Repository secret
gh secret set CURSOR_API_KEY --repo OWNER/REPO --body "$CURSOR_API_KEY"

# Organization secret (all repos)
gh secret set CURSOR_API_KEY --org ORG --visibility all --body "$CURSOR_API_KEY"
```

Alternatively, use the GitHub UI: Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### Use in workflows

Set your `CURSOR_API_KEY` environment variable:

```yaml
env:
  CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/headless.md
# INDEX: 31/114
================================================================================

# Using Headless CLI

Use Cursor CLI in scripts and automation workflows for code analysis, generation, and refactoring tasks.

## How it works

Use [print mode](https://cursor.com/docs/cli/using.md#non-interactive-mode) (`-p, --print`) for non-interactive scripting and automation.

### File modification in scripts

Combine `--print` with `--force` (or `--yolo`) to modify files in scripts:

```bash
# Enable file modifications in print mode
agent -p --force "Refactor this code to use modern ES6+ syntax"

# Without --force, changes are only proposed, not applied
agent -p "Add JSDoc comments to this file"  # Won't modify files

# Batch processing with actual file changes
find src/ -name "*.js" | while read file; do
  agent -p --force "Add comprehensive JSDoc comments to $file"
done
```

The `--force` flag allows the agent to make direct file changes without
confirmation

## Setup

See [Installation](https://cursor.com/docs/cli/installation.md) and [Authentication](https://cursor.com/docs/cli/reference/authentication.md) for complete setup details.

```bash
# Install Cursor CLI (macOS, Linux, WSL)
curl https://cursor.com/install -fsS | bash

# Install Cursor CLI (Windows PowerShell)
irm 'https://cursor.com/install?win32=true' | iex

# Set API key for scripts
export CURSOR_API_KEY=your_api_key_here
agent -p "Analyze this code"
```

## Example scripts

Use different output formats for different script needs. See [Output format](https://cursor.com/docs/cli/reference/output-format.md) for details.

### Searching the codebase

By default, `--print` uses `text` format for clean, final-answer-only responses:

```bash
#!/bin/bash
# Simple codebase question - uses text format by default

agent -p "What does this codebase do?"
```

### Automated code review

Use `--output-format json` for structured analysis:

```bash
#!/bin/bash
# simple-code-review.sh - Basic code review script

echo "Starting code review..."

# Review recent changes
agent -p --force --output-format text \
  "Review the recent code changes and provide feedback on:
  - Code quality and readability
  - Potential bugs or issues
  - Security considerations
  - Best practices compliance

  Provide specific suggestions for improvement and write to review.txt"

if [ $? -eq 0 ]; then
  echo "✅ Code review completed successfully"
else
  echo "❌ Code review failed"
  exit 1
fi
```

### Real-time progress tracking

Use `--output-format stream-json` for message-level progress tracking, or add `--stream-partial-output` for incremental streaming of deltas:

```bash
#!/bin/bash
# stream-progress.sh - Track progress in real-time

echo "🚀 Starting stream processing..."

# Track progress in real-time
accumulated_text=""
tool_count=0
start_time=$(date +%s)

agent -p --force --output-format stream-json --stream-partial-output \
  "Analyze this project structure and create a summary report in analysis.txt" | \
  while IFS= read -r line; do
    
    type=$(echo "$line" | jq -r '.type // empty')
    subtype=$(echo "$line" | jq -r '.subtype // empty')
    
    case "$type" in
      "system")
        if [ "$subtype" = "init" ]; then
          model=$(echo "$line" | jq -r '.model // "unknown"')
          echo "🤖 Using model: $model"
        fi
        ;;
        
      "assistant")
        # Accumulate incremental text deltas for smooth progress
        content=$(echo "$line" | jq -r '.message.content[0].text // empty')
        accumulated_text="$accumulated_text$content"
        
        # Show live progress (updates with each character delta)
        printf "\r📝 Generating: %d chars" ${#accumulated_text}
        ;;

      "tool_call")
        if [ "$subtype" = "started" ]; then
          tool_count=$((tool_count + 1))

          # Extract tool information
          if echo "$line" | jq -e '.tool_call.writeToolCall' > /dev/null 2>&1; then
            path=$(echo "$line" | jq -r '.tool_call.writeToolCall.args.path // "unknown"')
            echo -e "\n🔧 Tool #$tool_count: Creating $path"
          elif echo "$line" | jq -e '.tool_call.readToolCall' > /dev/null 2>&1; then
            path=$(echo "$line" | jq -r '.tool_call.readToolCall.args.path // "unknown"')
            echo -e "\n📖 Tool #$tool_count: Reading $path"
          fi

        elif [ "$subtype" = "completed" ]; then
          # Extract and show tool results
          if echo "$line" | jq -e '.tool_call.writeToolCall.result.success' > /dev/null 2>&1; then
            lines=$(echo "$line" | jq -r '.tool_call.writeToolCall.result.success.linesCreated // 0')
            size=$(echo "$line" | jq -r '.tool_call.writeToolCall.result.success.fileSize // 0')
            echo "   ✅ Created $lines lines ($size bytes)"
          elif echo "$line" | jq -e '.tool_call.readToolCall.result.success' > /dev/null 2>&1; then
            lines=$(echo "$line" | jq -r '.tool_call.readToolCall.result.success.totalLines // 0')
            echo "   ✅ Read $lines lines"
          fi
        fi
        ;;

      "result")
        duration=$(echo "$line" | jq -r '.duration_ms // 0')
        end_time=$(date +%s)
        total_time=$((end_time - start_time))

        echo -e "\n\n🎯 Completed in ${duration}ms (${total_time}s total)"
        echo "📊 Final stats: $tool_count tools, ${#accumulated_text} chars generated"
        ;;
    esac
  done
```

## Working with images

To send images, media files, or other binary data to the agent, include file paths in your prompts. The agent can read any files through tool calling, including images, videos, and other formats.

### Including file paths in prompts

Simply reference file paths in your prompt text. The agent will automatically read the files when needed:

```bash
# Analyze an image
agent -p "Analyze this image and describe what you see: ./screenshot.png"

# Process multiple media files
agent -p "Compare these two images and identify differences: ./before.png ./after.png"

# Combine file paths with text instructions
agent -p "Review the code in src/app.ts and the design mockup in designs/homepage.png. Suggest improvements to match the design."
```

### How it works

When you include file paths in your prompt:

1. The agent receives your prompt with the file path references
2. The agent uses tool calling to read the files automatically
3. Images are handled transparently
4. You can reference files using relative or absolute paths

### Example: Image analysis script

```bash
#!/bin/bash
# analyze-image.sh - Analyze images using the headless CLI

IMAGE_PATH="./screenshots/ui-mockup.png"

agent -p --output-format json \
  "Analyze this image and provide a detailed description: $IMAGE_PATH" | \
  jq -r '.result'
```

### Example: Batch media processing

```bash
#!/bin/bash
# process-media.sh - Process multiple media files

for image in images/*.png; do
  echo "Processing $image..."
  agent -p --output-format text \
    "Describe what's in this image: $image" > "${image%.png}.description.txt"
done
```

File paths can be relative to the current working directory or absolute paths.
The agent will read files through tool calls, so ensure the files exist and
are accessible from where you run the command.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/installation.md
# INDEX: 32/114
================================================================================

# Installation

## Installation

### macOS, Linux and Windows (WSL)

Install Cursor CLI with a single command:

```bash
curl https://cursor.com/install -fsS | bash
```

### Windows (native)

Install Cursor CLI on Windows using PowerShell:

```powershell
irm 'https://cursor.com/install?win32=true' | iex
```

### Verification

After installation, verify that Cursor CLI is working correctly:

```bash
agent --version
```

## Post-installation setup

1. **Add \~/.local/bin to your PATH:**

   For bash:

   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```

   For zsh:

   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

2. **Start using Cursor Agent:**
   ```bash
   agent
   ```

## Updates

Cursor CLI will try to auto-update by default to ensure you always have the latest version.

To manually update Cursor CLI to the latest version:

```bash
agent update
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/mcp.md
# INDEX: 33/114
================================================================================

# MCP

## Overview

The Cursor CLI supports [Model Context Protocol (MCP)](https://cursor.com/docs/context/mcp.md) servers, allowing you to connect external tools and data sources to `agent`. **MCP in the CLI uses the same configuration as the editor** - any MCP servers you've configured will work with both.

### Learn about MCP

New to MCP? Read the complete guide on configuration, authentication, and
available servers

## CLI commands

Use the `agent mcp` command to manage MCP servers

### List configured servers

View all configured MCP servers and their current status:

```bash
agent mcp list
```

This opens an interactive menu where you can browse, enable, and configure MCP servers at a glance. The list shows:

- Server names and identifiers
- Connection status (connected/disconnected)
- Configuration source (project or global)
- Transport method (stdio, HTTP, SSE)

You can also use the `/mcp list` slash command in interactive mode for the same interface.

### List available tools

View tools provided by a specific MCP server:

```bash
agent mcp list-tools <identifier>
```

This displays:

- Tool names and descriptions
- Required and optional parameters
- Parameter types and constraints

### Login to MCP server

Authenticate with an MCP server configured in your `mcp.json`:

```bash
agent mcp login <identifier>
```

The CLI uses a streamlined login flow with automatic callback handling. The agent gets access to authenticated MCPs immediately after login completes.

### Enable MCP server

Enable an MCP server:

```bash
agent mcp enable <identifier>
```

You can also use the `/mcp enable <name>` slash command in interactive mode.

### Disable MCP server

Disable an MCP server:

```bash
agent mcp disable <identifier>
```

You can also use the `/mcp disable <name>` slash command in interactive mode.

MCP server names with spaces are supported in all `/mcp` commands.

## Using MCP with Agent

Once you have MCP servers configured (see the [main MCP guide](https://cursor.com/docs/context/mcp.md) for setup), `agent` automatically discovers and uses available tools when relevant to your requests.

```bash
# Check what MCP servers are available
agent mcp list

# See what tools a specific server provides
agent mcp list-tools playwright

# Use agent - it automatically uses MCP tools when helpful
agent -p "Navigate to google.com and take a screenshot of the search page"

# Auto-approve all MCP servers (skip approval prompts)
agent --approve-mcps "query my database for recent errors"
```

The CLI follows the same configuration precedence as the editor (project → global → nested), automatically discovering configurations from parent directories.

## Related

### MCP Overview

Complete MCP guide: setup, configuration, and authentication

### Available MCP Tools

Browse pre-built MCP servers you can use


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/overview.md
# INDEX: 34/114
================================================================================

# Cursor CLI

Cursor CLI lets you interact with AI agents directly from your terminal to write, review, and modify code. Whether you prefer an interactive terminal interface or print automation for scripts and CI pipelines, the CLI provides powerful coding assistance right where you work.

## Getting started

```bash
# Install (macOS, Linux, WSL)
curl https://cursor.com/install -fsS | bash

# Install (Windows PowerShell)
irm 'https://cursor.com/install?win32=true' | iex

# Run interactive session
agent
```

[Media](https://ptht05hbb1ssoooe.public.blob.vercel-storage.com/assets/uploads/plan-mode.mp4)

## Interactive mode

Start a conversational session with the agent to describe your goals, review proposed changes, and approve commands:

```bash
# Start interactive session
agent

# Start with initial prompt
agent "refactor the auth module to use JWT tokens"
```

## Modes

The CLI supports the same modes as the editor. Switch between modes using slash commands, keyboard shortcuts, or the `--mode` flag.

| Mode      | Description                                                  | Shortcut                                    |
| :-------- | :----------------------------------------------------------- | :------------------------------------------ |
| **Agent** | Full access to all tools for complex coding tasks            | Default (no `--mode` value needed)          |
| **Plan**  | Design your approach before coding with clarifying questions | Shift+Tab, `/plan`, `--plan`, `--mode=plan` |
| **Ask**   | Read-only exploration without making changes                 | `/ask`, `--mode=ask`                        |

See [Agent Modes](https://cursor.com/docs/agent/modes.md) for details on each mode.

## Non-interactive mode

Use print mode for non-interactive scenarios like scripts, CI pipelines, or automation:

```bash
# Run with specific prompt and model
agent -p "find and fix performance issues" --model "gpt-5.2"

# Use with git changes included for review
agent -p "review these changes for security issues" --output-format text
```

## Cloud Agent handoff

Push your conversation to a [Cloud Agent](https://cursor.com/docs/cloud-agent.md) to continue running while you're away. Prepend `&` to any message, or start a session directly in cloud mode with `-c` / `--cloud`:

```bash
# Start in cloud mode
agent -c "refactor the auth module and add comprehensive tests"

# Send a task to Cloud Agent mid-conversation
& refactor the auth module and add comprehensive tests
```

Pick up your Cloud Agent tasks on web or mobile at [cursor.com/agents](https://cursor.com/agents).

## Sessions

Resume previous conversations to maintain context across multiple interactions:

```bash
# List all previous chats
agent ls

# Resume latest conversation
agent resume

# Continue the previous session
agent --continue

# Resume specific conversation
agent --resume="chat-id-here"
```

## Sandbox controls

Configure command execution settings with `/sandbox` or the `--sandbox <mode>` flag (`enabled` or `disabled`). Toggle sandbox mode on or off and control network access through an interactive menu. Settings persist across sessions.

[Media](https://ptht05hbb1ssoooe.public.blob.vercel-storage.com/assets/uploads/sandox.mp4)

## Max Mode

Toggle [Max Mode](https://cursor.com/docs/context/max-mode.md) on models that support it using `/max-mode [on|off]`.

[Media](https://ptht05hbb1ssoooe.public.blob.vercel-storage.com/assets/uploads/max-mode.mp4)

## Sudo password prompting

Run commands requiring elevated privileges without leaving the CLI. When a command needs `sudo`, Cursor displays a secure, masked password prompt. Your password flows directly to `sudo` via a secure IPC channel; the AI model never sees it.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/authentication.md
# INDEX: 35/114
================================================================================

# Authentication

Cursor CLI supports two authentication methods: browser-based login (recommended) and API keys.

## Browser authentication (recommended)

Use the browser flow for the easiest authentication experience:

```bash
# Log in using browser flow
agent login

# Check authentication status
agent status

# Log out and clear stored authentication
agent logout
```

The login command will open your default browser and prompt you to authenticate with your Cursor account. Once completed, your credentials are securely stored locally.

## API key authentication

For automation, scripts, or CI/CD environments, use API key authentication:

### Step 1: Generate an API key

Generate an API key in your Cursor dashboard under Integrations > User API Keys.

### Step 2: Set the API key

You can provide the API key in two ways:

**Option 1: Environment variable (recommended)**

```bash
export CURSOR_API_KEY=your_api_key_here
agent "implement user authentication"
```

**Option 2: Command line flag**

```bash
agent --api-key your_api_key_here "implement user authentication"
```

## Authentication status

Check your current authentication status:

```bash
agent status
```

This command will display:

- Whether you're authenticated
- Your account information
- Current endpoint configuration

## Troubleshooting

- **"Not authenticated" errors:** Run `agent login` or ensure your API key is correctly set
- **SSL certificate errors:** Use the `--insecure` flag for development environments
- **Endpoint issues:** Use the `--endpoint` flag to specify a custom API endpoint


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/configuration.md
# INDEX: 36/114
================================================================================

# Configuration

Configure the Agent CLI using the `cli-config.json` file.

## File location

| Type    | Platform    | Path                                       |
| :------ | :---------- | :----------------------------------------- |
| Global  | macOS/Linux | `~/.cursor/cli-config.json`                |
| Global  | Windows     | `$env:USERPROFILE\.cursor\cli-config.json` |
| Project | All         | `<project>/.cursor/cli.json`               |

Only permissions can be configured at the project level. All other CLI
settings must be set globally.

Override with environment variables:

- **`CURSOR_CONFIG_DIR`**: custom directory path
- **`XDG_CONFIG_HOME`** (Linux/BSD): uses `$XDG_CONFIG_HOME/cursor/cli-config.json`

## Schema

### Required fields

| Field               | Type      | Description                                                                                    |
| :------------------ | :-------- | :--------------------------------------------------------------------------------------------- |
| `version`           | number    | Config schema version (current: `1`)                                                           |
| `editor.vimMode`    | boolean   | Enable Vim keybindings (default: `false`)                                                      |
| `permissions.allow` | string\[] | Permitted operations (see [Permissions](https://cursor.com/docs/cli/reference/permissions.md)) |
| `permissions.deny`  | string\[] | Forbidden operations (see [Permissions](https://cursor.com/docs/cli/reference/permissions.md)) |

### Optional fields

| Field                                 | Type    | Description                                                             |
| :------------------------------------ | :------ | :---------------------------------------------------------------------- |
| `model`                               | object  | Selected model configuration                                            |
| `hasChangedDefaultModel`              | boolean | CLI-managed model override flag                                         |
| `network.useHttp1ForAgent`            | boolean | Use HTTP/1.1 instead of HTTP/2 for agent connections (default: `false`) |
| `attribution.attributeCommitsToAgent` | boolean | Add `Co-authored-by: Cursor` trailer to Agent commits (default: `true`) |
| `attribution.attributePRsToAgent`     | boolean | Add "Made with Cursor" footer to Agent PRs (default: `true`)            |

## Examples

### Minimal config

```json
{
  "version": 1,
  "editor": { "vimMode": false },
  "permissions": { "allow": ["Shell(ls)"], "deny": [] }
}
```

### Enable Vim mode

```json
{
  "version": 1,
  "editor": { "vimMode": true },
  "permissions": { "allow": ["Shell(ls)"], "deny": [] }
}
```

### Configure permissions

```json
{
  "version": 1,
  "editor": { "vimMode": false },
  "permissions": {
    "allow": ["Shell(ls)", "Shell(echo)"],
    "deny": ["Shell(rm)"]
  }
}
```

See [Permissions](https://cursor.com/docs/cli/reference/permissions.md) for available permission types and examples.

## Troubleshooting

**Config errors**: Move the file aside and restart:

```bash
mv ~/.cursor/cli-config.json ~/.cursor/cli-config.json.bad
```

**Changes don't persist**: Ensure valid JSON and write permissions. Some fields are CLI-managed and may be overwritten.

## Notes

- Pure JSON format (no comments)
- CLI performs self-repair for missing fields
- Corrupted files are backed up as `.bad` and recreated
- Permission entries are exact strings (see [Permissions](https://cursor.com/docs/cli/reference/permissions.md) for details)

## Models

You can select a model for the CLI using the `/model` slash command.

```bash
/model auto
/model gpt-5.2
/model sonnet-4.5-thinking
```

See the [Slash commands](https://cursor.com/docs/cli/reference/slash-commands.md) docs for other commands.

## Proxy configuration

If your network routes traffic through a proxy server, configure the CLI using environment variables and the config file.

### Environment variables

Set these environment variables before running the CLI:

```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
export NODE_USE_ENV_PROXY=1
```

If your proxy performs SSL inspection (man-in-the-middle), also trust your organization's CA certificate:

```bash
export NODE_EXTRA_CA_CERTS=/path/to/corporate-ca-cert.pem
```

### HTTP/1.1 fallback

Some enterprise proxies (like Zscaler) don't support HTTP/2 bidirectional streaming. Enable HTTP/1.1 mode in your config:

```json
{
  "version": 1,
  "editor": { "vimMode": false },
  "permissions": { "allow": [], "deny": [] },
  "network": {
    "useHttp1ForAgent": true
  }
}
```

This switches agent connections to HTTP/1.1 with Server-Sent Events (SSE), which works with most corporate proxies.

See [Network Configuration](https://cursor.com/docs/enterprise/network-configuration.md) for proxy testing commands and troubleshooting.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/output-format.md
# INDEX: 37/114
================================================================================

# Output Format

The Cursor Agent CLI provides multiple output formats with the `--output-format` option when combined with `--print`. These formats include structured formats for programmatic use (`json`, `stream-json`) and a simplified text format for human-readable output (`text`).

The default `--output-format` is `text`. This option is only valid when
printing (`--print`) or when print mode is inferred (non-TTY stdout or piped
stdin).

## JSON format

The `json` output format emits a single JSON object (followed by a newline) when the run completes successfully. Deltas and tool events are not emitted; text is aggregated into the final result.

On failure, the process exits with a non-zero code and writes an error message to stderr. No well-formed JSON object is emitted in failure cases.

### Success response

When successful, the CLI outputs a JSON object with the following structure:

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "duration_ms": 1234,
  "duration_api_ms": 1234,
  "result": "<full assistant text>",
  "session_id": "<uuid>",
  "request_id": "<optional request id>"
}
```

| Field             | Description                                                         |
| ----------------- | ------------------------------------------------------------------- |
| `type`            | Always `"result"` for terminal results                              |
| `subtype`         | Always `"success"` for successful completions                       |
| `is_error`        | Always `false` for successful responses                             |
| `duration_ms`     | Total execution time in milliseconds                                |
| `duration_api_ms` | API request time in milliseconds (currently equal to `duration_ms`) |
| `result`          | Complete assistant response text (concatenation of all text deltas) |
| `session_id`      | Unique session identifier                                           |
| `request_id`      | Optional request identifier (may be omitted)                        |

## Stream JSON format

The `stream-json` output format emits newline-delimited JSON (NDJSON). Each line contains a single JSON object representing an event during execution. This format aggregates text deltas and outputs **one line per assistant message** (the complete message between tool calls).

The stream ends with a terminal `result` event on success. On failure, the process exits with a non-zero code and the stream may end early without a terminal event; an error message is written to stderr.

**Streaming partial output:** For real-time character-level streaming, use `--stream-partial-output` with `--output-format stream-json`. This emits text as it's generated in small chunks, with the same event structure but multiple `assistant` events per message. Concatenate all `message.content[].text` values to reconstruct the complete response.

### Event types

#### System initialization

Emitted once at the beginning of each session:

```json
{
  "type": "system",
  "subtype": "init",
  "apiKeySource": "env|flag|login",
  "cwd": "/absolute/path",
  "session_id": "<uuid>",
  "model": "<model display name>",
  "permissionMode": "default"
}
```

Future fields like `tools` and `mcp_servers` may be added to this event.

#### User message

Contains the user's input prompt:

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [{ "type": "text", "text": "<prompt>" }]
  },
  "session_id": "<uuid>"
}
```

#### Assistant message

Emitted once per complete assistant message (between tool calls). Each event contains the full text of that message segment:

```json
{
  "type": "assistant",
  "message": {
    "role": "assistant",
    "content": [{ "type": "text", "text": "<complete message text>" }]
  },
  "session_id": "<uuid>"
}
```

#### Tool call events

Tool calls are tracked with start and completion events:

**Tool call started:**

```json
{
  "type": "tool_call",
  "subtype": "started",
  "call_id": "<string id>",
  "tool_call": {
    "readToolCall": {
      "args": { "path": "file.txt" }
    }
  },
  "session_id": "<uuid>"
}
```

**Tool call completed:**

```json
{
  "type": "tool_call",
  "subtype": "completed",
  "call_id": "<string id>",
  "tool_call": {
    "readToolCall": {
      "args": { "path": "file.txt" },
      "result": {
        "success": {
          "content": "file contents...",
          "isEmpty": false,
          "exceededLimit": false,
          "totalLines": 54,
          "totalChars": 1254
        }
      }
    }
  },
  "session_id": "<uuid>"
}
```

#### Tool call types

**Read file tool:**

- **Started**: `tool_call.readToolCall.args` contains `{ "path": "file.txt" }`
- **Completed**: `tool_call.readToolCall.result.success` contains file metadata and content

**Write file tool:**

- **Started**: `tool_call.writeToolCall.args` contains `{ "path": "file.txt", "fileText": "content...", "toolCallId": "id" }`
- **Completed**: `tool_call.writeToolCall.result.success` contains `{ "path": "/absolute/path", "linesCreated": 19, "fileSize": 942 }`

**Other tools:**

- May use `tool_call.function` structure with `{ "name": "tool_name", "arguments": "..." }`

#### Terminal result

The final event emitted on successful completion:

```json
{
  "type": "result",
  "subtype": "success",
  "duration_ms": 1234,
  "duration_api_ms": 1234,
  "is_error": false,
  "result": "<full assistant text>",
  "session_id": "<uuid>",
  "request_id": "<optional request id>"
}
```

### Example sequence

Here's a representative NDJSON sequence showing the typical flow of events:

```json
{"type":"system","subtype":"init","apiKeySource":"login","cwd":"/Users/user/project","session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff","model":"Claude 4 Sonnet","permissionMode":"default"}
{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Read README.md and create a summary"}]},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"I'll read the README.md file"}]},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"tool_call","subtype":"started","call_id":"toolu_vrtx_01NnjaR886UcE8whekg2MGJd","tool_call":{"readToolCall":{"args":{"path":"README.md"}}},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"tool_call","subtype":"completed","call_id":"toolu_vrtx_01NnjaR886UcE8whekg2MGJd","tool_call":{"readToolCall":{"args":{"path":"README.md"},"result":{"success":{"content":"# Project\n\nThis is a sample project...","isEmpty":false,"exceededLimit":false,"totalLines":54,"totalChars":1254}}}},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Based on the README, I'll create a summary"}]},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"tool_call","subtype":"started","call_id":"toolu_vrtx_01Q3VHVnWFSKygaRPT7WDxrv","tool_call":{"writeToolCall":{"args":{"path":"summary.txt","fileText":"# README Summary\n\nThis project contains...","toolCallId":"toolu_vrtx_01Q3VHVnWFSKygaRPT7WDxrv"}}},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"tool_call","subtype":"completed","call_id":"toolu_vrtx_01Q3VHVnWFSKygaRPT7WDxrv","tool_call":{"writeToolCall":{"args":{"path":"summary.txt","fileText":"# README Summary\n\nThis project contains...","toolCallId":"toolu_vrtx_01Q3VHVnWFSKygaRPT7WDxrv"},"result":{"success":{"path":"/Users/user/project/summary.txt","linesCreated":19,"fileSize":942}}}},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"Done! I've created the summary in summary.txt"}]},"session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff"}
{"type":"result","subtype":"success","duration_ms":5234,"duration_api_ms":5234,"is_error":false,"result":"I'll read the README.md fileBased on the README, I'll create a summaryDone! I've created the summary in summary.txt","session_id":"c6b62c6f-7ead-4fd6-9922-e952131177ff","request_id":"10e11780-df2f-45dc-a1ff-4540af32e9c0"}
```

## Text format

The `text` output format provides only the final assistant message without any intermediate progress updates or tool call summaries. This is the cleanest output format for scripts that only need the agent's final response.

This format is ideal when you want just the answer or final message from the agent, without any progress indicators or tool execution details.

### Example output

```
The command to move this branch onto main is `git rebase --onto main HEAD~3`.
```

Only the final assistant message (after the last tool call) is output, with no tool call summaries or intermediate text.

## Implementation notes

- Each event is emitted as a single line terminated by `\n`
- `thinking` events are suppressed in print mode and will not appear in any output format
- Field additions may occur over time in a backward-compatible way (consumers should ignore unknown fields)
- The `json` format waits for completion before outputting results
- The `stream-json` format outputs complete agent messages
- The `--stream-partial-output` flag provides real-time text deltas for character-level streaming (only works with `stream-json` format)
- Tool call IDs can be used to correlate start/completion events
- Session IDs remain consistent throughout a single agent execution


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/parameters.md
# INDEX: 38/114
================================================================================

# Parameters

## Global options

Global options can be used with any command:

| Option                     | Description                                                                                                          |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `-v, --version`            | Output the version number                                                                                            |
| `--api-key <key>`          | API key for authentication (can also use `CURSOR_API_KEY` env var)                                                   |
| `-H, --header <header>`    | Add custom header to agent requests (format: `Name: Value`, can be used multiple times)                              |
| `-p, --print`              | Print responses to console (for scripts or non-interactive use). Has access to all tools, including write and shell. |
| `--output-format <format>` | Output format (only works with `--print`): `text`, `json`, or `stream-json` (default: `text`)                        |
| `--stream-partial-output`  | Stream partial output as individual text deltas (only works with `--print` and `stream-json` format)                 |
| `-c, --cloud`              | Start in cloud mode                                                                                                  |
| `--resume [chatId]`        | Resume a chat session                                                                                                |
| `--continue`               | Continue the previous session (alias for `--resume=-1`)                                                              |
| `--model <model>`          | Model to use                                                                                                         |
| `--mode <mode>`            | Set agent mode: `plan` or `ask` (agent is the default when no mode is specified)                                     |
| `--plan`                   | Start in plan mode (shorthand for `--mode=plan`)                                                                     |
| `--list-models`            | List all available models                                                                                            |
| `-f, --force`              | Force allow commands unless explicitly denied                                                                        |
| `--yolo`                   | Alias for `--force`                                                                                                  |
| `--sandbox <mode>`         | Set sandbox mode: `enabled` or `disabled`                                                                            |
| `--approve-mcps`           | Automatically approve all MCP servers                                                                                |
| `--trust`                  | Trust the workspace without prompting (headless mode only)                                                           |
| `--workspace <path>`       | Workspace directory to use                                                                                           |
| `-h, --help`               | Display help for command                                                                                             |

## Commands

| Command                       | Description                               | Usage                               |
| ----------------------------- | ----------------------------------------- | ----------------------------------- |
| `agent`                       | Start in agent mode (the default)         | `agent agent`                       |
| `login`                       | Authenticate with Cursor                  | `agent login`                       |
| `logout`                      | Sign out and clear stored authentication  | `agent logout`                      |
| `status` \| `whoami`          | Check authentication status               | `agent status`                      |
| `about`                       | Display version, system, and account info | `agent about`                       |
| `models`                      | List all available models                 | `agent models`                      |
| `mcp`                         | Manage MCP servers                        | `agent mcp`                         |
| `update`                      | Update Cursor Agent to the latest version | `agent update`                      |
| `ls`                          | List previous chat sessions               | `agent ls`                          |
| `resume`                      | Resume the latest chat session            | `agent resume`                      |
| `create-chat`                 | Create a new empty chat and return its ID | `agent create-chat`                 |
| `generate-rule` \| `rule`     | Generate a new Cursor rule interactively  | `agent generate-rule`               |
| `install-shell-integration`   | Install shell integration to `~/.zshrc`   | `agent install-shell-integration`   |
| `uninstall-shell-integration` | Remove shell integration from `~/.zshrc`  | `agent uninstall-shell-integration` |
| `help [command]`              | Display help for command                  | `agent help [command]`              |

When no command is specified, Cursor Agent starts in interactive agent mode by
default.

## MCP

Manage MCP servers configured for Cursor Agent.

| Subcommand                | Description                                                      | Usage                               |
| ------------------------- | ---------------------------------------------------------------- | ----------------------------------- |
| `login <identifier>`      | Authenticate with an MCP server configured in `.cursor/mcp.json` | `agent mcp login <identifier>`      |
| `list`                    | List configured MCP servers and their status                     | `agent mcp list`                    |
| `list-tools <identifier>` | List available tools and their argument names for a specific MCP | `agent mcp list-tools <identifier>` |
| `enable <identifier>`     | Enable an MCP server                                             | `agent mcp enable <identifier>`     |
| `disable <identifier>`    | Disable an MCP server                                            | `agent mcp disable <identifier>`    |

All MCP commands support `-h, --help` for command-specific help.

## Arguments

When starting in chat mode (default behavior), you can provide an initial prompt:

**Arguments:**

- `prompt` — Initial prompt for the agent

## Getting help

All commands support the global `-h, --help` option to display command-specific help.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/permissions.md
# INDEX: 39/114
================================================================================

# Permissions

Configure what the agent is allowed to do using permission tokens in your CLI configuration. Permissions are set in `~/.cursor/cli-config.json` (global) or `<project>/.cursor/cli.json` (project-specific).

## Permission types

### Shell commands

**Format:** `Shell(commandBase)`

Controls access to shell commands. The `commandBase` is the first token in the command line. Supports glob patterns and an optional `command:args` syntax for finer control.

| Example         | Description                                        |
| --------------- | -------------------------------------------------- |
| `Shell(ls)`     | Allow running `ls` commands                        |
| `Shell(git)`    | Allow any `git` subcommand                         |
| `Shell(npm)`    | Allow npm package manager commands                 |
| `Shell(curl:*)` | Allow `curl` with any arguments                    |
| `Shell(rm)`     | Deny destructive file removal (commonly in `deny`) |

### File reads

**Format:** `Read(pathOrGlob)`

Controls read access to files and directories. Supports glob patterns.

| Example             | Description                             |
| ------------------- | --------------------------------------- |
| `Read(src/**/*.ts)` | Allow reading TypeScript files in `src` |
| `Read(**/*.md)`     | Allow reading markdown files anywhere   |
| `Read(.env*)`       | Deny reading environment files          |
| `Read(/etc/passwd)` | Deny reading system files               |

### File writes

**Format:** `Write(pathOrGlob)`

Controls write access to files and directories. Supports glob patterns. When using in print mode, `--force` is required to write files.

| Example               | Description                           |
| --------------------- | ------------------------------------- |
| `Write(src/**)`       | Allow writing to any file under `src` |
| `Write(package.json)` | Allow modifying package.json          |
| `Write(**/*.key)`     | Deny writing private key files        |
| `Write(**/.env*)`     | Deny writing environment files        |

### Web fetch

**Format:** `WebFetch(domainOrPattern)`

Controls which domains the agent can fetch when using the web fetch tool (e.g., to retrieve documentation or web pages). Without an allowlist entry, each fetch prompts for approval. Add domains to `allow` to auto-approve fetches from trusted sources.

| Example                     | Description                                       |
| --------------------------- | ------------------------------------------------- |
| `WebFetch(docs.github.com)` | Allow fetches from `docs.github.com`              |
| `WebFetch(*.example.com)`   | Allow fetches from any subdomain of `example.com` |
| `WebFetch(*)`               | Allow fetches from any domain (use with caution)  |

**Domain pattern matching:**

- `*` matches all domains
- `*.example.com` matches subdomains (e.g., `docs.example.com`, `api.example.com`)
- `example.com` matches that exact domain only

### MCP tools

**Format:** `Mcp(server:tool)`

Controls which MCP (Model Context Protocol) tools the agent can run. Use `server` (from `mcp.json`) and `tool` name, with `*` for wildcards.

| Example          | Description                                 |
| ---------------- | ------------------------------------------- |
| `Mcp(datadog:*)` | Allow all tools from the Datadog MCP server |
| `Mcp(*:search)`  | Allow any server's `search` tool            |
| `Mcp(*:*)`       | Allow all MCP tools (use with caution)      |

## Configuration

Add permissions to the `permissions` object in your CLI configuration file:

```json
{
  "permissions": {
    "allow": [
      "Shell(ls)",
      "Shell(git)",
      "Read(src/**/*.ts)",
      "Write(package.json)",
      "WebFetch(docs.github.com)",
      "WebFetch(*.github.com)",
      "Mcp(datadog:*)"
    ],
    "deny": [
      "Shell(rm)",
      "Read(.env*)",
      "Write(**/*.key)",
      "WebFetch(malicious-site.com)"
    ]
  }
}
```

## Pattern matching

- Glob patterns use `**`, `*`, and `?` wildcards
- Relative paths are scoped to the current workspace
- Absolute paths can target files outside the project
- Deny rules take precedence over allow rules
- Use `command:args` (e.g., `curl:*`) to match both command and arguments with globs


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/slash-commands.md
# INDEX: 40/114
================================================================================

# Slash commands

| Command                 | Description                                                                                                         |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `/plan`                 | Switch to Plan mode to design your approach before coding                                                           |
| `/ask`                  | Switch to Ask mode for read-only exploration                                                                        |
| `/model <model>`        | Set or list models                                                                                                  |
| `/auto-run [state]`     | Toggle auto-run (default) or set \[on\|off\|status]                                                                 |
| `/sandbox`              | Configure sandbox mode and network access settings                                                                  |
| `/max-mode [on\|off]`   | Toggle max mode on models that support it                                                                           |
| `/new-chat`             | Start a new chat session                                                                                            |
| `/vim`                  | Toggle Vim keys                                                                                                     |
| `/help [command]`       | Show help (/help \[cmd])                                                                                            |
| `/feedback <message>`   | Share feedback with the team                                                                                        |
| `/resume <chat>`        | Resume a previous chat by folder name                                                                               |
| `/usage`                | View Cursor streaks and usage stats                                                                                 |
| `/about`                | Show environment and CLI setup details                                                                              |
| `/max-mode [on\|off]`   | Toggle max mode on models that support it                                                                           |
| `/copy-request-id`      | Copy last request ID to clipboard                                                                                   |
| `/copy-conversation-id` | Copy conversation ID to clipboard                                                                                   |
| `/logout`               | Sign out from Cursor                                                                                                |
| `/quit`                 | Exit                                                                                                                |
| `/setup-terminal`       | Auto-configure terminal keybindings (see [Terminal Setup](https://cursor.com/docs/cli/reference/terminal-setup.md)) |
| `/mcp list`             | Browse, enable, and configure MCP servers                                                                           |
| `/mcp enable <name>`    | Enable an MCP server                                                                                                |
| `/mcp disable <name>`   | Disable an MCP server                                                                                               |
| `/rules`                | Create new rules or edit existing rules                                                                             |
| `/commands`             | Create new commands or edit existing commands                                                                       |
| `/compress`             | Summarize conversation to free context space                                                                        |


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/reference/terminal-setup.md
# INDEX: 41/114
================================================================================

# Terminal Setup

Configure your terminal for the best Cursor CLI experience. This guide covers keybindings for multi-line input, Vim mode, and theme synchronization.

## Quick start

If Shift+Enter doesn't work for newlines in your terminal, run `/setup-terminal` for guidance on configuring alternatives:

```bash
/setup-terminal
```

This command detects your terminal and provides instructions for configuring Option+Enter as an alternative way to insert newlines.

## Universal options

These methods work in **all terminals**, including tmux, screen, and SSH sessions:

| Method | Description                                              |
| :----- | :------------------------------------------------------- |
| +Enter | Type a backslash, then press Enter to insert a newline   |
| Ctrl+J | Standard control character for newline (ASCII line feed) |

If you're in tmux or having trouble with other keybindings, Ctrl+J is the most reliable option.

## Terminal support

### Native Shift+Enter support

These terminals support Shift+Enter for newlines out of the box:

- **iTerm2** (macOS)
- **Ghostty**
- **Kitty**
- **Warp**
- **Zed** (integrated terminal)

### Requires `/setup-terminal`

These terminals need `/setup-terminal` to configure Option+Enter for newlines:

- **Apple Terminal** (macOS)
- **Alacritty**
- **VS Code** (integrated terminal)

### Terminal multiplexers

**tmux** and **screen** intercept Shift+Enter before it reaches applications. Use the universal options instead:

- Ctrl+J — Works reliably in all multiplexer sessions
- +Enter — Also works universally

You can configure your outer terminal (e.g., iTerm2) for Shift+Enter, but the keybinding won't pass through tmux. Use the universal options for the most consistent experience.

## Vim mode

Enable Vim keybindings for navigation and editing in the CLI input area.

### Toggle with slash command

```bash
/vim
```

This toggles Vim mode on or off for the current session and saves the preference.

### Configure in settings

Add to your `~/.cursor/cli-config.json`:

```json
{
  "version": 1,
  "editor": { "vimMode": true },
  "permissions": { "allow": [], "deny": [] }
}
```

### Modes

Vim mode uses modal editing:

- **Normal mode** — Navigate and execute commands (default when Vim mode is enabled)
- **Insert mode** — Type text normally

Press Esc to return to normal mode from insert mode.

### Navigation

| Key     | Description                                           |
| :------ | :---------------------------------------------------- |
| h, l    | Move left / right                                     |
| j, k    | Move down / up                                        |
| w, b    | Next / previous word                                  |
| e       | End of word                                           |
| W, B, E | Same as above, but for WORD (non-whitespace sequence) |
| 0, $    | Start / end of line                                   |

### Editing

| Key        | Description                                 |
| :--------- | :------------------------------------------ |
| x          | Delete character under cursor               |
| X          | Delete character before cursor              |
| d + motion | Delete range (e.g., `dw` deletes word)      |
| dd         | Delete entire line                          |
| D          | Delete to end of line                       |
| s          | Substitute character (delete + insert mode) |
| S, cc      | Change entire line                          |
| C          | Change to end of line                       |

### Entering insert mode

| Key | Description             |
| :-- | :---------------------- |
| i   | Insert at cursor        |
| a   | Insert after cursor     |
| I   | Insert at start of line |
| A   | Insert at end of line   |
| o   | Open new line below     |
| O   | Open new line above     |

### Counts

Prefix commands with a number to repeat them. For example, `3w` moves forward 3 words, `2dd` deletes 2 lines.

Vim mode affects the input area only. Navigation through chat history and other UI elements uses standard keybindings.

## Terminal theme

Cursor CLI automatically detects your terminal's color scheme and adapts its appearance.

### Automatic detection

The CLI queries your terminal for its background color using standard escape sequences. Most modern terminals support this:

- **Dark terminals** → CLI uses dark theme
- **Light terminals** → CLI uses light theme

### Terminals with automatic detection

These terminals report their color scheme correctly:

- iTerm2
- Ghostty
- Kitty
- Alacritty
- Apple Terminal
- Windows Terminal
- VS Code integrated terminal

### Forcing a theme

If automatic detection doesn't work, you can override it with an environment variable:

```bash
# Force dark theme
export COLORFGBG="15;0"

# Force light theme
export COLORFGBG="0;15"
```

Add this to your shell profile (`.bashrc`, `.zshrc`, etc.) to make it permanent.

### Troubleshooting theme issues

**Colors look wrong:**

- Ensure your terminal supports 256 colors or true color
- Check that `TERM` is set correctly (e.g., `xterm-256color`)
- Try setting `COLORFGBG` explicitly

**tmux users:**

- Add to your `.tmux.conf` to pass through color detection:
  ```
  set -g default-terminal "tmux-256color"
  set -ag terminal-overrides ",xterm-256color:RGB"
  ```
- Restart tmux after making changes

## Manual configuration

If `/setup-terminal` doesn't work for your terminal, you can manually configure keybindings.

### Option+Enter for newlines

Option+Enter sends a special escape sequence that Cursor CLI recognizes as a newline. Configure your terminal to send `\x1b\r` (Escape followed by carriage return) when Option+Enter is pressed.

**iTerm2:**

1. Open **Preferences** → **Profiles** → **Keys** → **Key Mappings**
2. Click **+** to add a new mapping
3. Set **Keyboard Shortcut** to Option+Enter
4. Set **Action** to "Send Escape Sequence"
5. Enter `\r` as the escape sequence

**Alacritty:**

Add to your `alacritty.toml`:

```toml
[keyboard]
bindings = [
  { key = "Return", mods = "Alt", chars = "\u001b\r" }
]
```

**Kitty:**

Add to your `kitty.conf`:

```
map alt+enter send_text all \x1b\r
```

### Shift+Enter

Shift+Enter support depends on your terminal correctly reporting the key modifier. Most modern terminals handle this automatically, but some may need configuration.

**VS Code terminal:**

VS Code's integrated terminal may not pass Shift+Enter correctly. Add to your `keybindings.json`:

```json
{
  "key": "shift+enter",
  "command": "workbench.action.terminal.sendSequence",
  "args": { "text": "\u001b[13;2u" },
  "when": "terminalFocus"
}
```

## Troubleshooting

**Keybindings not working:**

- Verify your terminal is detecting the keys correctly using `cat` or `showkey`
- Check if a terminal multiplexer (tmux/screen) is intercepting the keys
- Use Ctrl+J as a reliable fallback

**tmux users:**

- Shift+Enter and Option+Enter won't work through tmux
- Use Ctrl+J or +Enter instead
- These universal options work everywhere, including nested tmux sessions

**SSH sessions:**

- Remote terminal capabilities depend on your local terminal emulator
- Ctrl+J works reliably over SSH
- +Enter is another reliable option

## Summary

| Keybinding   | Works in                          | Notes                                                      |
| :----------- | :-------------------------------- | :--------------------------------------------------------- |
| Ctrl+J       | All terminals                     | Most reliable, works everywhere                            |
| +Enter       | All terminals                     | Universal alternative                                      |
| Shift+Enter  | iTerm2, Ghostty, Kitty, Warp, Zed | Native support, no config needed                           |
| Option+Enter | After `/setup-terminal`           | Newline alternative for Apple Terminal, Alacritty, VS Code |


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/shell-mode.md
# INDEX: 42/114
================================================================================

# Shell Mode

Shell Mode runs shell commands directly from the CLI without leaving your conversation. Use it for quick, non-interactive commands with safety checks and output displayed in the conversation.

[Media](/docs-static/images/cli/shell-mode/cli-shell-mode.mp4)

## Command execution

Commands run in your login shell (`$SHELL`) with the CLI's working directory and environment. Chain commands to run in other directories:

```bash
cd subdir && npm test
```

## Output

Large outputs are truncated automatically and long-running processes timeout to maintain performance.

## Limitations

- Commands timeout after 30 seconds
- Long-running processes, servers, and interactive prompts are not supported
- Use short, non-interactive commands for best results

## Permissions

Commands are checked against your permissions and team settings before execution. See [Permissions](https://cursor.com/docs/cli/reference/permissions.md) for detailed configuration.

Admin policies may block certain commands, and commands with redirection cannot be allowlisted inline.

## Usage guidelines

Shell Mode works well for status checks, quick builds, file operations, and environment inspection.

Avoid long-running servers, interactive applications, and commands requiring input.

Each command runs independently - use `cd <dir> && ...` to run commands in other directories.

## Troubleshooting

- If a command hangs, cancel with Ctrl+C and add non-interactive flags
- When prompted for permissions, approve once or add to allowlist with Tab
- For truncated output, use Ctrl+O to expand
- To run in different directories, use `cd <dir> && ...` since changes don't persist
- Shell Mode supports zsh and bash from your `$SHELL` variable

## FAQ

### Does \`cd\` persist across runs?

No. Each command runs independently. Use `cd <dir> && ...` to run commands in different directories.

### Can I change the timeout?

No. Commands are limited to 30 seconds and this is not configurable.

### Where are permissions configured?

Permissions are managed by CLI and team configuration. Use the decision banner to add commands to allowlists.

### How do I exit Shell Mode?

Press Escape when the input is empty, Backspace/Delete on empty input, or Ctrl+C to clear and exit.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cli/using.md
# INDEX: 43/114
================================================================================

# Using Agent in CLI

## Modes

The CLI supports the same [modes](https://cursor.com/docs/agent/modes.md) as the editor. Switch modes using slash commands or the `--mode` flag.

### Plan mode

Use Plan mode to design your approach before coding. The agent asks clarifying questions to refine your plan.

- Press Shift+Tab to rotate to Plan mode
- Use `/plan` to switch to Plan mode
- Start with `--plan` or `--mode=plan` flag

### Ask mode

Use Ask mode to explore code without making changes. The agent searches your codebase and provides answers without editing files.

- Use `/ask` to switch to Ask mode
- Start with `--mode=ask` flag

## Prompting

Stating intent clearly is recommended for the best results. For example, you can use the prompt "do not write any code" to ensure that the agent won't edit any files. This is generally helpful when planning tasks before implementing them.

Agent has tools for file operations, searching, running shell commands, and web access.

## MCP

Agent supports [MCP (Model Context Protocol)](https://cursor.com/docs/context/mcp/directory.md) for extended functionality and integrations. The CLI will automatically detect and respect your `mcp.json` configuration file, enabling the same MCP servers and tools that you've configured for the editor.

## Rules

The CLI agent supports the same [rules system](https://cursor.com/docs/context/rules.md) as the editor. You can create rules in the `.cursor/rules` directory to provide context and guidance to the agent. These rules will be automatically loaded and applied based on their configuration, allowing you to customize the agent's behavior for different parts of your project or specific file types.

The CLI also reads `AGENTS.md` and `CLAUDE.md` at the project root (if
present) and applies them as rules alongside `.cursor/rules`.

## Working with Agent

### Navigation

Previous messages can be accessed using arrow up (ArrowUp) where you can cycle through them.

### Input shortcuts

- Shift+Tab — Rotate between modes (Agent, Plan, Ask)
- Shift+Enter — Insert a newline instead of submitting, making it easier to write multi-line prompts.
- Ctrl+D — Exit the CLI. Follows standard shell behavior, requiring a double-press to exit.
- Ctrl+J or +Enter — Universal alternatives for inserting newlines that work in all terminals.

Shift+Enter works in iTerm2, Ghostty, Kitty, Warp, and Zed. For tmux users, use Ctrl+J instead. See [Terminal Setup](https://cursor.com/docs/cli/reference/terminal-setup.md) for configuration options and troubleshooting.

### Review

Review changes with Ctrl+R. Press i to add follow-up instructions. Use ArrowUp/ArrowDown to scroll, and ArrowLeft/ArrowRight to switch files.

### Selecting context

Select files and folders to include in context with @. Free up space in the context window by running `/compress`. See [Summarization](https://cursor.com/docs/agent/chat/summarization.md) for details.

## Cloud Agent handoff

Push your conversation to a [Cloud Agent](https://cursor.com/docs/cloud-agent.md) and let it keep running while you're away. Start a session in cloud mode with `-c` / `--cloud`, or prepend `&` to any message to send it to the cloud. Pick it back up on web or mobile at [cursor.com/agents](https://cursor.com/agents).

```bash
# Start in cloud mode
agent -c "refactor the auth module and add comprehensive tests"

# Send a task to Cloud Agent mid-conversation
& refactor the auth module and add comprehensive tests
```

## History

Continue from an existing thread with `--resume [thread id]` to load prior context.

To resume the most recent conversation, use `agent resume`, `--continue`, or the `/resume` slash command.

You can also run `agent ls` to see a list of previous conversations.

## Command approval

Before running terminal commands, CLI will ask you to approve (y) or reject (n) execution.

## Non-interactive mode

Use `-p` or `--print` to run Agent in non-interactive mode. This will print the response to the console.

With non-interactive mode, you can invoke Agent in a non-interactive way. This allows you to integrate it in scripts, CI pipelines, etc.

You can combine this with `--output-format` to control how the output is formatted. For example, use `--output-format json` for structured output that's easier to parse in scripts, or `--output-format text` for plain text output of the agent's final response.

Cursor has full write access in non-interactive mode.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent.md
# INDEX: 44/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/api/endpoints.md
# INDEX: 45/114
================================================================================

# Cloud Agents API

The Cloud Agents API lets you programmatically launch and manage cloud agents that work on your repositories.

- The Cloud Agents API uses [Basic Authentication](https://cursor.com/docs/api.md#basic-authentication). You can obtain an API key from your [Cursor Dashboard](https://cursor.com/settings).
- For details on authentication methods, rate limits, and best practices, see the [API Overview](https://cursor.com/docs/api.md).
- View the full [OpenAPI specification](/docs-static/cloud-agents-openapi.yaml) for detailed schemas and examples.
- MCP (Model Context Protocol) is not yet supported by the Cloud Agents API.

## Endpoints

### List Agents

/v0/agents

List all cloud agents for the authenticated user.

#### Query Parameters

`limit` number (optional)

Number of cloud agents to return. Default: 20, Max: 100

`cursor` string (optional)

Pagination cursor from the previous response

`prUrl` string (optional)

Filter agents by pull request URL

```bash
curl --request GET \
  --url https://api.cursor.com/v0/agents \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "agents": [
    {
      "id": "bc_abc123",
      "name": "Add README Documentation",
      "status": "FINISHED",
      "source": {
        "repository": "https://github.com/your-org/your-repo",
        "ref": "main"
      },
      "target": {
        "branchName": "cursor/add-readme-1234",
        "url": "https://cursor.com/agents?id=bc_abc123",
        "prUrl": "https://github.com/your-org/your-repo/pull/1234",
        "autoCreatePr": false,
        "openAsCursorGithubApp": false,
        "skipReviewerRequest": false
      },
      "summary": "Added README.md with installation instructions and usage examples",
      "createdAt": "2024-01-15T10:30:00Z"
    },
    {
      "id": "bc_def456",
      "name": "Fix authentication bug",
      "status": "RUNNING",
      "source": {
        "repository": "https://github.com/your-org/your-repo",
        "ref": "main"
      },
      "target": {
        "branchName": "cursor/fix-auth-5678",
        "url": "https://cursor.com/agents?id=bc_def456",
        "autoCreatePr": true,
        "openAsCursorGithubApp": true,
        "skipReviewerRequest": false
      },
      "createdAt": "2024-01-15T11:45:00Z"
    }
  ],
  "nextCursor": "bc_ghi789"
}
```

### Agent Status

/v0/agents/

Retrieve the current status and results of a cloud agent.

#### Path Parameters

`id` string

Unique identifier for the cloud agent (e.g., bc\_abc123)

```bash
curl --request GET \
  --url https://api.cursor.com/v0/agents/bc_abc123 \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "id": "bc_abc123",
  "name": "Add README Documentation",
  "status": "FINISHED",
  "source": {
    "repository": "https://github.com/your-org/your-repo",
    "ref": "main"
  },
  "target": {
    "branchName": "cursor/add-readme-1234",
    "url": "https://cursor.com/agents?id=bc_abc123",
    "prUrl": "https://github.com/your-org/your-repo/pull/1234",
    "autoCreatePr": false,
    "openAsCursorGithubApp": false,
    "skipReviewerRequest": false
  },
  "summary": "Added README.md with installation instructions and usage examples",
  "createdAt": "2024-01-15T10:30:00Z"
}
```

### Agent Conversation

/v0/agents//conversation

Retrieve the conversation history of a cloud agent, including all user prompts and assistant responses.

If the cloud agent has been deleted, you cannot access the conversation.

#### Path Parameters

`id` string

Unique identifier for the cloud agent (e.g., `bc_abc123`)

```bash
curl --request GET \
  --url https://api.cursor.com/v0/agents/bc_abc123/conversation \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "id": "bc_abc123",
  "messages": [
    {
      "id": "msg_001",
      "type": "user_message",
      "text": "Add a README.md file with installation instructions"
    },
    {
      "id": "msg_002",
      "type": "assistant_message",
      "text": "I'll help you create a comprehensive README.md file with installation instructions. Let me start by analyzing your project structure..."
    },
    {
      "id": "msg_003",
      "type": "assistant_message",
      "text": "I've created a README.md file with the following sections:\n- Project overview\n- Installation instructions\n- Usage examples\n- Configuration options"
    },
    {
      "id": "msg_004",
      "type": "user_message",
      "text": "Also add a section about troubleshooting"
    },
    {
      "id": "msg_005",
      "type": "assistant_message",
      "text": "I've added a troubleshooting section to the README with common issues and solutions."
    }
  ]
}
```

### Launch an Agent

/v0/agents

Start a new cloud agent to work on your repository.

#### Request Body

`prompt` object (required)

The task prompt for the agent, including optional images

`prompt.text` string (required)

The instruction text for the agent

`prompt.images` array (optional)

Array of image objects with base64 data and dimensions (max 5)

`model` string (optional)

The LLM to use (e.g., claude-4-sonnet). If not provided, we'll pick the most appropriate model.

`source` object (required)

Repository source information

`source.repository` string (required unless prUrl is provided)

GitHub repository URL (e.g., [https://github.com/your-org/your-repo](https://github.com/your-org/your-repo))

`source.ref` string (optional)

Git ref (branch name, tag, or commit hash) to use as the base branch

`source.prUrl` string (optional)

GitHub pull request URL. When provided, the agent works on this PR's repository and branches. If set, repository and ref are ignored.

`target` object (optional)

Target configuration for the agent

`target.autoCreatePr` boolean (optional)

Whether to automatically create a pull request when the agent completes. Default: false

`target.openAsCursorGithubApp` boolean (optional)

Whether to open the pull request as the Cursor GitHub App instead of as the user. Only applies if autoCreatePr is true. Default: false

`target.skipReviewerRequest` boolean (optional)

Whether to skip adding the user as a reviewer to the pull request. Only applies if autoCreatePr is true and the PR is opened as the Cursor GitHub App. Default: false

`target.branchName` string (optional)

Custom branch name for the agent to create

`target.autoBranch` boolean (optional, default: true)

Whether to create a new branch (true) or push to the PR's existing head branch (false). Only applies when source.prUrl is provided.

`webhook` object (optional)

[Webhook](https://cursor.com/docs/cloud-agent/api/webhooks.md) configuration for status change notifications

`webhook.url` string (required if webhook provided)

URL to receive [webhook](https://cursor.com/docs/cloud-agent/api/webhooks.md) notifications about agent status changes

`webhook.secret` string (optional)

Secret key for [webhook](https://cursor.com/docs/cloud-agent/api/webhooks.md) payload verification (minimum 32 characters)

```bash
curl --request POST \
  --url https://api.cursor.com/v0/agents \
  -u YOUR_API_KEY: \
  --header 'Content-Type: application/json' \
  --data '{
  "prompt": {
    "text": "Add a README.md file with installation instructions",
    "images": [
      {
        "data": "iVBORw0KGgoAAAANSUhEUgAA...",
        "dimension": {
          "width": 1024,
          "height": 768
        }
      }
    ]
  },
  "source": {
    "repository": "https://github.com/your-org/your-repo",
    "ref": "main"
  },
  "target": {
    "autoCreatePr": true,
    "branchName": "feature/add-readme"
  }
}'
```

**Response:**

```json
{
  "id": "bc_abc123",
  "name": "Add README Documentation",
  "status": "CREATING",
  "source": {
    "repository": "https://github.com/your-org/your-repo",
    "ref": "main"
  },
  "target": {
    "branchName": "feature/add-readme",
    "url": "https://cursor.com/agents?id=bc_abc123",
    "prUrl": "https://github.com/your-org/your-repo/pull/123",
    "autoCreatePr": true,
    "openAsCursorGithubApp": false,
    "skipReviewerRequest": false
  },
  "createdAt": "2024-01-15T10:30:00Z"
}
```

### Add Follow-up

/v0/agents//followup

Add a follow-up instruction to an existing cloud agent.

#### Path Parameters

`id` string

Unique identifier for the cloud agent (e.g., bc\_abc123)

#### Request Body

`prompt` object (required)

The follow-up prompt for the agent, including optional images

`prompt.text` string (required)

The follow-up instruction text for the agent

`prompt.images` array (optional)

Array of image objects with base64 data and dimensions (max 5)

```bash
curl --request POST \
  --url https://api.cursor.com/v0/agents/bc_abc123/followup \
  -u YOUR_API_KEY: \
  --header 'Content-Type: application/json' \
  --data '{
  "prompt": {
    "text": "Also add a section about troubleshooting",
    "images": [
      {
        "data": "iVBORw0KGgoAAAANSUhEUgAA...",
        "dimension": {
          "width": 1024,
          "height": 768
        }
      }
    ]
  }
}'
```

**Response:**

```json
{
  "id": "bc_abc123"
}
```

### Stop an Agent

/v0/agents//stop

Stop a running cloud agent. This pauses the agent's execution without deleting it.

You can only stop agents that are currently running. If you send a follow-up prompt to a stopped agent, it will start running again.

#### Path Parameters

`id` string

Unique identifier for the cloud agent (e.g., `bc_abc123`)

```bash
curl --request POST \
  --url https://api.cursor.com/v0/agents/bc_abc123/stop \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "id": "bc_abc123"
}
```

### Delete an Agent

/v0/agents/

Delete a cloud agent. This action is permanent and cannot be undone.

#### Path Parameters

`id` string

Unique identifier for the cloud agent (e.g., `bc_abc123`)

```bash
curl --request DELETE \
  --url https://api.cursor.com/v0/agents/bc_abc123 \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "id": "bc_abc123"
}
```

### API Key Info

/v0/me

Retrieve information about the API key being used for authentication.

```bash
curl --request GET \
  --url https://api.cursor.com/v0/me \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "apiKeyName": "Production API Key",
  "createdAt": "2024-01-15T10:30:00Z",
  "userEmail": "developer@example.com"
}
```

### List Models

/v0/models

Retrieve a list of recommended models for cloud agents.

We recommend having an "Auto" option where you don't provide a model name to the creation endpoint, and we will pick the most appropriate model.

```bash
curl --request GET \
  --url https://api.cursor.com/v0/models \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "models": [
    "claude-4-sonnet-thinking",
    "gpt-5.2",
    "claude-4.5-sonnet-thinking"
  ]
}
```

### List GitHub Repositories

/v0/repositories

Retrieve a list of GitHub repositories accessible to the authenticated user.

**This endpoint has very strict rate limits.**

Limit requests to **1 / user / minute**, and **30 / user / hour.**

This request can take tens of seconds to respond for users with access to many repositories.

Make sure to handle this information not being available gracefully.

```bash
curl --request GET \
  --url https://api.cursor.com/v0/repositories \
  -u YOUR_API_KEY:
```

**Response:**

```json
{
  "repositories": [
    {
      "owner": "your-org",
      "name": "your-repo",
      "repository": "https://github.com/your-org/your-repo"
    },
    {
      "owner": "your-org",
      "name": "another-repo",
      "repository": "https://github.com/your-org/another-repo"
    },
    {
      "owner": "your-username",
      "name": "personal-project",
      "repository": "https://github.com/your-username/personal-project"
    }
  ]
}
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/best-practices.md
# INDEX: 46/114
================================================================================

# Best Practices

Use these recommendations to get more reliable Cloud Agent runs.

## Set up the environment first

Use [Cloud agent setup](https://cursor.com/docs/cloud-agent/setup.md) so that Cursor has its environment configured. Like a human developer, Cursor does better work if its environment is set up correctly.

## Ensure the agent can access what it needs

Before running a Cloud Agent, verify these prerequisites:

- **Secrets**: Make sure the agent has access to required secrets (API keys, database credentials, etc.) through the [Secrets tab](https://cursor.com/dashboard?tab=cloud-agents) in your dashboard.
- **Egress controls**: If you have [network access](https://cursor.com/docs/cloud-agent/network-access.md) restrictions enabled, ensure all URLs your local development requires are whitelisted.
- **Local testability**: Your repo should be set up to run well locally without requiring external services that cannot be reached from a VM. If it is hard for a human developer to test locally, it will also be hard for an agent.

## Use skills and agents.md to configure your agent

If the cloud agent is having difficulty testing its changes, we recommend using [skills](https://cursor.com/docs/context/skills.md) and agents.md to configure your agent.

Think of the agent as a smart, but low-context human developer. The best way to make sure it does the right thing is to give it the context it needs to understand what to do.

For example, at Cursor our agents.md lists tips for running and debugging the most commonly used microservices in our mono-repo. We also have lots of skills about how to test and debug key services, each with clear instructions on when to use the skill.

The skills contain in-depth details, such as how to debug a specific microservice or how to set up a third-party dependency when needed for testing.

## Give the agent the tools it needs

We have often found that agents are limited by the tools they have access to. We recommend using MCP and creating custom tools so that the agent has access to the same systems a human developer would.

## Mold the tools to the agent

It is important to create tools that the agent is good at using. We recommend creating tools, and iterating based on observations of how the agent uses them.

For example, at Cursor we have created a custom CLI for the model to run micro-services in our codebase. We found that when running custom dev commands, e.g. from a package.json file, some models would forget arguments, or agents would get distracted by noisy build logs which human developers knew to ignore.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/capabilities.md
# INDEX: 47/114
================================================================================

# Capabilities

## Computer use

Each cloud agent runs in its own isolated VM with a full desktop environment. Agents can use a mouse and keyboard to control the desktop and browser, allowing them to interact with the software they build like a human developer.

This means agents can start dev servers, open the app in a browser, click through UI flows, and verify their changes work before pushing a PR. Read more in the [announcement blog post](/blog/agent-computer-use).

## Demos

Agents create artifacts such as screenshots, videos, and log references to demonstrate their work. These artifacts are attached to the PR so you can quickly validate changes without checking out the branch locally.

## MCP tools

Cloud agents can use [MCP (Model Context Protocol)](https://cursor.com/docs/context/mcp.md) servers configured for your team. This gives agents access to external tools and data sources like databases, APIs, and third-party services during their runs.

Add and enable MCP servers through the MCP dropdown in [cursor.com/agents](https://cursor.com/agents).

### Custom MCP servers

You can add custom MCP servers using either **HTTP** or **stdio** transport. SSE and `mcp-remote` are not supported.

MCP configurations are encrypted at rest. Sensitive fields are redacted and cannot be read back by any user after saving:

- **`env`** — environment variables for stdio servers
- **`headers`** — request headers for HTTP servers
- **`CLIENT_SECRET`** — OAuth client secret for HTTP servers

### HTTP vs stdio

- **HTTP (recommended)** — server configurations are never present in the cloud agent's VM environment. The agent does not have access to refresh tokens, headers, or other credentials. Tool calls are proxied through the backend.
- **Stdio** — servers run inside the cloud agent's VM, so the agent has access to the server's configuration and environment variables. This is similar to how stdio MCPs work in the Cursor IDE.

Stdio servers depend on the VM environment to execute. We cannot verify that a stdio server will run successfully until a cloud agent is launched. We recommend using HTTP MCPs when possible, and configuring your [environment setup](https://cursor.com/docs/cloud-agent/setup.md) correctly if you use stdio servers.

## Fixing CI Failures

Cloud Agents will automatically attempt to fix CI failures in PRs they create. They will ignore failing CI checks that are also failing in the base commit of the PR. Currently, only GitHub Actions is supported.

To disable this feature on all your personal Cloud Agents, go to [Cursor Dashboard → Cloud Agents → My Settings](https://cursor.com/dashboard?tab=cloud-agents) and disable the "Automatically fix CI Failures" option.

To disable this feature on a specific Cloud Agent PR, you can comment `@cursor autofix off` on the PR. To re-enable it, comment `@cursor autofix on`.

If you want cloud agents to fix CI failures in your own PRs, you can simply ask them by tagging Cursor in a comment as normal. For example, `@cursor please fix the CI failures`, or `@cursor fix the CI lint check failure`.

Automatically fixing CI failures is currently only available on Teams; support for non-Teams accounts is coming soon. In the meantime, if you want similar behavior, you can ask the cloud agent explicitly to monitor and fix CI failures on the PR.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/egress-ip-ranges.md
# INDEX: 48/114
================================================================================

# Cloud Agent Egress IP Ranges

Cloud Agents make network connections from specific IP address ranges when accessing external services, APIs, or repositories. This page documents the IP addresses that Cloud Agents use for outbound connections.

## API Endpoint

The IP ranges are available via a [JSON API endpoint](https://cursor.com/docs/ips.json):

```bash
curl https://cursor.com/docs/ips.json
```

### Response Format

```json
{
  "version": 1,
  "modified": "2025-09-24T16:00:00.000Z",
  "cloudAgents": {
    "us3p": ["100.26.13.169/32", "34.195.201.10/32", ...],
    "us4p": ["54.184.235.255/32", "35.167.37.158/32", ...],
    "us5p": ["3.12.82.200/32", "52.14.104.140/32", ...]
  }
}
```

- **version**: Schema version number for the API response
- **modified**: ISO 8601 timestamp of when the IP ranges were last updated
- **cloudAgents**: Object containing IP ranges, keyed by cluster

IP ranges published in [CIDR notation](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing). You can use an online conversion tool to convert from CIDR notation to IP address ranges if needed.

## Using the IP Ranges

These published IP ranges may be used by Cloud Agents to:

- Clone and push to remote repositories (unless using the [GitHub IP allow list](https://cursor.com/docs/integrations/github.md#ip-allow-list-configuration))
- Download packages and dependencies
- Make API calls to external services
- Access web resources during agent execution

If your organization uses firewall rules or IP allowlists to control network access, you may need to allowlist these IP ranges to ensure Cloud Agents can properly access your services.

**Important considerations:**

- We make changes to our IP addresses from time to time for scaling and operational needs.
- We do not recommend allowlisting by IP address as your primary security mechanism.
- If you must use these IP ranges, we strongly encourage regular monitoring of the JSON API endpoint.

## GitHub Proxy and IP Allow List

Cursor supports a similar but distinct feature to [use a GitHub egress proxy for IP allow lists](https://cursor.com/docs/integrations/github.md#ip-allow-list-configuration). This proxy works for all GitHub-dependent Cursor features, including Cloud Agents.

We recommended that you use the GitHub-specific IP allow list for GitHub, as it is more deeply integrated with the Cursor GitHub app, and the above egress IP ranges for everything else.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/network-access.md
# INDEX: 49/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/security.md
# INDEX: 50/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/settings.md
# INDEX: 51/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/cloud-agent/setup.md
# INDEX: 52/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/configuration/extensions.md
# INDEX: 53/114
================================================================================

# Extensions

Cursor supports VS Code extensions, allowing you to enhance your development environment with additional functionality. Extensions can be installed from the built-in marketplace or directly using extension URLs.

## Extension registry

Cursor uses the Open VSX registry to provide extensions. However, unlike the standard Open VSX implementation, **Cursor independently verifies all extensions** for security and compatibility.

This verification process ensures:

- Extensions are safe to use
- They work properly with Cursor's AI features
- Performance remains optimal

While Cursor is built on VS Code's foundation, not all VS Code extensions may
be available or work exactly the same way due to Cursor's additional AI
capabilities and verification requirements.

## Installing extensions

### Using the extensions panel

The easiest way to install extensions is through the Extensions panel:

1. Open the Extensions view (⌘/Ctrl + Shift + X)
2. Search for the extension you want
3. Click Install

### Using extension URLs

You can also open extensions directly using a special URL pattern:

```bash
cursor:extension/publisher.extensionname
```

For example, to open the ChatGPT extension page:

```bash
cursor:extension/openai.chatgpt
```

This pattern is useful for:

- Sharing specific extensions with team members
- Creating documentation with direct links to extensions
- Automating extension installation in setup scripts

## Managing extensions

### Viewing installed extensions

To see your installed extensions:

1. Open the Extensions panel (⌘/Ctrl + Shift + X)
2. Click on the "Installed" filter

### Disabling or uninstalling

Right-click on any installed extension to:

- Disable the extension temporarily
- Uninstall it completely
- Configure extension-specific settings

### Extension settings

Many extensions come with configurable settings. To access them:

1. Open Settings (⌘/Ctrl + ,)
2. Search for the extension name
3. Modify the available settings

## Publisher verification

Extension publishers can request verification to display a verification badge in the marketplace. Verified publishers have undergone additional security review and identity confirmation.

### Requesting verification

To request verification for your extension:

### Add marketplace links to your website

On your public website, add a link to the OpenVSX listing for your extension. Place this link prominently (such as in the installation section) alongside links to other marketplaces. This link must be on a website with its own domain name; a GitHub readme is not supported.

Update the "homepage" link on your OpenVSX listing to point to this website.

### Ensure consistent extension IDs

If your extension is published on multiple marketplaces, use the same
extension ID on OpenVSX as you do elsewhere.

### Submit a verification request

Create a post in the [Extension Verification category](https://forum.cursor.com/c/showcase/extension-verification/23) containing: - Your extension
name - A link to your website where we can verify the OpenVSX registry link

### Wait for review

We'll verify the link and add the verification badge to your publisher name once approved.

The verification process helps users identify trusted extensions and ensures a
higher standard of security and authenticity in the marketplace.

## Importing from VS Code

If you're migrating from VS Code, you can import all your extensions automatically. See our [VS Code migration guide](https://cursor.com/docs/configuration/migrations/vscode.md) for detailed instructions.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/kbd.md
# INDEX: 54/114
================================================================================

# Keyboard Shortcuts

Overview of keyboard shortcuts in Cursor. See all keyboard shortcuts by pressing Cmd R then Cmd S or by opening command palette Cmd Shift P and searching for `Keyboard Shortcuts`.

Learn more about Keyboard Shortcuts in Cursor with [Key Bindings for VS Code](https://code.visualstudio.com/docs/getstarted/keybindings) as a baseline for Cursor's keybindings.

All Cursor keybindings, including Cursor-specific features, can be remapped in Keyboard Shortcuts settings.

## General

| Shortcut        | Action                                  |
| --------------- | --------------------------------------- |
| Cmd I           | Toggle Sidepanel (unless bound to mode) |
| Cmd L           | Toggle Sidepanel (unless bound to mode) |
| Cmd E           | Toggle Agent layout                     |
| Cmd .           | Mode Menu                               |
| Cmd /           | Loop between AI models                  |
| Cmd Shift J     | Cursor settings                         |
| Cmd Shift Space | Toggle Voice Mode                       |
| Cmd ,           | General settings                        |
| Cmd Shift P     | Command palette                         |

## Chat

Shortcuts for the chat input box.

| Shortcut                                  | Action                       |
| ----------------------------------------- | ---------------------------- |
| Return                                    | Nudge (default)              |
| Ctrl Return                               | Queue message                |
| Cmd Return when typing                    | Force send message           |
| Cmd Shift Backspace                       | Cancel generation            |
| Cmd Shift L with code selected            | Add selected code as context |
| Cmd V with code or log in clipboard       | Add clipboard as context     |
| Cmd Shift V with code or log in clipboard | Add clipboard to input box   |
| Cmd Return with suggested changes         | Accept all changes           |
| Cmd Backspace                             | Reject all changes           |
| Tab                                       | Cycle to next message        |
| Shift Tab                                 | Rotate between Agent modes   |
| Cmd Opt /                                 | Model toggle                 |
| Cmd N / Cmd R                             | New chat                     |
| Cmd T                                     | New chat tab                 |
| Cmd \[                                    | Previous chat                |
| Cmd ]                                     | Next chat                    |
| Cmd W                                     | Close chat                   |
| Escape                                    | Unfocus field                |

## Inline Edit

| Shortcut            | Action             |
| ------------------- | ------------------ |
| Cmd K               | Open               |
| Cmd Shift K         | Toggle input focus |
| Return              | Submit             |
| Cmd Shift Backspace | Cancel             |
| Opt Return          | Ask quick question |

## Code Selection & Context

| Shortcut                        | Action                                                    |
| ------------------------------- | --------------------------------------------------------- |
| @                               | [@-mentions](https://cursor.com/docs/context/mentions.md) |
| /                               | Shortcut Commands                                         |
| Cmd Shift L                     | Add selection to Chat                                     |
| Cmd Shift K                     | Add selection to Edit                                     |
| Cmd L                           | Add selection to new chat                                 |
| Cmd M                           | Toggle file reading strategies                            |
| Cmd →                           | Accept next word of suggestion                            |
| Cmd Return                      | Search codebase in chat                                   |
| Select code, Cmd C, Cmd V       | Add copied reference code as context                      |
| Select code, Cmd C, Cmd Shift V | Add copied code as text context                           |

## Tab

| Shortcut | Action            |
| -------- | ----------------- |
| Tab      | Accept suggestion |
| Cmd →    | Accept next word  |

## Terminal

| Shortcut   | Action                   |
| ---------- | ------------------------ |
| Cmd K      | Open terminal prompt bar |
| Cmd Return | Run generated command    |
| Escape     | Accept command           |


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/languages/ios-macos-swift.md
# INDEX: 55/114
================================================================================

# iOS & macOS (Swift)

Welcome to Swift development in Cursor! Whether you're building iOS apps, macOS applications, or server-side Swift projects, we've got you covered. This guide will help you set up your Swift environment in Cursor, starting with the basics and moving on to more advanced features.

## Basic Workflow

The simplest way to use Cursor with Swift is to treat it as your primary code editor while still relying on Xcode for building and running your apps. You'll get great features like:

- Smart code completion
- AI-powered coding assistance (try [CMD+K](https://cursor.com/docs/inline-edit/overview.md) on any line)
- Quick access to documentation with [@Docs](https://cursor.com/docs/context/mentions.md)
- Syntax highlighting
- Basic code navigation

When you need to build or run your app, simply switch to Xcode. This workflow is perfect for developers who want to leverage Cursor's AI capabilities while sticking to familiar Xcode tools for debugging and deployment.

### Hot Reloading

When using Xcode workspaces or projects (instead of opening a folder directly in Xcode), Xcode can often ignore changes to your files that were made in Cursor, or outside of Xcode in general.

While you can open the folder in Xcode to resolve this, you may need to use a project for your Swift development workflow.

A great solution to this is to use [Inject](https://github.com/krzysztofzablocki/Inject), a hot reloading library for Swift that allows your app to "hot reload" and update as soon as changes are made in real time. This does not suffer from the side effects of the Xcode workspace/project issue, and allows you to make changes in Cursor and have them reflected in your app immediately.

## Advanced Swift Development

This section of the guide was heavily inspired by [Thomas
Ricouard](https://x.com/Dimillian) and his
[article](https://dimillian.medium.com/how-to-use-cursor-for-ios-development-54b912c23941)
about using Cursor for iOS development. Please check his article for more
details and drop him a follow for more Swift content.

If you are looking to only need one editor open at a time, and want to avoid the need to switch between Xcode and Cursor, you can use an extension like [Sweetpad](https://sweetpad.hyzyla.dev/) to integrate Cursor directly with Xcode's underlying build system.

Sweetpad is a powerful extension that allows you to build, run and debug your Swift projects directly in Cursor, without compromising on Xcode's features.

To get started with Sweetpad, you'll still need to have Xcode installed on your Mac - it's the foundation of Swift development. You can download Xcode from the [Mac App Store](https://apps.apple.com/us/app/xcode/id497799835). Once you have Xcode set up, let's enhance your development experience in Cursor with a few essential tools.

Open your terminal and run:

```bash
# Builds your projects without needing Xcode open
brew install xcode-build-server

# Pretty print's the `xcodebuild` command output into Cursor's terminal
brew install xcbeautify

# Allows for advanced formating and language features
brew install swiftformat
```

Next, install the [Swift Language Support](cursor:extension/chrisatwindsurf.swift-vscode) extension in Cursor. This will give you syntax highlighting and basic language features right out of the box.

Then, we can install the [Sweetpad](https://sweetpad.hyzyla.dev/) extension to integrate Cursor with Xcode. Sweetpad wraps a bunch of shortcuts around the `xcodebuild` CLI (and much more), and allows you to scan your targets, select the destination, build, and run your app just like Xcode. On top of that, it’ll set up your project for Xcode Build Server so you get all the features mentioned above.

### Sweetpad Usage

Once Sweetpad is installed, and you have a Swift project open in Cursor, you should first run the `Sweetpad: Generate Build Server Config` command. This will generate a `buildServer.json` file in the root of your project that allows the Xcode Build Server to work with your project.

Then, from either the Command Palette or the Sweetpad sidebar, you can select the target you want to build and run.

You need to build your project once to enable auto-completion, jump to definition, and other language features.

You can also now hit F5 to build and run your project with a debugger - you might need to create a launch configuration first, but just select Sweetpad from the list when prompted!

As with many extensions in Cursor, you can bind many of the Sweetpad commands to keyboard shortcuts, to make your workflow even more efficient.

To learn more about Sweetpad, check out these resources:

### Sweetpad Website

Official Sweetpad website with features and installation instructions

### Sweetpad Guide

Comprehensive guide covering configuration, usage and advanced features


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/languages/java.md
# INDEX: 56/114
================================================================================

# Java

This guide will help you configure Cursor for Java development, including setting up the JDK, installing necessary extensions, debugging, running Java applications, and integrating build tools like Maven and Gradle. It also covers workflow features similar to IntelliJ or VS Code.

## Setting up Java for Cursor

### Java Installation

Before setting up Cursor itself, you will need Java installed on your machine.

Cursor does not ship with a Java compiler, so you need to install a JDK if you
haven't already.

- **Windows**: Download and install a JDK (e.g., OpenJDK, Oracle JDK, Microsoft Build of OpenJDK). Set JAVA\_HOME and add JAVA\_HOME\bin to your PATH.
- **macOS**: Install via Homebrew (`brew install openjdk`) or download an installer. Ensure JAVA\_HOME points to the installed JDK.
- **Linux**: Use your package manager (`sudo apt install openjdk-17-jdk` or equivalent) or install via SDKMAN.

To check installation, run:

```bash
java -version
javac -version
```

If Cursor does not detect your JDK, configure it manually in settings.json. Then, restart Cursor to apply changes.

```json
{
  "java.jdt.ls.java.home": "/path/to/jdk",
  "java.configuration.runtimes": [
    {
      "name": "JavaSE-17",
      "path": "/path/to/jdk-17",
      "default": true
    }
  ]
}
```

### Cursor Setup

Cursor supports VS Code extensions. Install the following manually:

### Extension Pack for Java

Includes Java language support, debugger, test runner, Maven support, and
project manager

### Gradle for Java

Essential for working with Gradle build system

### Spring Boot Extension Pack

Required for Spring Boot development

### Kotlin

Necessary for Kotlin application development

### Configure Build Tools

#### Maven

Ensure Maven is installed (`mvn -version`). Install from [maven.apache.org](https://maven.apache.org/download.cgi) if needed:

1. Download the binary archive
2. Extract to desired location
3. Set MAVEN\_HOME environment variable to the extracted folder
4. Add %MAVEN\_HOME%\bin (Windows) or $MAVEN\_HOME/bin (Unix) to PATH

#### Gradle

Ensure Gradle is installed (`gradle -version`). Install from [gradle.org](https://gradle.org/install/) if needed:

1. Download the binary distribution
2. Extract to desired location
3. Set GRADLE\_HOME environment variable to the extracted folder
4. Add %GRADLE\_HOME%\bin (Windows) or $GRADLE\_HOME/bin (Unix) to PATH

Alternatively, use the Gradle Wrapper which will automatically download and use the correct Gradle version:

## Running and Debugging

Now you are all set up, it's time to run and debug your Java code.
Depending on your needs, you can use the following methods:

### Run

Click the "Run" link that appears above any main method to quickly execute
your program

### Debug

Open the Run and Debug sidebar panel and use the Run button to start your
application

### Terminal

Execute from command line using Maven or Gradlecommands

### Spring Boot

Launch Spring Boot applications directly from the Spring Boot Dashboard
extension

## Java x Cursor Workflow

Cursor's AI-powered features can significantly enhance your Java development workflow. Here are some ways to leverage Cursor's capabilities specifically for Java:

### Tab Completion

Smart completions for methods, signatures, and Java boilerplate like
getters/setters.

### Agent Mode

Implement design patterns, refactor code, or generate classes with proper
inheritance.

### Inline Edit

Quick inline edits to methods, fix errors, or generate unit tests without
breaking flow.

### Chat

Get help with Java concepts, debug exceptions, or understand framework
features.

### Example Workflows

1. **Generate Java Boilerplate**: Use [Tab completion](https://cursor.com/docs/tab/overview.md) to quickly generate constructors, getters/setters, equals/hashCode methods, and other repetitive Java patterns.
2. **Debug Complex Java Exceptions**: When facing a cryptic Java stack trace, highlight it and use [Ask](https://cursor.com/docs/chat/overview.md) to explain the root cause and suggest potential fixes.
3. **Refactor Legacy Java Code**: Use [Agent mode](https://cursor.com/docs/agent/overview.md) to modernize older Java code - convert anonymous classes to lambdas, upgrade to newer Java language features, or implement design patterns.
4. **Frameworks Development**: Add your documentation to Cursor's context with @docs, and generate framework-specific code throughout Cursor.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/languages/javascript-typescript.md
# INDEX: 57/114
================================================================================

# JavaScript & TypeScript

Welcome to JavaScript and TypeScript development in Cursor! The editor provides exceptional support for JS/TS development through its extension ecosystem. Here's what you need to know to get the most out of Cursor.

## Essential Extensions

While Cursor works great with any extensions you prefer, we recommend these for those just getting started:

- **ESLint** - Required for Cursor's AI-powered lint fixing capabilities
- **JavaScript and TypeScript Language Features** - Enhanced language support and IntelliSense
- **Path Intellisense** - Intelligent path completion for file paths

## Cursor Features

Cursor enhances your existing JavaScript/TypeScript workflow with:

- **Tab Completions**: Context-aware code completions that understand your project structure
- **Automatic Imports**: Tab can automatically import libraries as soon as you use them
- **Inline Editing**: Use `CMD+K` on any line to edit with perfect syntax
- **Composer Guidance**: Plan and edit your code across multiple files with the Composer

### Automatic Linting Resolution

Cursor integrates with linter extensions like ESLint, Biome, and others.

When using the Cursor agent, once it has attempted to answer your query and has made any code changes, it will automatically read the output of the linter and will attempt to fix any lint errors it might not have known about.

### Browser

Cursor includes an [integrated browser](https://cursor.com/docs/agent/browser.md) that works with the agent to help you develop and debug web applications.

- **Open your local dev server**: The agent can launch and open your development server directly in the integrated browser, allowing you to see your changes in real-time.
- **Read console logs**: The browser captures all console messages, errors, and warnings, giving the agent full visibility into JavaScript issues.
- **Inspect network traffic**: The agent can monitor HTTP requests and responses, helping diagnose API issues and track down bugs.
- **Visual feedback**: Screenshots and accessibility snapshots let the agent understand page layout and interact with UI elements intelligently.

## Framework Support

Cursor works seamlessly with all major JavaScript frameworks and libraries, such as:

### React & Next.js

- Full JSX/TSX support with intelligent component suggestions
- Server component and API route intelligence for Next.js
- Recommended: [**React Developer Tools**](cursor:extension/msjsdiag.vscode-react-native) extension

### Vue.js

- Template syntax support with Volar integration
- Component auto-completion and type checking
- Recommended: [**Vue Language Features**](cursor:extension/vue.volar)

### Angular

- Template validation and TypeScript decorator support
- Component and service generation
- Recommended: [**Angular Language Service**](cursor:extension/Angular.ng-template)

### Svelte

- Component syntax highlighting and intelligent completions
- Reactive statement and store suggestions
- Recommended: [**Svelte for VS Code**](cursor:extension/svelte.svelte-vscode)

### Backend Frameworks (Express/NestJS)

- Route and middleware intelligence
- TypeScript decorator support for NestJS
- API testing tools integration

Remember, Cursor's AI features work well with all these frameworks, understanding their patterns and best practices to provide relevant suggestions. The AI can help with everything from component creation to complex refactoring tasks, while respecting your project's existing patterns.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/languages/python.md
# INDEX: 58/114
================================================================================

# Python

This guide was heavily inspired by [Jack Fields](https://x.com/OrdinaryInds)
and his
[article](https://medium.com/ordinaryindustries/the-ultimate-vs-code-setup-for-python-538026b34d94)
about setting up VS Code for Python development. Please check his article for
more details.

## Prerequisites

Before we begin, ensure you have:

- [Python](https://python.org) installed (3.8 or higher recommended)
- [Git](https://git-scm.com/) for version control
- Cursor installed and updated to the latest version

## Essential Extensions

The following extensions setup Cursor to be fully featured for Python development. These provide you with syntax highlighting, linting, debugging and unit testing.

- [**Python**](cursor:extension/ms-python.python) (Core language support from Microsoft)
- [**Cursor Pyright**](cursor:extension/anysphere.cursorpyright) (Fast Python language server)
- [**Python Debugger**](cursor:extension/ms-python.debugpy) (Enhanced debugging capabilities)
- [**Ruff**](cursor:extension/charliermarsh.ruff) (Python linter and formatter)

### Advanced Python Tooling

While the above extensions have previously been the most popular extensions for Python development in Cursor, we've also added some additional extensions that can help you get the most out of your Python development.

#### `uv` - Python Environment Manager

[uv](https://github.com/astral-sh/uv) is a modern Python package manager that can be used to create and manage virtual environments, in addition to replacing pip as the default package manager.

To install uv, run the following command in your terminal:

```bash
pip install uv
```

#### `ruff` - Python Linter and Formatter

[Ruff](https://docs.astral.sh/ruff/) is a modern Python linter and formatter that can be used to check for programming errors, helps enforce coding standards, and can suggest refactoring. It can be used alongside Black for code formatting.

To install Ruff, run the following command in your terminal:

```bash
pip install ruff
```

## Cursor Configuration

### 1. Python Interpreter

Configure your Python interpreter in Cursor:

1. Open Command Palette (Cmd/Ctrl + Shift + P)
2. Search for "Python: Select Interpreter"
3. Choose your Python interpreter (or virtual environment if you're using one)

### 2. Code Formatting

Set up automatic code formatting with Black:

Black is a code formatter that automatically formats your code to follow a
consistent style. It requires zero configuration and is widely adopted in the
Python community.

To install Black, run the following command in your terminal:

```bash
pip install black
```

Then, configure Cursor to use Black for code formatting, by adding the following to your `settings.json` file:

```json
{
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.formatting.blackArgs": ["--line-length", "88"]
}
```

### 3. Linting

We can use PyLint to check for programming errors, helps enforce coding standards, and can suggest refactoring.

To install PyLint, run the following command in your terminal:

```bash
pip install pylint
```

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.lintOnSave": true
}
```

### 4. Type Checking

In addition to linting, we can use MyPy to check for type errors.

To install MyPy, run the following command in your terminal:

```bash
pip install mypy
```

```json
{
  "python.linting.mypyEnabled": true
}
```

## Debugging

Cursor provides powerful debugging capabilities for Python:

1. Set breakpoints by clicking the gutter
2. Use the Debug panel (Cmd/Ctrl + Shift + D)
3. Configure `launch.json` for custom debug configurations

## Framework Support

Cursor works seamlessly with popular Python frameworks:

- **Web Frameworks**: Django, Flask, FastAPI
- **Data Science**: Jupyter, NumPy, Pandas
- **Machine Learning**: TensorFlow, PyTorch, scikit-learn
- **Testing**: pytest, unittest
- **API**: requests, aiohttp
- **Database**: SQLAlchemy, psycopg2


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/migrations/jetbrains.md
# INDEX: 59/114
================================================================================

# JetBrains Migration

Cursor offers a modern, AI-powered coding experience that can replace your JetBrains IDEs. While the transition might feel different at first, Cursor's VS Code-based foundation provides powerful features and extensive customization options.

Don't want to migrate? You can still use [Cursor CLI](https://cursor.com/docs/cli/overview.md) with your JetBrains IDEs.

## Editor Components

### Extensions

JetBrains IDEs are great tools, as they come already pre-configured for the languages and frameworks they are intended for.

Cursor is different - being a blank canvas out of the box, you can customize it to your liking, not being limited by the languages and frameworks the IDE was intended for.

Cursor has access to a vast ecosystem of extensions, and almost all of the functionality (and more!) that JetBrains IDEs offer can be recreated through these extensions.

Take a look at some of these popular extensions below:

- **[Remote SSH](cursor:extension/anysphere.remote-ssh)** - SSH Extension
- **[Project Manager](cursor:extension/alefragnani.project-manager)** - Manage multiple projects
- **[GitLens](cursor:extension/eamodio.gitlens)** - Enhanced Git integration
- **[Local History](cursor:extension/xyz.local-history)** - Track local file changes
- **[Error Lens](cursor:extension/usernamehw.errorlens)** - Inline error highlighting
- **[ESLint](cursor:extension/dbaeumer.vscode-eslint)** - Code linting
- **[Prettier](cursor:extension/esbenp.prettier-vscode)** - Code formatting
- **[Todo Tree](cursor:extension/Gruntfuggly.todo-tree)** - Track TODOs and FIXMEs

### Keyboard Shortcuts

Cursor has a built-in keyboard shortcut manager that allows you to map your favorite keyboard shortcuts to actions.

With the [IntelliJ IDEA Keybindings](cursor:extension/k--kato.intellij-idea-keybindings) extension, you can bring almost all of the JetBrains IDEs shortcuts directly to Cursor!
Be sure to read the extension's documentation to learn how to configure it to your liking.

Common shortcuts that differ:

- **Find Action:** ⌘/Ctrl+Shift+P  (vs. ⌘/Ctrl+Shift+A)
- **Quick Fix:** ⌘/Ctrl+.  (vs. Alt+Enter)
- **Go to File:** ⌘/Ctrl+P  (vs. ⌘/Ctrl+Shift+N)

### Themes

Recreate the look and feel of your favorite JetBrains IDEs in Cursor with these community themes.

Choose from the standard Darcula Theme, or pick a theme to match the syntax highlighting of your JetBrains tools.

- **[JetBrains - Darcula Theme](cursor:extension/rokoroku.vscode-theme-darcula)** - Experience the classic JetBrains Darcula dark theme
- **[JetBrains PyCharm](cursor:extension/gabemahoney.pycharm-dark-theme-for-python)**
- **[IntelliJ](cursor:extension/compassak.intellij-idea-new-ui)**
- **[JetBrains Fleet](cursor:extension/MichaelZhou.fleet-theme)**
- **[JetBrains Rider](cursor:extension/muhammad-sammy.rider-theme)**
- **[JetBrains Icons](cursor:extension/ardonplay.vscode-jetbrains-icon-theme)** - Get the familiar JetBrains file and folder icons

### Font

To complete your JetBrains-like experience, you can use the official JetBrains Mono font:

1. [Download JetBrains Mono](https://www.jetbrains.com/lp/mono/) and install it onto your system:
2. Restart Cursor after installing the font
3. Open Settings in Cursor (⌘/Ctrl + ,)
4. Search for "Font Family"
5. Set the font family to `'JetBrains Mono'`

For the best experience, you can also enable font ligatures by setting `"editor.fontLigatures": true` in your settings.

## Tips for a Smooth Transition

### Use Command Palette

Press ⌘/Ctrl + Shift + P to find commands

### AI Features

Leverage Cursor's AI features for code completion and refactoring

### Customize Settings

Fine-tune your settings.json for optimal workflow

### Terminal Integration

Use the built-in terminal for command-line operations

### Extensions

Browse the VS Code marketplace for additional tools

Remember that while some workflows might be different, Cursor offers powerful AI-assisted coding features that can enhance your productivity beyond traditional IDE capabilities.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/migrations/vscode.md
# INDEX: 60/114
================================================================================

# VS Code Migration

Cursor is based upon the VS Code codebase, allowing us to focus on making the best AI-powered coding experience while maintaining a familiar editing environment. This makes it easy to migrate your existing VS Code settings to Cursor.

## Profile Migration

### One-click Import

Here's how to get your entire VS Code setup in one click:

1. Open the Cursor Settings (⌘/Ctrl + Shift + J)
2. Navigate to General > Account
3. Under "VS Code Import", click the Import button

![VS Code Import](/docs-static/images/get-started/vscode-import.png)

This will transfer your:

- Extensions
- Themes
- Settings
- Keybindings

### Manual Profile Migration

If you are moving between machines, or want more control over your settings, you can manually migrate your profile.

#### Exporting a Profile

1. On your VS Code instance, open the Command Palette (⌘/Ctrl + Shift + P)
2. Search for "Preferences: Open Profiles (UI)"
3. Find the profile you want to export on the left sidebar
4. Click the 3-dot menu and select "Export Profile"
5. Choose to export it either to your local machine or to a GitHub Gist

#### Importing a Profile

1. On your Cursor instance, open the Command Palette (⌘/Ctrl + Shift + P)
2. Search for "Preferences: Open Profiles (UI)"
3. Click the dropdown menu next to 'New Profile' and click 'Import Profile'
4. Either paste in the URL of the GitHub Gist or choose 'Select File' to upload a local file
5. Click 'Import' at the bottom of the dialog to save the profile
6. Finally, in the sidebar, choose the new profile and click the tick icon to active it

## Settings and Interface

### Settings Menus

- **Cursor Settings:** (⌘/Ctrl + Shift + P), then type "Cursor Settings"
- **VS Code Settings:** (⌘/Ctrl + Shift + P), then type "Preferences: Open Settings (UI)"

### Version Updates

We regularly rebase Cursor onto the latest VS Code version to stay current with features and fixes. To ensure stability, Cursor often uses slightly older VS Code versions.

### Activity Bar Orientation

We made the activity bar horizontal to optimize space for the AI chat interface. If you prefer vertical:

1. Open the Command Palette (⌘/Ctrl + Shift + P)
2. Search for "Preferences: Open Settings (UI)"
3. Search for `workbench.activityBar.orientation`
4. Set the value to `vertical`
5. Restart Cursor


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/shell.md
# INDEX: 61/114
================================================================================

# Shell Commands

Cursor provides command-line tools to open files and folders from your terminal. Install both the `cursor` and `code` commands to integrate Cursor with your development workflow.

## Installing CLI commands

Install the CLI commands through the Command Palette:

1. Open the Command Palette (Cmd/Ctrl + P)
2. Type "Install" to filter installation commands
3. Select and run `Install 'cursor' to shell`
4. Repeat and select `Install 'code' to shell`

## Using the CLI commands

After installation, use either command to open files or folders in Cursor:

```bash
# Using the cursor command
cursor path/to/file.js
cursor path/to/folder/

# Using the code command (VS Code compatible)
code path/to/file.js
code path/to/folder/
```

## Command options

Both commands support these options:

- Open a file: `cursor file.js`
- Open a folder: `cursor ./my-project`
- Open multiple items: `cursor file1.js file2.js folder1/`
- Open in a new window: `cursor -n` or `cursor --new-window`
- Wait for the window to close: `cursor -w` or `cursor --wait`

## FAQ

### What's the difference between cursor and code commands?

The `code` command is provided for VS Code compatibility. The `cursor` command also providers access to the [Cursor CLI](https://cursor.com/docs/cli/overview.md).

### Do I need to install both commands?

No, install either or both based on preference.

### Where are the commands installed?

Commands are installed in your system's default shell configuration file (e.g., `.bashrc`, `.zshrc`, or `.config/fish/config.fish`).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/themes.md
# INDEX: 62/114
================================================================================

# Themes

Cursor supports both light and dark themes for your coding environment. Cursor inherits VS Code's theming capabilities - use any VS Code theme, create custom themes, and install theme extensions from the marketplace.

## Changing theme

1. Open the Command Palette (Cmd+Shift+P / Ctrl+Shift+P)
2. Type "theme" to filter commands
3. Select "Preferences: Color Theme"
4. Choose a theme

![Theme selection menu in Cursor showing available color themes](/docs-static/images/config/themes.png)

## FAQ

### Can I use my VS Code themes in Cursor?

Yes! Cursor is compatible with VS Code themes. Install any VS Code marketplace theme or copy custom theme files.

### How do I create a custom theme?

Create custom themes like in VS Code. Use "Developer: Generate Color Theme From Current Settings" to start from current settings, or follow the VS Code theme authoring guide.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/configuration/worktrees.md
# INDEX: 63/114
================================================================================

# Parallel Agents

This feature allows you to run multiple agents locally in parallel, or run a single prompt across multiple models at once.

Parallel agents run in their own worktree, allowing them to make edits, or build and test code without interfering with each other.

A worktree is a Git feature that lets you use multiple branches of one repository at once.
Each worktree has its own set of files and changes.

Cursor automatically creates and configures worktrees for you, and we currently have a 1:1 mapping of agents to worktrees. You can also add custom instructions to [configure the worktree setup](https://cursor.com/docs/configuration/worktrees.md#initialization-script), like installing dependencies or applying database migrations.

## Basic Worktree usage

The most basic way to use worktrees in Cursor is to run a single agent in a worktree.

![Basic worktree usage](/docs-static/images/worktrees/worktree-dropdown.png)

When the agent run is complete, click the "Apply" button to apply the agent's changes to your local branch. This is different from the "Keep" button in local agents.

If you'd like to see all worktrees in your git repository, you can run the command `git worktree list` in your terminal. The output will look like this:

```
/.../<repo>                                  15ae12e   [main]
/Users/<you>/.cursor/worktrees/<repo>/98Zlw  15ae12e   [feat-1-98Zlw]
/Users/<you>/.cursor/worktrees/<repo>/a4Xiu  15ae12e   [feat-2-a4Xiu]
```

# Best-of-N - Use multiple models at once

A powerful feature of worktrees is the ability to run a single prompt on multiple models at once.

![Basic best-of-N usage](/docs-static/images/worktrees/worktree-bon.png)

Once you submit a prompt, you will see two cards, one for each model. Click across the cards to see the changes made by each Agent.

![Best-of-N cards](/docs-static/images/worktrees/worktree-bon-cards.png)

Then, click the "Apply" button to apply the changes to your checked out branch.

### When to use multiple models

Running the same prompt across multiple models is especially useful for:

- **Hard problems** where different models might take different approaches
- **Comparing code quality** across model families to find the best solution
- **Finding edge cases** one model might miss that another catches
- **Benchmarking** which models work best for your specific codebase

Having multiple models attempt the same problem and picking the best result significantly improves the final output, especially for harder tasks.

Configure notifications and sounds in Cursor settings so you know when parallel agents finish their work.

## "Apply" Functionality

When you run a parallel agent, you will see a "Apply" button. Clicking this button will apply the changes to your checked out branch. The way this process works is the following:

1. When Cursor creates a worktree, all new files and edited files in your primary working tree are brought along to the worktree (the only exception is files that are ignored by Git).
2. The agent will perform its work in isolation inside this worktree, and potentially make edits to files.
3. When you click "Apply", we try to cleanly merge those changes in to your primary working tree.

If you're applying multiple times inside the same Best-of-N run, Cursor will ask you how you'd like to proceed:

- You have the option to "Full Overwrite" (replace the full contents of every file with the changes from the agent in the worktree)
- Try to "merge" between multiple options using the native conflict resolution UI

## Initialization Script

You can customize the worktree setup by editing the `.cursor/worktrees.json` file. Cursor finds this file in the following order:

1. In the worktree path
2. In the root path of your project

### Configuration options

The `worktrees.json` file supports three configuration keys:

- **`setup-worktree-unix`**: Commands or script path for macOS/Linux. Takes precedence over `setup-worktree` on Unix systems.
- **`setup-worktree-windows`**: Commands or script path for Windows. Takes precedence over `setup-worktree` on Windows.
- **`setup-worktree`**: Generic fallback for all operating systems.

Each key accepts either:

- **An array of shell commands** - executed sequentially in the worktree
- **A string filepath** - path to a script file relative to `.cursor/worktrees.json`

## Example setup configurations

### Using command arrays

#### Node.js project

```json
{
  "setup-worktree": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env"
  ]
}
```

We do not recommend symlinking dependencies into the worktree, as this can cause issues in the
main worktree. Instead, we recommend using fast package managers such as `bun`, `pnpm` or `uv`
in the Python ecosystem to install dependencies.

#### Python project with virtual environment

```json
{
  "setup-worktree": [
    "python -m venv venv",
    "source venv/bin/activate && pip install -r requirements.txt",
    "cp $ROOT_WORKTREE_PATH/.env .env"
  ]
}
```

#### Project with database migrations

```json
{
  "setup-worktree": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env",
    "npm run db:migrate"
  ]
}
```

#### Build and link dependencies

```json
{
  "setup-worktree": [
    "pnpm install",
    "pnpm run build",
    "cp $ROOT_WORKTREE_PATH/.env.local .env.local"
  ]
}
```

### Using script files

For complex setups, you can reference script files instead of inline commands:

```json
{
  "setup-worktree-unix": "setup-worktree-unix.sh",
  "setup-worktree-windows": "setup-worktree-windows.ps1",
  "setup-worktree": [
    "echo 'Using generic fallback. For better support, define OS-specific scripts.'"
  ]
}
```

Place your scripts in the `.cursor/` directory alongside `worktrees.json`:

**setup-worktree-unix.sh** (Unix/macOS):

```bash
#!/bin/bash
set -e

# Install dependencies
npm ci

# Copy environment file
cp "$ROOT_WORKTREE_PATH/.env" .env

# Run database migrations
npm run db:migrate

echo "Worktree setup complete!"
```

**setup-worktree-windows.ps1** (Windows):

```powershell
$ErrorActionPreference = 'Stop'

# Install dependencies
npm ci

# Copy environment file
Copy-Item "$env:ROOT_WORKTREE_PATH\.env" .env

# Run database migrations
npm run db:migrate

Write-Host "Worktree setup complete!"
```

### OS-specific configurations

You can provide different setup commands for different operating systems:

```json
{
  "setup-worktree-unix": [
    "npm ci",
    "cp $ROOT_WORKTREE_PATH/.env .env",
    "chmod +x scripts/*.sh"
  ],
  "setup-worktree-windows": [
    "npm ci",
    "copy %ROOT_WORKTREE_PATH%\\.env .env"
  ]
}
```

### Debugging

If you would like to debug the worktree setup script, open the "Output" bottom panel and select "Worktrees Setup" from the dropdown.

## Worktrees Cleanup

Cursor automatically manages worktrees to prevent excessive disk usage:

- **Per-workspace limit**: Each workspace can have up to 20 worktrees
- **Automatic cleanup**: When you create a new worktree and exceed the limit, Cursor automatically removes the oldest worktrees

Worktrees are removed based on last access time, with the oldest worktrees being removed first. Cleanup is applied per-workspace, so worktrees from different repositories don't interfere with each other. This is done on a schedule, which can be configured in the settings:

```json
{
  // 2.1 and above only:
  "cursor.worktreeCleanupIntervalHours": 6,
  "cursor.worktreeMaxCount": 20
}
```

## Worktrees in the SCM Pane

If you would like to visualize Cursor-created worktrees in the SCM Pane, you can enable the `git.showCursorWorktrees` setting (defaults to `false`).

![Worktrees in the SCM Pane](/docs-static/images/worktrees/worktrees-scm.png)

## Language Server Protocol (LSP) Support

For performance reasons, Cursor currently does not support LSP in worktrees. The agent will not be able to lint files. We are working on supporting this functionality.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/commands.md
# INDEX: 64/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/context/ignore-files.md
# INDEX: 65/114
================================================================================

# Ignore files

## Overview

Cursor reads and indexes your project's codebase to power its features. Control which directories and files Cursor can access using a `.cursorignore` file in your root directory.

Cursor blocks access to files listed in `.cursorignore` from:

- [Semantic search](https://cursor.com/docs/context/semantic-search.md)
- Code accessible by [Tab](https://cursor.com/docs/tab/overview.md), [Agent](https://cursor.com/docs/agent/overview.md), and [Inline Edit](https://cursor.com/docs/inline-edit/overview.md)
- Code accessible via [@ mention references](https://cursor.com/docs/context/mentions/overview.md)

The terminal and MCP server tools used by Agent cannot block access to code
governed by `.cursorignore`

## Why ignore files?

**Security**: Restrict access to API keys, credentials, and secrets. While Cursor blocks ignored files, complete protection isn't guaranteed due to LLM unpredictability.

**Performance**: In large codebases or monorepos, exclude irrelevant portions for faster indexing and more accurate file discovery.

## Global ignore files

Set ignore patterns for all projects in user settings to exclude sensitive files without per-project configuration. The global ignore list is empty by default.

![Global Cursor Ignore List](/docs-static/images/settings/global-ignore.png)

Common patterns to add:

- Environment files: `**/.env`, `**/.env.*`
- Credentials: `**/credentials.json`, `**/secrets.json`
- Keys: `**/*.key`, `**/*.pem`, `**/id_rsa`

## Configuring `.cursorignore`

Create a `.cursorignore` file in your root directory using `.gitignore` syntax.

### Pattern examples

```sh
config.json      # Specific file
dist/           # Directory
*.log           # File extension
**/logs         # Nested directories
!app/           # Exclude from ignore (negate)
```

### Hierarchical ignore

Enable `Cursor Settings` > `Features` > `Editor` > `Hierarchical Cursor Ignore` to search parent directories for `.cursorignore` files.

**Notes**: Comments start with `#`. Later patterns override earlier ones. Patterns are relative to file location.

## Limit indexing with `.cursorindexingignore`

Use `.cursorindexingignore` to exclude files from indexing only. These files remain accessible to AI features but won't appear in codebase searches.

## Files ignored by default

Cursor automatically ignores files in `.gitignore` and the default ignore list below. Override with `!` prefix in `.cursorignore`.

### Default Ignore List

For indexing only, these files are ignored in addition to files in your `.gitignore`, `.cursorignore` and `.cursorindexingignore`:

```sh
package-lock.json
pnpm-lock.yaml
yarn.lock
composer.lock
Gemfile.lock
bun.lockb
.env*
.git/
.svn/
.hg/
*.lock
*.bak
*.tmp
*.bin
*.exe
*.dll
*.so
*.lockb
*.qwoff
*.isl
*.csv
*.pdf
*.doc
*.doc
*.xls
*.xlsx
*.ppt
*.pptx
*.odt
*.ods
*.odp
*.odg
*.odf
*.sxw
*.sxc
*.sxi
*.sxd
*.sdc
*.jpg
*.jpeg
*.png
*.gif
*.bmp
*.tif
*.mp3
*.wav
*.wma
*.ogg
*.flac
*.aac
*.mp4
*.mov
*.wmv
*.flv
*.avi
*.zip
*.tar
*.gz
*.7z
*.rar
*.tgz
*.dmg
*.iso
*.cue
*.mdf
*.mds
*.vcd
*.toast
*.img
*.apk
*.msi
*.cab
*.tar.gz
*.tar.xz
*.tar.bz2
*.tar.lzma
*.tar.Z
*.tar.sz
*.lzma
*.ttf
*.otf
*.pak
*.woff
*.woff2
*.eot
*.webp
*.vsix
*.rmeta
*.rlib
*.parquet
*.svg
.egg-info/
.venv/
node_modules/
__pycache__/
.next/
.nuxt/
.cache/
.sass-cache/
.gradle/
.DS_Store/
.ipynb_checkpoints/
.pytest_cache/
.mypy_cache/
.tox/
.git/
.hg/
.svn/
.bzr/
.lock-wscript/
.Python/
.jupyter/
.history/
.yarn/
.yarn-cache/
.eslintcache/
.parcel-cache/
.cache-loader/
.nyc_output/
.node_repl_history/
.pnp.js/
.pnp/
```

### Negation pattern limitations

When using negation patterns (prefixed with `!`), you cannot re-include a file if a parent directory is excluded via \*.

```sh
# Ignore all files in public folder
public/*

# ✅ This works, as the file exists at the top level
!public/index.html

# ❌ This doesn't work - cannot re-include files from nested directories
!public/assets/style.css
```

**Workaround**: Explicitly exclude nested directories:

```sh
public/assets/*
!public/assets/style.css # This file is now accessible
```

Excluded directories are not traversed for performance, so patterns on contained files have no effect.
This matches the .gitignore implementation for negation patterns in nested directories. For more details, see the [official Git documentation on gitignore patterns](https://git-scm.com/docs/gitignore).

## Troubleshooting

Test patterns with `git check-ignore -v [file]`.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/mcp.md
# INDEX: 66/114
================================================================================

# Model Context Protocol (MCP)

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) enables Cursor to connect to external tools and data sources.

[Media](/docs-static/images/context/mcp/simple-mcp-call.mp4)

## Servers

Browse available MCP servers. Click "Add to Cursor" to install them directly.

| Group | Name                       | Description                                                                                                                                                                                                                                                                                   | Transport       | OAuth | Install                                                                                                                                                                                                              | Docs                                                                                                                                                         |
| ----- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| -     | GitHub                     | Version control and collaborative development platform.                                                                                                                                                                                                                                       | stdio           | No    | `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server`                                                                                                                                | -                                                                                                                                                            |
| -     | Slack                      | Team communication and collaboration platform.                                                                                                                                                                                                                                                | sse             | Yes   | [https://mcp.slack.com/mcp](https://mcp.slack.com/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Notion                     | All-in-one workspace for notes, docs, and project management.                                                                                                                                                                                                                                 | sse             | Yes   | [https://mcp.notion.com/mcp](https://mcp.notion.com/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Figma                      | Design and collaboration platform for teams.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.figma.com/mcp](https://mcp.figma.com/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Context7                   | Up-to-date code documentation.                                                                                                                                                                                                                                                                | sse             | No    | [https://mcp.context7.com/mcp](https://mcp.context7.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Linear                     | Issue tracking and project management for development teams.                                                                                                                                                                                                                                  | stdio, sse      | Yes   | [https://mcp.linear.app/mcp](https://mcp.linear.app/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Playwright                 | End-to-end browser testing.                                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @playwright/mcp@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | shadcn/ui                  | Use the shadcn/ui MCP server to browse, search, and install components from registries.                                                                                                                                                                                                       | stdio           | No    | `npx shadcn@latest mcp`                                                                                                                                                                                              | -                                                                                                                                                            |
| -     | Sentry                     | Error tracking and performance monitoring.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.sentry.dev/mcp](https://mcp.sentry.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Salesforce DX              | Interact with Salesforce orgs, manage metadata, data, and development workflows.                                                                                                                                                                                                              | stdio           | No    | `npx -y @salesforce/mcp --orgs DEFAULT_TARGET_ORG`                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Supabase                   | Create and manage Supabase projects.                                                                                                                                                                                                                                                          | sse             | Yes   | [https://mcp.supabase.com/mcp](https://mcp.supabase.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Vercel                     | Manage projects and deployments on Vercel.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.vercel.com](https://mcp.vercel.com)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | GitLab                     | DevSecOps platform for code, CI/CD, and security.                                                                                                                                                                                                                                             | http            | No    | [https://your-gitlab-instance.com/api/v4/mcp](https://your-gitlab-instance.com/api/v4/mcp)                                                                                                                           | [https://docs.gitlab.com/user/gitlab\_duo/model\_context\_protocol/mcp\_server/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/) |
| -     | PostHog                    | Analytics, error tracking, and feature flags.                                                                                                                                                                                                                                                 | sse             | No    | `npx -y mcp-remote@latest https://mcp.posthog.com/sse --header Authorization:${POSTHOG_AUTH_HEADER}`                                                                                                                 | -                                                                                                                                                            |
| -     | Netlify                    | Build and deploy web projects.                                                                                                                                                                                                                                                                | stdio           | No    | `npx -y @netlify/mcp`                                                                                                                                                                                                | -                                                                                                                                                            |
| -     | Heroku                     | Manage Heroku apps and resources.                                                                                                                                                                                                                                                             | stdio           | No    | `npx -y @heroku/mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| -     | Postman                    | API collaboration and testing.                                                                                                                                                                                                                                                                | stdio           | No    | [https://mcp.postman.com/minimal](https://mcp.postman.com/minimal)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Prisma                     | Manage Prisma Postgres databases, including creating new instances and running schema migrations.                                                                                                                                                                                             | stdio, sse      | Yes   | [https://mcp.prisma.io/mcp](https://mcp.prisma.io/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| SAP   | CAP                        | SAP Cloud Application Programming Model development.                                                                                                                                                                                                                                          | stdio           | No    | `npx -y @cap-js/mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| SAP   | SAP Fiori                  | SAP Fiori UI elements and application development.                                                                                                                                                                                                                                            | stdio           | No    | `npx --yes @sap-ux/fiori-mcp-server@latest fiori-mcp`                                                                                                                                                                | -                                                                                                                                                            |
| SAP   | SAP Mobile Development Kit | SAP Mobile Development Kit tools and templates.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @sap/mdk-mcp-server`                                                                                                                                                                                         | -                                                                                                                                                            |
| SAP   | UI5 MCP Server             | OpenUI5 and SAPUI5 web application development.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @ui5/mcp-server@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | MongoDB                    | Manage MongoDB data and deployments.                                                                                                                                                                                                                                                          | stdio           | No    | `npx -y mongodb-mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| -     | dbt Labs                   | dbt CLI, Semantic Layer, and Discovery API.                                                                                                                                                                                                                                                   | stdio           | No    | `uvx dbt-mcp`                                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Atlassian                  | Project management and collaboration tools including Jira and Confluence.                                                                                                                                                                                                                     | sse             | Yes   | [https://mcp.atlassian.com/v1/mcp](https://mcp.atlassian.com/v1/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | DuckDB                     | In-process SQL OLAP database for local analytics.                                                                                                                                                                                                                                             | stdio           | No    | `uvx mcp-server-motherduck --db-path :memory:`                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Braintrust                 | Access to the documentation, experiments, and logs in Braintrust.                                                                                                                                                                                                                             | sse             | Yes   | [https://api.braintrust.dev/mcp](https://api.braintrust.dev/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Browserbase                | Headless browser sessions for agents.                                                                                                                                                                                                                                                         | stdio           | No    | `npx @browserbasehq/mcp`                                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Chrome DevTools            | Debug web pages directly in Chrome with DevTools debugging capabilities and performance insights.                                                                                                                                                                                             | stdio           | No    | `npx chrome-devtools-mcp@latest`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | ClickUp                    | Project management and collaboration for teams & agents.                                                                                                                                                                                                                                      | http            | Yes   | [https://mcp.clickup.com/mcp](https://mcp.clickup.com/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | Convex                     | Interact with your Convex deployment - query tables, run functions, manage environment variables, and analyze logs.                                                                                                                                                                           | stdio           | No    | `npx -y convex@latest mcp start`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Shopify                    | Shopify app development tools.                                                                                                                                                                                                                                                                | stdio           | No    | `npx -y @shopify/dev-mcp@latest`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | snyk                       | Vulnerability scanning of your codebase.                                                                                                                                                                                                                                                      | stdio           | No    | `npx -y snyk@latest mcp -t stdio`                                                                                                                                                                                    | -                                                                                                                                                            |
| -     | Hugging Face               | Access the Hugging Face Hub and Gradio MCP Servers.                                                                                                                                                                                                                                           | sse             | No    | [https://hf.co/mcp](https://hf.co/mcp)                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Wix                        | Build and manage Wix sites.                                                                                                                                                                                                                                                                   | sse             | No    | [https://mcp.wix.com/mcp](https://mcp.wix.com/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Semgrep                    | Scan code for security vulnerabilities.                                                                                                                                                                                                                                                       | stdio           | No    | `semgrep mcp`                                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | LaunchDarkly               | Feature flags as a service.                                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y --package @launchdarkly/mcp-server -- mcp start --api-key api-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`                                                                                                          | -                                                                                                                                                            |
| -     | Statsig                    | Feature flags and experimentation platform.                                                                                                                                                                                                                                                   | sse             | No    | [https://api.statsig.com/v1/mcp](https://api.statsig.com/v1/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Endor Labs                 | Security risk insights for code.                                                                                                                                                                                                                                                              | stdio           | No    | `endorctl ai-tools mcp-server`                                                                                                                                                                                       | -                                                                                                                                                            |
| -     | InstantDB                  | Query and manage InstantDB.                                                                                                                                                                                                                                                                   | sse             | No    | [https://mcp.instantdb.com/mcp](https://mcp.instantdb.com/mcp)                                                                                                                                                       | -                                                                                                                                                            |
| -     | Tinybird                   | Real-time analytics APIs.                                                                                                                                                                                                                                                                     | stdio           | No    | `npx -y mcp-remote https://cloud.tinybird.co/mcp?token=TB_TOKEN`                                                                                                                                                     | -                                                                                                                                                            |
| -     | Neon                       | Manage Neon Postgres.                                                                                                                                                                                                                                                                         | sse             | Yes   | [https://mcp.neon.tech/mcp](https://mcp.neon.tech/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Socket                     | Analyze and secure dependencies.                                                                                                                                                                                                                                                              | sse             | No    | [https://mcp.socket.dev/](https://mcp.socket.dev/)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Pipedream                  | Connect to APIs and workflows.                                                                                                                                                                                                                                                                | sse             | No    | [https://mcp.pipedream.net/\<uuid>/\<app>](https://mcp.pipedream.net/\<uuid>/\<app>)                                                                                                                                 | -                                                                                                                                                            |
| -     | Auth0                      | Manage Auth0 resources.                                                                                                                                                                                                                                                                       | stdio           | No    | `npx -y @auth0/auth0-mcp-server run`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Honeycomb                  | Query observability data and SLOs.                                                                                                                                                                                                                                                            | sse             | No    | [https://mcp.honeycomb.io/mcp](https://mcp.honeycomb.io/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | PagerDuty                  | Manage incidents and alerts.                                                                                                                                                                                                                                                                  | stdio           | No    | `uvx pagerduty-mcp --enable-write-tools`                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Graphite                   | Create and manage stacked PRs.                                                                                                                                                                                                                                                                | stdio           | No    | `gt mcp`                                                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Railway                    | Deploy apps, databases, and services.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @railway/mcp-server`                                                                                                                                                                                         | -                                                                                                                                                            |
| -     | Replicate                  | Search, discover, compare, and run AI models with a cloud API.                                                                                                                                                                                                                                | sse             | Yes   | [https://mcp.replicate.com/sse](https://mcp.replicate.com/sse)                                                                                                                                                       | -                                                                                                                                                            |
| -     | AWS Documentation          | Access AWS documentation, search, and get recommendations.                                                                                                                                                                                                                                    | stdio           | No    | `uvx awslabs.aws-documentation-mcp-server@latest`                                                                                                                                                                    | -                                                                                                                                                            |
| -     | Select Star                | Data catalog, lineage, and context.                                                                                                                                                                                                                                                           | stdio           | No    | `npx -y mcp-remote@latest https://mcp.production.selectstar.com/mcp --header Authorization:${SELECT_STAR_TOKEN}`                                                                                                     | -                                                                                                                                                            |
| -     | SonarQube                  | Analyze code with SonarQube.                                                                                                                                                                                                                                                                  | stdio           | No    | `docker run -i --rm -e SONARQUBE_TOKEN -e SONARQUBE_URL mcp/sonarqube`                                                                                                                                               | -                                                                                                                                                            |
| -     | MS Learn Docs              | Search Microsoft docs.                                                                                                                                                                                                                                                                        | sse             | No    | [https://learn.microsoft.com/api/mcp](https://learn.microsoft.com/api/mcp)                                                                                                                                           | -                                                                                                                                                            |
| -     | Stripe                     | Payment processing APIs.                                                                                                                                                                                                                                                                      | stdio, sse      | No    | `npx -y @stripe/mcp --tools=all`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | PayPal                     | Payment APIs.                                                                                                                                                                                                                                                                                 | sse             | Yes   | [https://mcp.paypal.com/sse](https://mcp.paypal.com/sse)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Plaid                      | Access financial account data.                                                                                                                                                                                                                                                                | sse             | No    | [https://api.dashboard.plaid.com/mcp/sse](https://api.dashboard.plaid.com/mcp/sse)                                                                                                                                   | -                                                                                                                                                            |
| -     | firecrawl                  | The web crawling, scraping, and search API for AI                                                                                                                                                                                                                                             | sse             | No    | `npx -y firecrawl-mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Corridor                   | Proactively enforce security guardrails to reduce vulnerabilities.                                                                                                                                                                                                                            | https           | No    | [https://app.corridor.dev/api/mcp](https://app.corridor.dev/api/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Amplitude                  | Behavior analytics and experimentation platform for product data insights.                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.amplitude.com/mcp](https://mcp.amplitude.com/mcp)                                                                                                                                                       | -                                                                                                                                                            |
| -     | Astro docs server          | This server provides up-to-date access to the official Astro documentation.                                                                                                                                                                                                                   | sse             | No    | [https://mcp.docs.astro.build/mcp](https://mcp.docs.astro.build/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Mercado Pago               | Access Mercado Pago docs.                                                                                                                                                                                                                                                                     | stdio           | No    | [https://mcp.mercadopago.com/mcp](https://mcp.mercadopago.com/mcp)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Mercado Libre              | Access Mercado Libre docs.                                                                                                                                                                                                                                                                    | sse             | No    | [https://mcp.mercadolibre.com/mcp](https://mcp.mercadolibre.com/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Apify                      | Extract data from any website with thousands of scrapers, crawlers, and automations                                                                                                                                                                                                           | streamable-http | Yes   | [https://mcp.apify.com](https://mcp.apify.com)                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Render                     | Manage your Render services.                                                                                                                                                                                                                                                                  | streamable-http | No    | [https://mcp.render.com/mcp](https://mcp.render.com/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Azure DevOps               | Interact with Azure DevOps work items, pull requests, builds, and releases.                                                                                                                                                                                                                   | stdio           | No    | `npx -y @azure-devops/mcp {organization}`                                                                                                                                                                            | -                                                                                                                                                            |
| -     | Webflow                    | Webflow's MCP server enhances an agent's understanding of your Webflow projects. It's built on Webflow's APIs, exposing them as tools your AI agent can use to create elements, styles, and variables on the canvas, as well as manage collections, custom code, assets, and other site data. | sse             | Yes   | [https://mcp.webflow.com/sse](https://mcp.webflow.com/sse)                                                                                                                                                           | -                                                                                                                                                            |
| -     | terraform                  | Generate and automate Terraform workflows.                                                                                                                                                                                                                                                    | stdio           | No    | `docker run --rm -i -e TFE_ADDRESS -e TFE_TOKEN -e ENABLE_TF_OPERATIONS hashicorp/terraform-mcp-server:latest`                                                                                                       | -                                                                                                                                                            |
| -     | vault                      | Store and manage secrets.                                                                                                                                                                                                                                                                     | stdio           | No    | `docker run --rm -i -e VAULT_ADDR -e VAULT_TOKEN -e VAULT_NAMESPACE hashicorp/vault-mcp-server:latest`                                                                                                               | -                                                                                                                                                            |
| -     | Browser Use                | The Browser Use MCP server provides Cursor agents access to browser-use documentation. This gives AI assistants deep context about the browser-use library when helping you write code.                                                                                                       | sse             | No    | [https://docs.browser-use.com/mcp](https://docs.browser-use.com/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Sanity                     | Create, query, and manage Sanity content, releases, datasets, and schemas.                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.sanity.io](https://mcp.sanity.io)                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Airwallex Developer MCP    | Tools to search Airwallex docs and interact with the Airwallex sandbox environment while integrating with Airwallex APIs.                                                                                                                                                                     | stdio           | No    | `npx -y @airwallex/developer-mcp@latest`                                                                                                                                                                             | [https://www.airwallex.com/docs/developer-tools/ai/developer-mcp](https://www.airwallex.com/docs/developer-tools/ai/developer-mcp)                           |
| -     | Dynatrace                  | Enterprise observability platform for real-time monitoring and AI-powered insights.                                                                                                                                                                                                           | sse             | Yes   | [https://\{environmentId}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp](https://\{environmentId}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp) | -                                                                                                                                                            |
| -     | Arcade                     | Create and manage MCP gateways connecting 100+ integrations.                                                                                                                                                                                                                                  | sse             | Yes   | [https://ctl.arcade.dev/mcp](https://ctl.arcade.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Embrace                    | Mobile app performance monitoring and crash analytics.                                                                                                                                                                                                                                        | sse             | Yes   | [https://mcp.embrace.io/mcp](https://mcp.embrace.io/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | CodeSherlock               | AI code analysis for security, quality, and compliance checks.                                                                                                                                                                                                                                | stdio           | No    | `npx -y @codesherlock/codesherlock-mcp-server`                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Kyomi                      | Query data warehouses with natural language and institutional knowledge.                                                                                                                                                                                                                      | sse             | Yes   | [https://app.kyomi.ai/mcp](https://app.kyomi.ai/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Pendo                      | Product analytics and user behavior insights.                                                                                                                                                                                                                                                 | sse             | Yes   | [https://app.pendo.io/mcp/v0/shttp](https://app.pendo.io/mcp/v0/shttp)                                                                                                                                               | -                                                                                                                                                            |
| -     | SearchAPI                  | Real-time search engine API for AI applications.                                                                                                                                                                                                                                              | sse             | No    | [https://www.searchapi.io/mcp?token=\<your\_integration\_token>](https://www.searchapi.io/mcp?token=\<your_integration_token>)                                                                                       | -                                                                                                                                                            |
| -     | Defang                     | Deploy apps to AWS, GCP, and DigitalOcean from Docker Compose.                                                                                                                                                                                                                                | stdio           | No    | `npx -y defang mcp serve --client=cursor`                                                                                                                                                                            | -                                                                                                                                                            |
| -     | WordPress.com              | Manage WordPress.com sites, posts, and content.                                                                                                                                                                                                                                               | stdio           | Yes   | `npx -y mcp-remote https://public-api.wordpress.com/wpcom/v2/mcp/v1`                                                                                                                                                 | -                                                                                                                                                            |
| -     | Luciq                      | Query crash reports and observability data from your IDE.                                                                                                                                                                                                                                     | sse             | No    | [https://api.instabug.com/api/mcp](https://api.instabug.com/api/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | alphaXiv                   | Search ML research papers and analyze PDFs.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://api.alphaxiv.org/mcp/v1](https://api.alphaxiv.org/mcp/v1)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Codve                      | Logic-based code verification with confidence scores.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @codve/mcp-server`                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Arize AX                   | LLM tracing and instrumentation guidance.                                                                                                                                                                                                                                                     | stdio           | No    | `uvx arize-tracing-assistant@latest`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | MotherDuck                 | Query and explore MotherDuck cloud databases.                                                                                                                                                                                                                                                 | sse             | Yes   | [https://api.motherduck.com/mcp](https://api.motherduck.com/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Glean                      | Enterprise knowledge search and context.                                                                                                                                                                                                                                                      | sse             | No    | [https://\{instance}-be.glean.com/mcp/\{server-name}](https://\{instance}-be.glean.com/mcp/\{server-name})                                                                                                           | -                                                                                                                                                            |
| -     | incident.io                | Incident management and alerting.                                                                                                                                                                                                                                                             | stdio           | No    | `npx -y @incident-io/mcp`                                                                                                                                                                                            | -                                                                                                                                                            |
| -     | Firebase                   | Manage Firebase projects, Auth, Firestore, and more.                                                                                                                                                                                                                                          | stdio           | No    | `npx -y firebase-tools@latest mcp`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Aikido Security            | Security scanning in your AI coding workflow.                                                                                                                                                                                                                                                 | stdio           | No    | `npx -y @aikidosec/mcp`                                                                                                                                                                                              | -                                                                                                                                                            |
| -     | Mixpanel                   | Product analytics through natural language queries.                                                                                                                                                                                                                                           | stdio           | No    | `npx -y mcp-remote https://mcp.mixpanel.com/mcp --allow-http`                                                                                                                                                        | -                                                                                                                                                            |
| -     | Windsor.ai                 | Query analytics data across marketing platforms.                                                                                                                                                                                                                                              | sse             | No    | [https://mcp.windsor.ai](https://mcp.windsor.ai)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Circleback                 | Search meeting notes and transcripts for dev context.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y mcp-remote https://app.circleback.ai/api/mcp`                                                                                                                                                                | -                                                                                                                                                            |
| -     | Tauri                      | Build and debug Tauri desktop/mobile apps with screenshots and DOM state.                                                                                                                                                                                                                     | stdio           | No    | `npx -y @hypothesi/tauri-mcp-server`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Vantage                    | Cloud cost management and FinOps insights.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.vantage.sh/mcp](https://mcp.vantage.sh/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Sidemail                   | Send transactional emails and manage email workflows.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @sidemail/mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Databend                   | AI-native cloud data warehouse analytics.                                                                                                                                                                                                                                                     | stdio           | No    | `uv tool run mcp-databend`                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Kubit                      | Analytics platform with natural language queries.                                                                                                                                                                                                                                             | sse             | Yes   | [https://mcp.kubit.ai/mcp](https://mcp.kubit.ai/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | CodeScene                  | Code health insights and technical debt analysis.                                                                                                                                                                                                                                             | stdio           | No    | `docker run -i --rm -e CS_ACCESS_TOKEN codescene/codescene-mcp`                                                                                                                                                      | -                                                                                                                                                            |
| -     | Vale                       | Style and grammar linting for documentation.                                                                                                                                                                                                                                                  | stdio           | No    | `vale-cli`                                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Fluid Attacks              | Security vulnerability scanning and analysis.                                                                                                                                                                                                                                                 | sse             | No    | [https://app.fluidattacks.com/mcp/messages/](https://app.fluidattacks.com/mcp/messages/)                                                                                                                             | -                                                                                                                                                            |
| -     | Clarity                    | Microsoft user behavior analytics.                                                                                                                                                                                                                                                            | stdio           | No    | `npx -y @microsoft/clarity-mcp-server@latest`                                                                                                                                                                        | -                                                                                                                                                            |
| -     | You.com                    | AI-powered web search and research.                                                                                                                                                                                                                                                           | sse             | No    | [https://api.you.com/mcp](https://api.you.com/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | TestDino                   | Connect AI tools to testing platform.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y testdino-mcp`                                                                                                                                                                                                | -                                                                                                                                                            |
| -     | Kernel                     | Fast infrastructure for agents to access the internet.                                                                                                                                                                                                                                        | sse             | Yes   | [https://mcp.onkernel.com/mcp](https://mcp.onkernel.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Angular                    | Angular framework documentation and examples.                                                                                                                                                                                                                                                 | stdio           | No    | `npx -y @angular/cli mcp`                                                                                                                                                                                            | -                                                                                                                                                            |
| -     | AWS                        | Access AWS services through natural language.                                                                                                                                                                                                                                                 | stdio           | No    | `uvx mcp-proxy-for-aws@latest https://aws-mcp.us-east-1.api.aws/mcp --metadata AWS_REGION=us-west-2`                                                                                                                 | -                                                                                                                                                            |
| -     | Uno Platform               | Cross-platform .NET application development.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.platform.uno/v1](https://mcp.platform.uno/v1)                                                                                                                                                           | -                                                                                                                                                            |
| -     | DBHub                      | Universal database connector for MySQL, PostgreSQL, SQL Server.                                                                                                                                                                                                                               | stdio           | No    | `npx @bytebase/dbhub --transport stdio --dsn postgres://user:password@localhost:5432/dbname`                                                                                                                         | -                                                                                                                                                            |
| -     | CoreStory                  | Access PRDs, technical specs, and project context.                                                                                                                                                                                                                                            | http            | No    | [https://c2s.corestory.ai/mcp](https://c2s.corestory.ai/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Ref                        | Token-efficient documentation search.                                                                                                                                                                                                                                                         | sse             | Yes   | [https://api.ref.tools/mcp](https://api.ref.tools/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Perplexity                 | AI-powered web search and research.                                                                                                                                                                                                                                                           | stdio           | No    | `npx -y @perplexity-ai/mcp-server`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Checkmarx                  | Application security testing and vulnerability scanning.                                                                                                                                                                                                                                      | sse             | Yes   | [https://\{tenant}/api/security-mcp/mcp](https://\{tenant}/api/security-mcp/mcp)                                                                                                                                     | -                                                                                                                                                            |
| -     | SafeDep Vet                | Vet open source packages for security issues.                                                                                                                                                                                                                                                 | stdio           | No    | `docker run --rm -i ghcr.io/safedep/vet:latest -s server mcp`                                                                                                                                                        | -                                                                                                                                                            |
| -     | Elasticsearch              | Query logs and data from the ELK stack.                                                                                                                                                                                                                                                       | stdio           | No    | `npx mcp-remote ${KIBANA_URL}/api/agent_builder/mcp --header Authorization:${AUTH_HEADER}`                                                                                                                           | -                                                                                                                                                            |
| -     | Unleash                    | Open source feature flags management.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @unleash/mcp@latest`                                                                                                                                                                                         | -                                                                                                                                                            |
| -     | Tigris                     | S3-compatible object storage management.                                                                                                                                                                                                                                                      | sse             | Yes   | [https://mcp.storage.dev/mcp](https://mcp.storage.dev/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | DevRev                     | Work item management for development teams.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://api.devrev.ai/mcp/v1](https://api.devrev.ai/mcp/v1)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Mux                        | Video platform for uploads, streaming, and analytics.                                                                                                                                                                                                                                         | sse             | Yes   | [https://mcp.mux.com](https://mcp.mux.com)                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Hex                        | Data analytics platform for insights and exploration.                                                                                                                                                                                                                                         | sse             | Yes   | [https://app.hex.tech/mcp](https://app.hex.tech/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Stack Overflow             | Access trusted technical Q\&A from Stack Overflow.                                                                                                                                                                                                                                            | stdio           | No    | `npx mcp-remote mcp.stackoverflow.com`                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Fellow                     | AI meeting notes, transcripts, and action items.                                                                                                                                                                                                                                              | sse             | Yes   | [https://fellow.app/mcp](https://fellow.app/mcp)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | LiveKit                    | Real-time communication documentation and examples.                                                                                                                                                                                                                                           | sse             | No    | [https://docs.livekit.io/mcp](https://docs.livekit.io/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | GrowthBook                 | Feature flags and A/B testing platform.                                                                                                                                                                                                                                                       | stdio           | No    | `npx -y @growthbook/mcp@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | Octopus Deploy             | Manage deployments, releases, and runbooks.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @octopusdeploy/mcp-server`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Builder.io                 | Headless CMS content management.                                                                                                                                                                                                                                                              | sse             | No    | [https://cdn.builder.io/api/v1/mcp/builder-content](https://cdn.builder.io/api/v1/mcp/builder-content)                                                                                                               | -                                                                                                                                                            |
| -     | DevExpress                 | DevExpress component library documentation.                                                                                                                                                                                                                                                   | sse             | No    | [https://api.devexpress.com/mcp/docs](https://api.devexpress.com/mcp/docs)                                                                                                                                           | -                                                                                                                                                            |
| -     | Cloudinary                 | Media asset management and transformation.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://asset-management.mcp.cloudinary.com/sse](https://asset-management.mcp.cloudinary.com/sse)                                                                                                                   | -                                                                                                                                                            |
| -     | Cloudflare                 | Cloudflare documentation and reference.                                                                                                                                                                                                                                                       | sse             | No    | [https://docs.mcp.cloudflare.com/mcp](https://docs.mcp.cloudflare.com/mcp)                                                                                                                                           | -                                                                                                                                                            |
| -     | Shuttle                    | Deploy Rust applications to the cloud.                                                                                                                                                                                                                                                        | stdio           | No    | `shuttle mcp start`                                                                                                                                                                                                  | -                                                                                                                                                            |
| -     | ConfigCat                  | Feature flag management for teams.                                                                                                                                                                                                                                                            | stdio           | No    | `npx -y @configcat/mcp-server`                                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Coralogix                  | Observability platform for logs, metrics, and traces.                                                                                                                                                                                                                                         | stdio           | No    | `npx mcp-remote ${CORALOGIX_MCP_ENDPOINT} --header Authorization:${CORALOGIX_API_KEY}`                                                                                                                               | -                                                                                                                                                            |
| -     | Svelte                     | Svelte framework documentation and guidance.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.svelte.dev/mcp](https://mcp.svelte.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Scout APM                  | Application performance monitoring and insights.                                                                                                                                                                                                                                              | stdio           | No    | `docker run --rm -i --env SCOUT_API_KEY scoutapp/scout-mcp-local`                                                                                                                                                    | -                                                                                                                                                            |
| -     | Axiom                      | Log analytics, monitoring, and APL queries.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://mcp.axiom.co/mcp](https://mcp.axiom.co/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Customer.io                | Manage segments, users, and marketing automation.                                                                                                                                                                                                                                             | sse             | Yes   | [https://mcp.customer.io/mcp](https://mcp.customer.io/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | Bitly                      | URL shortening and link management.                                                                                                                                                                                                                                                           | stdio           | No    | `npx mcp-remote https://api-ssl.bitly.com/v4/mcp --header Authorization: Bearer ${AUTH_TOKEN}`                                                                                                                       | -                                                                                                                                                            |
| -     | Devopness                  | DevOps automation for cloud infrastructure.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://mcp.devopness.com/mcp/](https://mcp.devopness.com/mcp/)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Jam                        | Screen recorder with auto context for debugging.                                                                                                                                                                                                                                              | sse             | Yes   | [https://mcp.jam.dev/mcp](https://mcp.jam.dev/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Webvizio                   | Bug feedback with screenshots and browser logs.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @webvizio/mcp-server`                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Supadata                   | Video and web scraping for AI applications.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @supadata/mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Bitrise                    | Mobile CI/CD and build management.                                                                                                                                                                                                                                                            | sse             | No    | [https://mcp.bitrise.io](https://mcp.bitrise.io)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Harness                    | CI/CD and software delivery platform.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @harness/mcp-server stdio`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | DryRun Security            | Security analysis insights and trends.                                                                                                                                                                                                                                                        | stdio           | No    | `npx -y mcp-remote https://insights-mcp.dryrun.security/insights/mcp --transport http-only`                                                                                                                          | -                                                                                                                                                            |
| -     | OX Security                | Security platform for AI agent integration.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y mcp-remote@0.1.18 https://api.cloud.ox.security/api/mcp --header Authorization:${AUTH_TOKEN}`                                                                                                                | -                                                                                                                                                            |
| -     | Zapier                     | Automate workflows with 30,000+ actions across 8,000+ apps. Build once, orchestrate everywhere.                                                                                                                                                                                               | streamableHttp  | Yes   | [https://mcp.zapier.com/api/mcp/s/•••••••/mcp](https://mcp.zapier.com/api/mcp/s/•••••••/mcp)                                                                                                                         | -                                                                                                                                                            |
| -     | Okahu                      | Access to traces and debug your AI agent apps                                                                                                                                                                                                                                                 | https           | No    | [https://mcp.okahu.co/mcp](https://mcp.okahu.co/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Scalekit                   | Auth stack for AI applications. Manage environments and connections.                                                                                                                                                                                                                          | http            | Yes   | [https://mcp.scalekit.com/](https://mcp.scalekit.com/)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Chakra UI                  | Access Chakra UI component library, design tokens, and migration guidance.                                                                                                                                                                                                                    | stdio           | No    | `npx -y @chakra-ui/react-mcp`                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Alpha Vantage              | Financial data API for stocks, forex, crypto, and economic indicators.                                                                                                                                                                                                                        | http            | No    | [https://mcp.alphavantage.co/mcp](https://mcp.alphavantage.co/mcp)                                                                                                                                                   | -                                                                                                                                                            |

### Why use MCP?

MCP connects Cursor to external systems and data. Instead of explaining your project structure repeatedly, integrate directly with your tools.

Write MCP servers in any language that can print to `stdout` or serve an HTTP endpoint - Python, JavaScript, Go, etc.

### How it works

MCP servers expose capabilities through the protocol, connecting Cursor to external tools or data sources.

Cursor supports three transport methods:

| Transport             | Execution environment | Deployment       | Users          | Input                   | Auth   |
| :-------------------- | :-------------------- | :--------------- | :------------- | :---------------------- | :----- |
| **`stdio`**           | Local                 | Cursor manages   | Single user    | Shell command           | Manual |
| **`SSE`**             | Local/Remote          | Deploy as server | Multiple users | URL to an SSE endpoint  | OAuth  |
| **`Streamable HTTP`** | Local/Remote          | Deploy as server | Multiple users | URL to an HTTP endpoint | OAuth  |

### Protocol support

Cursor supports these MCP protocol capabilities:

| Feature         | Support   | Description                                                     |
| :-------------- | :-------- | :-------------------------------------------------------------- |
| **Tools**       | Supported | Functions for the AI model to execute                           |
| **Prompts**     | Supported | Templated messages and workflows for users                      |
| **Resources**   | Supported | Structured data sources that can be read and referenced         |
| **Roots**       | Supported | Server-initiated inquiries into URI or filesystem boundaries    |
| **Elicitation** | Supported | Server-initiated requests for additional information from users |

## Installing MCP servers

### One-click installation

Install MCP servers from our collection and authenticate with OAuth.

### Browse MCP Tools

Browse available MCP servers

### Add to Cursor Button

Create an "Add to Cursor" button

### Using `mcp.json`

Configure custom MCP servers with a JSON file:

```json title="CLI Server - Node.js"
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "mcp-server"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

```json title="CLI Server - Python"
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["mcp-server.py"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

```json title="Remote Server"
// MCP server using HTTP or SSE - runs on a server
{
  "mcpServers": {
    "server-name": {
      "url": "http://localhost:3000/mcp",
      "headers": {
        "API_KEY": "value"
      }
    }
  }
}
```

### Static OAuth for remote servers

For MCP servers that use OAuth, you can provide **static OAuth client credentials** in `mcp.json` instead of dynamic client registration. Use this when:

- The MCP provider gives you a fixed **Client ID** (and optionally **Client Secret**)
- The provider requires **whitelisting a redirect URL** (e.g. Figma, Linear)
- The provider does not support OAuth 2.0 Dynamic Client Registration

Add an `auth` object to remote server entries that use `url`:

```json title="Remote Server with Static OAuth"
{
  "mcpServers": {
    "oauth-server": {
      "url": "https://api.example.com/mcp",
      "auth": {
        "CLIENT_ID": "your-oauth-client-id",
        "CLIENT_SECRET": "your-client-secret",
        "scopes": ["read", "write"]
      }
    }
  }
}
```

| Field              | Required | Description                                                                                                                   |
| :----------------- | :------- | :---------------------------------------------------------------------------------------------------------------------------- |
| **CLIENT\_ID**     | Yes      | OAuth 2.0 Client ID from the MCP provider                                                                                     |
| **CLIENT\_SECRET** | No       | OAuth 2.0 Client Secret (if the provider uses confidential clients)                                                           |
| **scopes**         | No       | OAuth scopes to request. If omitted, Cursor will use `/.well-known/oauth-authorization-server` to discover `scopes_supported` |

#### Static redirect URL

Cursor uses a **fixed OAuth redirect URL** for all MCP servers:

```text
cursor://anysphere.cursor-mcp/oauth/callback
```

When configuring the MCP provider's OAuth app, register this URL as an allowed redirect URI. The server is identified via the OAuth `state` parameter, so one redirect URL works for all MCP servers.

#### Combining with config interpolation

`auth` values support the same interpolation as other fields:

```json
{
  "mcpServers": {
    "oauth-server": {
      "url": "https://api.example.com/mcp",
      "auth": {
        "CLIENT_ID": "${env:MCP_CLIENT_ID}",
        "CLIENT_SECRET": "${env:MCP_CLIENT_SECRET}"
      }
    }
  }
}
```

Use environment variables for Client ID and Client Secret instead of hardcoding them.

### STDIO server configuration

For STDIO servers (local command-line servers), configure these fields in your `mcp.json`:

| Field       | Required | Description                                                                                             | Examples                                  |
| :---------- | :------- | :------------------------------------------------------------------------------------------------------ | :---------------------------------------- |
| **type**    | Yes      | Server connection type                                                                                  | `"stdio"`                                 |
| **command** | Yes      | Command to start the server executable. Must be available on your system path or contain its full path. | `"npx"`, `"node"`, `"python"`, `"docker"` |
| **args**    | No       | Array of arguments passed to the command                                                                | `["server.py", "--port", "3000"]`         |
| **env**     | No       | Environment variables for the server                                                                    | `{"API_KEY": "${env:api-key}"}`           |
| **envFile** | No       | Path to an environment file to load more variables                                                      | `".env"`, `"${workspaceFolder}/.env"`     |

The `envFile` option is only available for STDIO servers. Remote servers (HTTP/SSE) do not support `envFile`. For remote servers, use [config interpolation](https://cursor.com/docs/context/mcp.md#config-interpolation) with environment variables set in your shell profile or system environment instead.

### Using the Extension API

For programmatic MCP server registration, Cursor provides an extension API that allows dynamic configuration without modifying `mcp.json` files. This is particularly useful for enterprise environments and automated setup workflows.

### MCP Extension API Reference

Learn how to register MCP servers programmatically using
`vscode.cursor.mcp.registerServer()`

### Configuration locations

### Project Configuration

Create `.cursor/mcp.json` in your project for project-specific tools.

### Global Configuration

Create `~/.cursor/mcp.json` in your home directory for tools available everywhere.

### Config interpolation

Use variables in `mcp.json` values. Cursor resolves variables in these fields: `command`, `args`, `env`, `url`, and `headers`.

Supported syntax:

- `${env:NAME}` environment variables
- `${userHome}` path to your home folder
- `${workspaceFolder}` project root (the folder that contains `.cursor/mcp.json`)
- `${workspaceFolderBasename}` name of the project root
- `${pathSeparator}` and `${/}` OS path separator

Examples

```json
{
  "mcpServers": {
    "local-server": {
      "command": "python",
      "args": ["${workspaceFolder}/tools/mcp_server.py"],
      "env": {
        "API_KEY": "${env:API_KEY}"
      }
    }
  }
}
```

```json
{
  "mcpServers": {
    "remote-server": {
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${env:MY_SERVICE_TOKEN}"
      }
    }
  }
}
```

### Authentication

MCP servers use environment variables for authentication. Pass API keys and tokens through the config.

Cursor supports OAuth for servers that require it.

## Using MCP in chat

Agent automatically uses MCP tools listed under `Available Tools` when relevant. This includes [Plan Mode](https://cursor.com/docs/agent/modes.md#plan). Ask for a specific tool by name or describe what you need. Enable or disable tools from settings.

### Toggling tools

Enable or disable MCP tools directly from the chat interface. Click a tool name in the tools list to toggle it. Disabled tools won't be loaded into context or available to Agent.

[Media](/docs-static/images/context/mcp/tool-toggle.mp4)

### Tool approval

Agent asks for approval before using MCP tools by default. Click the arrow next to the tool name to see arguments.

![Tool confirmation prompt](/docs-static/images/context/mcp/tool-confirm.png)

#### Auto-run

Enable auto-run for Agent to use MCP tools without asking. Works like terminal commands. Read more about Auto-run settings [here](https://cursor.com/docs/agent/tools.md#auto-run).

### Tool response

Cursor shows the response in chat with expandable views of arguments and responses:

![MCP tool call result](/docs-static/images/context/mcp/tool-call.png)

### Images as context

MCP servers can return images - screenshots, diagrams, etc. Return them as base64 encoded strings:

```js
const RED_CIRCLE_BASE64 = "/9j/4AAQSkZJRgABAgEASABIAAD/2w...";
// ^ full base64 clipped for readability

server.tool("generate_image", async (params) => {
  return {
    content: [
      {
        type: "image",
        data: RED_CIRCLE_BASE64,
        mimeType: "image/jpeg",
      },
    ],
  };
});
```

See this [example server](https://github.com/msfeldstein/mcp-test-servers/blob/main/src/image-server.js) for implementation details. Cursor attaches returned images to the chat. If the model supports images, it analyzes them.

## Security considerations

When installing MCP servers, consider these security practices:

- **Verify the source**: Only install MCP servers from trusted developers and repositories
- **Review permissions**: Check what data and APIs the server will access
- **Limit API keys**: Use restricted API keys with minimal required permissions
- **Audit code**: For critical integrations, review the server's source code

Remember that MCP servers can access external services and execute code on your behalf. Always understand what a server does before installation.

## Real-world examples

For practical examples of MCP in action, see our [Web Development guide](https://cursor.com/docs/cookbook/web-development.md) which demonstrates integrating Linear, Figma, and browser tools into your development workflow.

## FAQ

### What's the point of MCP servers?

MCP servers connect Cursor to external tools like Google Drive, Notion, and
other services to bring docs and requirements into your coding workflow.

### How do I debug MCP server issues?

View MCP logs by:

1. Open the Output panel in Cursor (Cmd+Shift+U)
2. Select "MCP Logs" from the dropdown
3. Check for connection errors, authentication issues, or server crashes

The logs show server initialization, tool calls, and error messages.

### Can I temporarily disable an MCP server?

Yes! Toggle servers on/off without removing them:

1. Open Settings (Cmd+Shift+J)
2. Go to Features → Model Context Protocol
3. Click the toggle next to any server to enable/disable

Disabled servers won't load or appear in chat. This is useful for troubleshooting or reducing tool clutter.

### What happens if an MCP server crashes or times out?

If an MCP server fails:

- Cursor shows an error message in chat
- The tool call is marked as failed
- You can retry the operation or check logs for details
- Other MCP servers continue working normally

Cursor isolates server failures to prevent one server from affecting others.

### How do I update an MCP server?

For npm-based servers:

1. Remove the server from settings
2. Clear npm cache: `npm cache clean --force`
3. Re-add the server to get the latest version

For custom servers, update your local files and restart Cursor.

### Can I use MCP servers with sensitive data?

Yes, but follow security best practices:

- Use environment variables for secrets, never hardcode them
- Run sensitive servers locally with `stdio` transport
- Limit API key permissions to minimum required
- Review server code before connecting to sensitive systems
- Consider running servers in isolated environments


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/mcp/directory.md
# INDEX: 67/114
================================================================================

# MCP Directory

Browse featured MCP servers for Cursor. Use search and filters to find integrations quickly.

| Group | Name                       | Description                                                                                                                                                                                                                                                                                   | Transport       | OAuth | Install                                                                                                                                                                                                              | Docs                                                                                                                                                         |
| ----- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| -     | GitHub                     | Version control and collaborative development platform.                                                                                                                                                                                                                                       | stdio           | No    | `docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN ghcr.io/github/github-mcp-server`                                                                                                                                | -                                                                                                                                                            |
| -     | Slack                      | Team communication and collaboration platform.                                                                                                                                                                                                                                                | sse             | Yes   | [https://mcp.slack.com/mcp](https://mcp.slack.com/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Notion                     | All-in-one workspace for notes, docs, and project management.                                                                                                                                                                                                                                 | sse             | Yes   | [https://mcp.notion.com/mcp](https://mcp.notion.com/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Figma                      | Design and collaboration platform for teams.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.figma.com/mcp](https://mcp.figma.com/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Context7                   | Up-to-date code documentation.                                                                                                                                                                                                                                                                | sse             | No    | [https://mcp.context7.com/mcp](https://mcp.context7.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Linear                     | Issue tracking and project management for development teams.                                                                                                                                                                                                                                  | stdio, sse      | Yes   | [https://mcp.linear.app/mcp](https://mcp.linear.app/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Playwright                 | End-to-end browser testing.                                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @playwright/mcp@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | shadcn/ui                  | Use the shadcn/ui MCP server to browse, search, and install components from registries.                                                                                                                                                                                                       | stdio           | No    | `npx shadcn@latest mcp`                                                                                                                                                                                              | -                                                                                                                                                            |
| -     | Sentry                     | Error tracking and performance monitoring.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.sentry.dev/mcp](https://mcp.sentry.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Salesforce DX              | Interact with Salesforce orgs, manage metadata, data, and development workflows.                                                                                                                                                                                                              | stdio           | No    | `npx -y @salesforce/mcp --orgs DEFAULT_TARGET_ORG`                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Supabase                   | Create and manage Supabase projects.                                                                                                                                                                                                                                                          | sse             | Yes   | [https://mcp.supabase.com/mcp](https://mcp.supabase.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Vercel                     | Manage projects and deployments on Vercel.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.vercel.com](https://mcp.vercel.com)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | GitLab                     | DevSecOps platform for code, CI/CD, and security.                                                                                                                                                                                                                                             | http            | No    | [https://your-gitlab-instance.com/api/v4/mcp](https://your-gitlab-instance.com/api/v4/mcp)                                                                                                                           | [https://docs.gitlab.com/user/gitlab\_duo/model\_context\_protocol/mcp\_server/](https://docs.gitlab.com/user/gitlab_duo/model_context_protocol/mcp_server/) |
| -     | PostHog                    | Analytics, error tracking, and feature flags.                                                                                                                                                                                                                                                 | sse             | No    | `npx -y mcp-remote@latest https://mcp.posthog.com/sse --header Authorization:${POSTHOG_AUTH_HEADER}`                                                                                                                 | -                                                                                                                                                            |
| -     | Netlify                    | Build and deploy web projects.                                                                                                                                                                                                                                                                | stdio           | No    | `npx -y @netlify/mcp`                                                                                                                                                                                                | -                                                                                                                                                            |
| -     | Heroku                     | Manage Heroku apps and resources.                                                                                                                                                                                                                                                             | stdio           | No    | `npx -y @heroku/mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| -     | Postman                    | API collaboration and testing.                                                                                                                                                                                                                                                                | stdio           | No    | [https://mcp.postman.com/minimal](https://mcp.postman.com/minimal)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Prisma                     | Manage Prisma Postgres databases, including creating new instances and running schema migrations.                                                                                                                                                                                             | stdio, sse      | Yes   | [https://mcp.prisma.io/mcp](https://mcp.prisma.io/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| SAP   | CAP                        | SAP Cloud Application Programming Model development.                                                                                                                                                                                                                                          | stdio           | No    | `npx -y @cap-js/mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| SAP   | SAP Fiori                  | SAP Fiori UI elements and application development.                                                                                                                                                                                                                                            | stdio           | No    | `npx --yes @sap-ux/fiori-mcp-server@latest fiori-mcp`                                                                                                                                                                | -                                                                                                                                                            |
| SAP   | SAP Mobile Development Kit | SAP Mobile Development Kit tools and templates.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @sap/mdk-mcp-server`                                                                                                                                                                                         | -                                                                                                                                                            |
| SAP   | UI5 MCP Server             | OpenUI5 and SAPUI5 web application development.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @ui5/mcp-server@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | MongoDB                    | Manage MongoDB data and deployments.                                                                                                                                                                                                                                                          | stdio           | No    | `npx -y mongodb-mcp-server`                                                                                                                                                                                          | -                                                                                                                                                            |
| -     | dbt Labs                   | dbt CLI, Semantic Layer, and Discovery API.                                                                                                                                                                                                                                                   | stdio           | No    | `uvx dbt-mcp`                                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Atlassian                  | Project management and collaboration tools including Jira and Confluence.                                                                                                                                                                                                                     | sse             | Yes   | [https://mcp.atlassian.com/v1/mcp](https://mcp.atlassian.com/v1/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | DuckDB                     | In-process SQL OLAP database for local analytics.                                                                                                                                                                                                                                             | stdio           | No    | `uvx mcp-server-motherduck --db-path :memory:`                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Braintrust                 | Access to the documentation, experiments, and logs in Braintrust.                                                                                                                                                                                                                             | sse             | Yes   | [https://api.braintrust.dev/mcp](https://api.braintrust.dev/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Browserbase                | Headless browser sessions for agents.                                                                                                                                                                                                                                                         | stdio           | No    | `npx @browserbasehq/mcp`                                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Chrome DevTools            | Debug web pages directly in Chrome with DevTools debugging capabilities and performance insights.                                                                                                                                                                                             | stdio           | No    | `npx chrome-devtools-mcp@latest`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | ClickUp                    | Project management and collaboration for teams & agents.                                                                                                                                                                                                                                      | http            | Yes   | [https://mcp.clickup.com/mcp](https://mcp.clickup.com/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | Convex                     | Interact with your Convex deployment - query tables, run functions, manage environment variables, and analyze logs.                                                                                                                                                                           | stdio           | No    | `npx -y convex@latest mcp start`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Shopify                    | Shopify app development tools.                                                                                                                                                                                                                                                                | stdio           | No    | `npx -y @shopify/dev-mcp@latest`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | snyk                       | Vulnerability scanning of your codebase.                                                                                                                                                                                                                                                      | stdio           | No    | `npx -y snyk@latest mcp -t stdio`                                                                                                                                                                                    | -                                                                                                                                                            |
| -     | Hugging Face               | Access the Hugging Face Hub and Gradio MCP Servers.                                                                                                                                                                                                                                           | sse             | No    | [https://hf.co/mcp](https://hf.co/mcp)                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Wix                        | Build and manage Wix sites.                                                                                                                                                                                                                                                                   | sse             | No    | [https://mcp.wix.com/mcp](https://mcp.wix.com/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Semgrep                    | Scan code for security vulnerabilities.                                                                                                                                                                                                                                                       | stdio           | No    | `semgrep mcp`                                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | LaunchDarkly               | Feature flags as a service.                                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y --package @launchdarkly/mcp-server -- mcp start --api-key api-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`                                                                                                          | -                                                                                                                                                            |
| -     | Statsig                    | Feature flags and experimentation platform.                                                                                                                                                                                                                                                   | sse             | No    | [https://api.statsig.com/v1/mcp](https://api.statsig.com/v1/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Endor Labs                 | Security risk insights for code.                                                                                                                                                                                                                                                              | stdio           | No    | `endorctl ai-tools mcp-server`                                                                                                                                                                                       | -                                                                                                                                                            |
| -     | InstantDB                  | Query and manage InstantDB.                                                                                                                                                                                                                                                                   | sse             | No    | [https://mcp.instantdb.com/mcp](https://mcp.instantdb.com/mcp)                                                                                                                                                       | -                                                                                                                                                            |
| -     | Tinybird                   | Real-time analytics APIs.                                                                                                                                                                                                                                                                     | stdio           | No    | `npx -y mcp-remote https://cloud.tinybird.co/mcp?token=TB_TOKEN`                                                                                                                                                     | -                                                                                                                                                            |
| -     | Neon                       | Manage Neon Postgres.                                                                                                                                                                                                                                                                         | sse             | Yes   | [https://mcp.neon.tech/mcp](https://mcp.neon.tech/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Socket                     | Analyze and secure dependencies.                                                                                                                                                                                                                                                              | sse             | No    | [https://mcp.socket.dev/](https://mcp.socket.dev/)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Pipedream                  | Connect to APIs and workflows.                                                                                                                                                                                                                                                                | sse             | No    | [https://mcp.pipedream.net/\<uuid>/\<app>](https://mcp.pipedream.net/\<uuid>/\<app>)                                                                                                                                 | -                                                                                                                                                            |
| -     | Auth0                      | Manage Auth0 resources.                                                                                                                                                                                                                                                                       | stdio           | No    | `npx -y @auth0/auth0-mcp-server run`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Honeycomb                  | Query observability data and SLOs.                                                                                                                                                                                                                                                            | sse             | No    | [https://mcp.honeycomb.io/mcp](https://mcp.honeycomb.io/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | PagerDuty                  | Manage incidents and alerts.                                                                                                                                                                                                                                                                  | stdio           | No    | `uvx pagerduty-mcp --enable-write-tools`                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Graphite                   | Create and manage stacked PRs.                                                                                                                                                                                                                                                                | stdio           | No    | `gt mcp`                                                                                                                                                                                                             | -                                                                                                                                                            |
| -     | Railway                    | Deploy apps, databases, and services.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @railway/mcp-server`                                                                                                                                                                                         | -                                                                                                                                                            |
| -     | Replicate                  | Search, discover, compare, and run AI models with a cloud API.                                                                                                                                                                                                                                | sse             | Yes   | [https://mcp.replicate.com/sse](https://mcp.replicate.com/sse)                                                                                                                                                       | -                                                                                                                                                            |
| -     | AWS Documentation          | Access AWS documentation, search, and get recommendations.                                                                                                                                                                                                                                    | stdio           | No    | `uvx awslabs.aws-documentation-mcp-server@latest`                                                                                                                                                                    | -                                                                                                                                                            |
| -     | Select Star                | Data catalog, lineage, and context.                                                                                                                                                                                                                                                           | stdio           | No    | `npx -y mcp-remote@latest https://mcp.production.selectstar.com/mcp --header Authorization:${SELECT_STAR_TOKEN}`                                                                                                     | -                                                                                                                                                            |
| -     | SonarQube                  | Analyze code with SonarQube.                                                                                                                                                                                                                                                                  | stdio           | No    | `docker run -i --rm -e SONARQUBE_TOKEN -e SONARQUBE_URL mcp/sonarqube`                                                                                                                                               | -                                                                                                                                                            |
| -     | MS Learn Docs              | Search Microsoft docs.                                                                                                                                                                                                                                                                        | sse             | No    | [https://learn.microsoft.com/api/mcp](https://learn.microsoft.com/api/mcp)                                                                                                                                           | -                                                                                                                                                            |
| -     | Stripe                     | Payment processing APIs.                                                                                                                                                                                                                                                                      | stdio, sse      | No    | `npx -y @stripe/mcp --tools=all`                                                                                                                                                                                     | -                                                                                                                                                            |
| -     | PayPal                     | Payment APIs.                                                                                                                                                                                                                                                                                 | sse             | Yes   | [https://mcp.paypal.com/sse](https://mcp.paypal.com/sse)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Plaid                      | Access financial account data.                                                                                                                                                                                                                                                                | sse             | No    | [https://api.dashboard.plaid.com/mcp/sse](https://api.dashboard.plaid.com/mcp/sse)                                                                                                                                   | -                                                                                                                                                            |
| -     | firecrawl                  | The web crawling, scraping, and search API for AI                                                                                                                                                                                                                                             | sse             | No    | `npx -y firecrawl-mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Corridor                   | Proactively enforce security guardrails to reduce vulnerabilities.                                                                                                                                                                                                                            | https           | No    | [https://app.corridor.dev/api/mcp](https://app.corridor.dev/api/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Amplitude                  | Behavior analytics and experimentation platform for product data insights.                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.amplitude.com/mcp](https://mcp.amplitude.com/mcp)                                                                                                                                                       | -                                                                                                                                                            |
| -     | Astro docs server          | This server provides up-to-date access to the official Astro documentation.                                                                                                                                                                                                                   | sse             | No    | [https://mcp.docs.astro.build/mcp](https://mcp.docs.astro.build/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Mercado Pago               | Access Mercado Pago docs.                                                                                                                                                                                                                                                                     | stdio           | No    | [https://mcp.mercadopago.com/mcp](https://mcp.mercadopago.com/mcp)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Mercado Libre              | Access Mercado Libre docs.                                                                                                                                                                                                                                                                    | sse             | No    | [https://mcp.mercadolibre.com/mcp](https://mcp.mercadolibre.com/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Apify                      | Extract data from any website with thousands of scrapers, crawlers, and automations                                                                                                                                                                                                           | streamable-http | Yes   | [https://mcp.apify.com](https://mcp.apify.com)                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Render                     | Manage your Render services.                                                                                                                                                                                                                                                                  | streamable-http | No    | [https://mcp.render.com/mcp](https://mcp.render.com/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Azure DevOps               | Interact with Azure DevOps work items, pull requests, builds, and releases.                                                                                                                                                                                                                   | stdio           | No    | `npx -y @azure-devops/mcp {organization}`                                                                                                                                                                            | -                                                                                                                                                            |
| -     | Webflow                    | Webflow's MCP server enhances an agent's understanding of your Webflow projects. It's built on Webflow's APIs, exposing them as tools your AI agent can use to create elements, styles, and variables on the canvas, as well as manage collections, custom code, assets, and other site data. | sse             | Yes   | [https://mcp.webflow.com/sse](https://mcp.webflow.com/sse)                                                                                                                                                           | -                                                                                                                                                            |
| -     | terraform                  | Generate and automate Terraform workflows.                                                                                                                                                                                                                                                    | stdio           | No    | `docker run --rm -i -e TFE_ADDRESS -e TFE_TOKEN -e ENABLE_TF_OPERATIONS hashicorp/terraform-mcp-server:latest`                                                                                                       | -                                                                                                                                                            |
| -     | vault                      | Store and manage secrets.                                                                                                                                                                                                                                                                     | stdio           | No    | `docker run --rm -i -e VAULT_ADDR -e VAULT_TOKEN -e VAULT_NAMESPACE hashicorp/vault-mcp-server:latest`                                                                                                               | -                                                                                                                                                            |
| -     | Browser Use                | The Browser Use MCP server provides Cursor agents access to browser-use documentation. This gives AI assistants deep context about the browser-use library when helping you write code.                                                                                                       | sse             | No    | [https://docs.browser-use.com/mcp](https://docs.browser-use.com/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | Sanity                     | Create, query, and manage Sanity content, releases, datasets, and schemas.                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.sanity.io](https://mcp.sanity.io)                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Airwallex Developer MCP    | Tools to search Airwallex docs and interact with the Airwallex sandbox environment while integrating with Airwallex APIs.                                                                                                                                                                     | stdio           | No    | `npx -y @airwallex/developer-mcp@latest`                                                                                                                                                                             | [https://www.airwallex.com/docs/developer-tools/ai/developer-mcp](https://www.airwallex.com/docs/developer-tools/ai/developer-mcp)                           |
| -     | Dynatrace                  | Enterprise observability platform for real-time monitoring and AI-powered insights.                                                                                                                                                                                                           | sse             | Yes   | [https://\{environmentId}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp](https://\{environmentId}.apps.dynatrace.com/platform-reserved/mcp-gateway/v0.1/servers/dynatrace-mcp/mcp) | -                                                                                                                                                            |
| -     | Arcade                     | Create and manage MCP gateways connecting 100+ integrations.                                                                                                                                                                                                                                  | sse             | Yes   | [https://ctl.arcade.dev/mcp](https://ctl.arcade.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Embrace                    | Mobile app performance monitoring and crash analytics.                                                                                                                                                                                                                                        | sse             | Yes   | [https://mcp.embrace.io/mcp](https://mcp.embrace.io/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | CodeSherlock               | AI code analysis for security, quality, and compliance checks.                                                                                                                                                                                                                                | stdio           | No    | `npx -y @codesherlock/codesherlock-mcp-server`                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Kyomi                      | Query data warehouses with natural language and institutional knowledge.                                                                                                                                                                                                                      | sse             | Yes   | [https://app.kyomi.ai/mcp](https://app.kyomi.ai/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Pendo                      | Product analytics and user behavior insights.                                                                                                                                                                                                                                                 | sse             | Yes   | [https://app.pendo.io/mcp/v0/shttp](https://app.pendo.io/mcp/v0/shttp)                                                                                                                                               | -                                                                                                                                                            |
| -     | SearchAPI                  | Real-time search engine API for AI applications.                                                                                                                                                                                                                                              | sse             | No    | [https://www.searchapi.io/mcp?token=\<your\_integration\_token>](https://www.searchapi.io/mcp?token=\<your_integration_token>)                                                                                       | -                                                                                                                                                            |
| -     | Defang                     | Deploy apps to AWS, GCP, and DigitalOcean from Docker Compose.                                                                                                                                                                                                                                | stdio           | No    | `npx -y defang mcp serve --client=cursor`                                                                                                                                                                            | -                                                                                                                                                            |
| -     | WordPress.com              | Manage WordPress.com sites, posts, and content.                                                                                                                                                                                                                                               | stdio           | Yes   | `npx -y mcp-remote https://public-api.wordpress.com/wpcom/v2/mcp/v1`                                                                                                                                                 | -                                                                                                                                                            |
| -     | Luciq                      | Query crash reports and observability data from your IDE.                                                                                                                                                                                                                                     | sse             | No    | [https://api.instabug.com/api/mcp](https://api.instabug.com/api/mcp)                                                                                                                                                 | -                                                                                                                                                            |
| -     | alphaXiv                   | Search ML research papers and analyze PDFs.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://api.alphaxiv.org/mcp/v1](https://api.alphaxiv.org/mcp/v1)                                                                                                                                                   | -                                                                                                                                                            |
| -     | Codve                      | Logic-based code verification with confidence scores.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @codve/mcp-server`                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Arize AX                   | LLM tracing and instrumentation guidance.                                                                                                                                                                                                                                                     | stdio           | No    | `uvx arize-tracing-assistant@latest`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | MotherDuck                 | Query and explore MotherDuck cloud databases.                                                                                                                                                                                                                                                 | sse             | Yes   | [https://api.motherduck.com/mcp](https://api.motherduck.com/mcp)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Glean                      | Enterprise knowledge search and context.                                                                                                                                                                                                                                                      | sse             | No    | [https://\{instance}-be.glean.com/mcp/\{server-name}](https://\{instance}-be.glean.com/mcp/\{server-name})                                                                                                           | -                                                                                                                                                            |
| -     | incident.io                | Incident management and alerting.                                                                                                                                                                                                                                                             | stdio           | No    | `npx -y @incident-io/mcp`                                                                                                                                                                                            | -                                                                                                                                                            |
| -     | Firebase                   | Manage Firebase projects, Auth, Firestore, and more.                                                                                                                                                                                                                                          | stdio           | No    | `npx -y firebase-tools@latest mcp`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Aikido Security            | Security scanning in your AI coding workflow.                                                                                                                                                                                                                                                 | stdio           | No    | `npx -y @aikidosec/mcp`                                                                                                                                                                                              | -                                                                                                                                                            |
| -     | Mixpanel                   | Product analytics through natural language queries.                                                                                                                                                                                                                                           | stdio           | No    | `npx -y mcp-remote https://mcp.mixpanel.com/mcp --allow-http`                                                                                                                                                        | -                                                                                                                                                            |
| -     | Windsor.ai                 | Query analytics data across marketing platforms.                                                                                                                                                                                                                                              | sse             | No    | [https://mcp.windsor.ai](https://mcp.windsor.ai)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Circleback                 | Search meeting notes and transcripts for dev context.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y mcp-remote https://app.circleback.ai/api/mcp`                                                                                                                                                                | -                                                                                                                                                            |
| -     | Tauri                      | Build and debug Tauri desktop/mobile apps with screenshots and DOM state.                                                                                                                                                                                                                     | stdio           | No    | `npx -y @hypothesi/tauri-mcp-server`                                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Vantage                    | Cloud cost management and FinOps insights.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://mcp.vantage.sh/mcp](https://mcp.vantage.sh/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Sidemail                   | Send transactional emails and manage email workflows.                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @sidemail/mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Databend                   | AI-native cloud data warehouse analytics.                                                                                                                                                                                                                                                     | stdio           | No    | `uv tool run mcp-databend`                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Kubit                      | Analytics platform with natural language queries.                                                                                                                                                                                                                                             | sse             | Yes   | [https://mcp.kubit.ai/mcp](https://mcp.kubit.ai/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | CodeScene                  | Code health insights and technical debt analysis.                                                                                                                                                                                                                                             | stdio           | No    | `docker run -i --rm -e CS_ACCESS_TOKEN codescene/codescene-mcp`                                                                                                                                                      | -                                                                                                                                                            |
| -     | Vale                       | Style and grammar linting for documentation.                                                                                                                                                                                                                                                  | stdio           | No    | `vale-cli`                                                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Fluid Attacks              | Security vulnerability scanning and analysis.                                                                                                                                                                                                                                                 | sse             | No    | [https://app.fluidattacks.com/mcp/messages/](https://app.fluidattacks.com/mcp/messages/)                                                                                                                             | -                                                                                                                                                            |
| -     | Clarity                    | Microsoft user behavior analytics.                                                                                                                                                                                                                                                            | stdio           | No    | `npx -y @microsoft/clarity-mcp-server@latest`                                                                                                                                                                        | -                                                                                                                                                            |
| -     | You.com                    | AI-powered web search and research.                                                                                                                                                                                                                                                           | sse             | No    | [https://api.you.com/mcp](https://api.you.com/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | TestDino                   | Connect AI tools to testing platform.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y testdino-mcp`                                                                                                                                                                                                | -                                                                                                                                                            |
| -     | Kernel                     | Fast infrastructure for agents to access the internet.                                                                                                                                                                                                                                        | sse             | Yes   | [https://mcp.onkernel.com/mcp](https://mcp.onkernel.com/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Angular                    | Angular framework documentation and examples.                                                                                                                                                                                                                                                 | stdio           | No    | `npx -y @angular/cli mcp`                                                                                                                                                                                            | -                                                                                                                                                            |
| -     | AWS                        | Access AWS services through natural language.                                                                                                                                                                                                                                                 | stdio           | No    | `uvx mcp-proxy-for-aws@latest https://aws-mcp.us-east-1.api.aws/mcp --metadata AWS_REGION=us-west-2`                                                                                                                 | -                                                                                                                                                            |
| -     | Uno Platform               | Cross-platform .NET application development.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.platform.uno/v1](https://mcp.platform.uno/v1)                                                                                                                                                           | -                                                                                                                                                            |
| -     | DBHub                      | Universal database connector for MySQL, PostgreSQL, SQL Server.                                                                                                                                                                                                                               | stdio           | No    | `npx @bytebase/dbhub --transport stdio --dsn postgres://user:password@localhost:5432/dbname`                                                                                                                         | -                                                                                                                                                            |
| -     | CoreStory                  | Access PRDs, technical specs, and project context.                                                                                                                                                                                                                                            | http            | No    | [https://c2s.corestory.ai/mcp](https://c2s.corestory.ai/mcp)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Ref                        | Token-efficient documentation search.                                                                                                                                                                                                                                                         | sse             | Yes   | [https://api.ref.tools/mcp](https://api.ref.tools/mcp)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Perplexity                 | AI-powered web search and research.                                                                                                                                                                                                                                                           | stdio           | No    | `npx -y @perplexity-ai/mcp-server`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Checkmarx                  | Application security testing and vulnerability scanning.                                                                                                                                                                                                                                      | sse             | Yes   | [https://\{tenant}/api/security-mcp/mcp](https://\{tenant}/api/security-mcp/mcp)                                                                                                                                     | -                                                                                                                                                            |
| -     | SafeDep Vet                | Vet open source packages for security issues.                                                                                                                                                                                                                                                 | stdio           | No    | `docker run --rm -i ghcr.io/safedep/vet:latest -s server mcp`                                                                                                                                                        | -                                                                                                                                                            |
| -     | Elasticsearch              | Query logs and data from the ELK stack.                                                                                                                                                                                                                                                       | stdio           | No    | `npx mcp-remote ${KIBANA_URL}/api/agent_builder/mcp --header Authorization:${AUTH_HEADER}`                                                                                                                           | -                                                                                                                                                            |
| -     | Unleash                    | Open source feature flags management.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @unleash/mcp@latest`                                                                                                                                                                                         | -                                                                                                                                                            |
| -     | Tigris                     | S3-compatible object storage management.                                                                                                                                                                                                                                                      | sse             | Yes   | [https://mcp.storage.dev/mcp](https://mcp.storage.dev/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | DevRev                     | Work item management for development teams.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://api.devrev.ai/mcp/v1](https://api.devrev.ai/mcp/v1)                                                                                                                                                         | -                                                                                                                                                            |
| -     | Mux                        | Video platform for uploads, streaming, and analytics.                                                                                                                                                                                                                                         | sse             | Yes   | [https://mcp.mux.com](https://mcp.mux.com)                                                                                                                                                                           | -                                                                                                                                                            |
| -     | Hex                        | Data analytics platform for insights and exploration.                                                                                                                                                                                                                                         | sse             | Yes   | [https://app.hex.tech/mcp](https://app.hex.tech/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Stack Overflow             | Access trusted technical Q\&A from Stack Overflow.                                                                                                                                                                                                                                            | stdio           | No    | `npx mcp-remote mcp.stackoverflow.com`                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Fellow                     | AI meeting notes, transcripts, and action items.                                                                                                                                                                                                                                              | sse             | Yes   | [https://fellow.app/mcp](https://fellow.app/mcp)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | LiveKit                    | Real-time communication documentation and examples.                                                                                                                                                                                                                                           | sse             | No    | [https://docs.livekit.io/mcp](https://docs.livekit.io/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | GrowthBook                 | Feature flags and A/B testing platform.                                                                                                                                                                                                                                                       | stdio           | No    | `npx -y @growthbook/mcp@latest`                                                                                                                                                                                      | -                                                                                                                                                            |
| -     | Octopus Deploy             | Manage deployments, releases, and runbooks.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @octopusdeploy/mcp-server`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Builder.io                 | Headless CMS content management.                                                                                                                                                                                                                                                              | sse             | No    | [https://cdn.builder.io/api/v1/mcp/builder-content](https://cdn.builder.io/api/v1/mcp/builder-content)                                                                                                               | -                                                                                                                                                            |
| -     | DevExpress                 | DevExpress component library documentation.                                                                                                                                                                                                                                                   | sse             | No    | [https://api.devexpress.com/mcp/docs](https://api.devexpress.com/mcp/docs)                                                                                                                                           | -                                                                                                                                                            |
| -     | Cloudinary                 | Media asset management and transformation.                                                                                                                                                                                                                                                    | sse             | Yes   | [https://asset-management.mcp.cloudinary.com/sse](https://asset-management.mcp.cloudinary.com/sse)                                                                                                                   | -                                                                                                                                                            |
| -     | Cloudflare                 | Cloudflare documentation and reference.                                                                                                                                                                                                                                                       | sse             | No    | [https://docs.mcp.cloudflare.com/mcp](https://docs.mcp.cloudflare.com/mcp)                                                                                                                                           | -                                                                                                                                                            |
| -     | Shuttle                    | Deploy Rust applications to the cloud.                                                                                                                                                                                                                                                        | stdio           | No    | `shuttle mcp start`                                                                                                                                                                                                  | -                                                                                                                                                            |
| -     | ConfigCat                  | Feature flag management for teams.                                                                                                                                                                                                                                                            | stdio           | No    | `npx -y @configcat/mcp-server`                                                                                                                                                                                       | -                                                                                                                                                            |
| -     | Coralogix                  | Observability platform for logs, metrics, and traces.                                                                                                                                                                                                                                         | stdio           | No    | `npx mcp-remote ${CORALOGIX_MCP_ENDPOINT} --header Authorization:${CORALOGIX_API_KEY}`                                                                                                                               | -                                                                                                                                                            |
| -     | Svelte                     | Svelte framework documentation and guidance.                                                                                                                                                                                                                                                  | sse             | No    | [https://mcp.svelte.dev/mcp](https://mcp.svelte.dev/mcp)                                                                                                                                                             | -                                                                                                                                                            |
| -     | Scout APM                  | Application performance monitoring and insights.                                                                                                                                                                                                                                              | stdio           | No    | `docker run --rm -i --env SCOUT_API_KEY scoutapp/scout-mcp-local`                                                                                                                                                    | -                                                                                                                                                            |
| -     | Axiom                      | Log analytics, monitoring, and APL queries.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://mcp.axiom.co/mcp](https://mcp.axiom.co/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Customer.io                | Manage segments, users, and marketing automation.                                                                                                                                                                                                                                             | sse             | Yes   | [https://mcp.customer.io/mcp](https://mcp.customer.io/mcp)                                                                                                                                                           | -                                                                                                                                                            |
| -     | Bitly                      | URL shortening and link management.                                                                                                                                                                                                                                                           | stdio           | No    | `npx mcp-remote https://api-ssl.bitly.com/v4/mcp --header Authorization: Bearer ${AUTH_TOKEN}`                                                                                                                       | -                                                                                                                                                            |
| -     | Devopness                  | DevOps automation for cloud infrastructure.                                                                                                                                                                                                                                                   | sse             | Yes   | [https://mcp.devopness.com/mcp/](https://mcp.devopness.com/mcp/)                                                                                                                                                     | -                                                                                                                                                            |
| -     | Jam                        | Screen recorder with auto context for debugging.                                                                                                                                                                                                                                              | sse             | Yes   | [https://mcp.jam.dev/mcp](https://mcp.jam.dev/mcp)                                                                                                                                                                   | -                                                                                                                                                            |
| -     | Webvizio                   | Bug feedback with screenshots and browser logs.                                                                                                                                                                                                                                               | stdio           | No    | `npx -y @webvizio/mcp-server`                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Supadata                   | Video and web scraping for AI applications.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y @supadata/mcp`                                                                                                                                                                                               | -                                                                                                                                                            |
| -     | Bitrise                    | Mobile CI/CD and build management.                                                                                                                                                                                                                                                            | sse             | No    | [https://mcp.bitrise.io](https://mcp.bitrise.io)                                                                                                                                                                     | -                                                                                                                                                            |
| -     | Harness                    | CI/CD and software delivery platform.                                                                                                                                                                                                                                                         | stdio           | No    | `npx -y @harness/mcp-server stdio`                                                                                                                                                                                   | -                                                                                                                                                            |
| -     | DryRun Security            | Security analysis insights and trends.                                                                                                                                                                                                                                                        | stdio           | No    | `npx -y mcp-remote https://insights-mcp.dryrun.security/insights/mcp --transport http-only`                                                                                                                          | -                                                                                                                                                            |
| -     | OX Security                | Security platform for AI agent integration.                                                                                                                                                                                                                                                   | stdio           | No    | `npx -y mcp-remote@0.1.18 https://api.cloud.ox.security/api/mcp --header Authorization:${AUTH_TOKEN}`                                                                                                                | -                                                                                                                                                            |
| -     | Zapier                     | Automate workflows with 30,000+ actions across 8,000+ apps. Build once, orchestrate everywhere.                                                                                                                                                                                               | streamableHttp  | Yes   | [https://mcp.zapier.com/api/mcp/s/•••••••/mcp](https://mcp.zapier.com/api/mcp/s/•••••••/mcp)                                                                                                                         | -                                                                                                                                                            |
| -     | Okahu                      | Access to traces and debug your AI agent apps                                                                                                                                                                                                                                                 | https           | No    | [https://mcp.okahu.co/mcp](https://mcp.okahu.co/mcp)                                                                                                                                                                 | -                                                                                                                                                            |
| -     | Scalekit                   | Auth stack for AI applications. Manage environments and connections.                                                                                                                                                                                                                          | http            | Yes   | [https://mcp.scalekit.com/](https://mcp.scalekit.com/)                                                                                                                                                               | -                                                                                                                                                            |
| -     | Chakra UI                  | Access Chakra UI component library, design tokens, and migration guidance.                                                                                                                                                                                                                    | stdio           | No    | `npx -y @chakra-ui/react-mcp`                                                                                                                                                                                        | -                                                                                                                                                            |
| -     | Alpha Vantage              | Financial data API for stocks, forex, crypto, and economic indicators.                                                                                                                                                                                                                        | http            | No    | [https://mcp.alphavantage.co/mcp](https://mcp.alphavantage.co/mcp)                                                                                                                                                   | -                                                                                                                                                            |

Don't see your MCP server? [Open an issue](https://github.com/cursor/mcp-servers/issues/new?template=server-request.yml) to request it.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/mcp/install-links.md
# INDEX: 68/114
================================================================================

# MCP Install Links

MCP servers can be installed with Cursor deeplinks. It uses the same format as [`mcp.json`](https://cursor.com/docs/context/mcp.md) with a name and transport configuration.

Install links:

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=$NAME&config=$BASE64_ENCODED_CONFIG
```

| Component                   | Description                                           |
| :-------------------------- | :---------------------------------------------------- |
| `cursor://`                 | Protocol scheme                                       |
| `anysphere.cursor-deeplink` | Deeplink handler                                      |
| `/mcp/install`              | Path                                                  |
| `name`                      | Query parameter for server name                       |
| `config`                    | Query parameter for base64 encoded JSON configuration |

## Generate install link

1. Get name and JSON configuration of server
2. `JSON.stringify` the configuration then base64 encode it
3. Replace `$NAME` and `$BASE64_ENCODED_CONFIG` with the name and encoded config

Helper for generating links:

## Example

Try this JSON in the MCP install link generator:

```json title="Single MCP server config"
{
  "postgres": {
    "command": "npx",
    "args": [
      "-y",
      "@modelcontextprotocol/server-postgres",
      "postgresql://localhost/mydb"
    ]
  }
}
```

Result:

| Format       | Example                                                                                                                                                                                                                                     |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Text link    | [cursor://anysphere.curs...](cursor://anysphere.cursor-deeplink/mcp/install?name=postgres\&config=eyJjb21tYW5kIjoibnB4IiwiYXJncyI6WyIteSIsIkBtb2RlbGNvbnRleHRwcm90b2NvbC9zZXJ2ZXItcG9zdGdyZXMiLCJwb3N0Z3Jlc3FsOi8vbG9jYWxob3N0L215ZGIiXX0=) |
| Dark button  | [](cursor://anysphere.cursor-deeplink/mcp/install?name=postgres\&config=eyJjb21tYW5kIjoibnB4IiwiYXJncyI6WyIteSIsIkBtb2RlbGNvbnRleHRwcm90b2NvbC9zZXJ2ZXItcG9zdGdyZXMiLCJwb3N0Z3Jlc3FsOi8vbG9jYWxob3N0L215ZGIiXX0=)                           |
| Light button | [](cursor://anysphere.cursor-deeplink/mcp/install?name=postgres\&config=eyJjb21tYW5kIjoibnB4IiwiYXJncyI6WyIteSIsIkBtb2RlbGNvbnRleHRwcm90b2NvbC9zZXJ2ZXItcG9zdGdyZXMiLCJwb3N0Z3Jlc3FsOi8vbG9jYWxob3N0L215ZGIiXX0=)                           |

## Install server

1. Click the link or paste into browser
2. Cursor prompts to install the server
3. Use the server in Cursor


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/mentions.md
# INDEX: 69/114
================================================================================

# @ Mentions

Navigate suggestions using arrow keys. Press `Enter` to select. If the suggestion is a category like `Files`, the suggestions filter to show the most relevant items within that category.

## @Files & Folders

### Referencing Files

Reference entire files in by selecting `@Files & Folders` followed by the filename to search. You can also drag files from the sidebar directly into Agent to add as context.

![@Files & Folders symbol](/docs-static/images/context/mentions/@-files-folders.png)

### Referencing Folders

When referencing folders using `@Folders`, Cursor provides the folder path and overview of its contents to help the AI understand what's available.

After selecting a folder, type `/` to navigate deeper and see all subfolders.

![@Folders symbol](/docs-static/images/context/mentions/@-folders.png)

### Context management

Large files and folders are automatically condensed to fit within context limits. See [file & folder condensation](https://cursor.com/docs/agent/chat/summarization.md#file--folder-condensation) for details.

## @Code

Reference specific code sections using the `@Code` symbol. This provides more granular control than `@Files & Folders`, letting you select precise code snippets instead of entire files.

![@Code symbol](/docs-static/images/context/mentions/@-code.png)

## @Docs

![Docs feature](/docs-static/images/context/mentions/@-docs.png)

The `@Docs` feature lets you use documentation to help write code. Cursor includes popular documentation and you can add your own.

### Using existing documentation

Type `@Docs` in chat to see available documentation. Browse and select from popular frameworks and libraries.

### Adding your own documentation

To add documentation not already available:

1. Type `@Docs` and select **Add new doc**
2. Paste the URL of the documentation site

![Add new doc](/docs-static/images/context/mentions/@-docs-add.png)

Once added, Cursor reads and understands the documentation, including all subpages. Use it like any other documentation.

Turn on **Share with team** to make documentation available to everyone on your team.

### Managing your documentation

Go to **Cursor Settings** > **Indexing & Docs** to see all your added documentation. From here:

- Edit documentation URLs
- Remove documentation you no longer need
- Add new documentation

![Manage your documentation](/docs-static/images/context/mentions/@-docs-mgmt.png)

## @Past Chats

Reference previous conversations using the `@Past Chats` symbol. This lets you provide context from earlier work to help the AI understand your project history and continue where you left off.

![@Past Chats dropdown](/docs-static/images/context/mentions/@-past-chats.png)

Type `@` in the chat input and select a past chat from the dropdown. Recent conversations appear at the top for quick access. The selected chat is added as context, giving the agent access to the full conversation history including messages, code changes, and tool results.

Use past chats to build on previous work, debug issues that span multiple sessions, or remind the agent of decisions made earlier.

## Built-in commands

- Summarize: Compress the context window and provide a summary of the conversation.

You can also define [custom commands](https://cursor.com/docs/agent/chat/commands.md) to use in the chat.

## Changelog

Cursor 2.0 includes improvements and some deprecations for context and @ mentions.

1. We've visually removed the top tray of the prompt input showing included context. However, the agent still sees the same context as before. Files and directories are now shown inline as pills. We've also improved copy/pasting prompts with tagged context.
2. We've removed explicit items in the context menu, including `@Definitions`, `@Web`, `@Link`, `@Recent Changes`, `@Linter Errors`, and others. Agent can now self-gather context without needing to manually attach it in the prompt input. For example, rather than using `@Git`, you can now ask the agent directly to review changes on your branch, or specific commits.
3. Notepads have been [deprecated](https://forum.cursor.com/t/deprecating-notepads-in-cursor/138305/5).
4. Applied rules are now shown by hovering the context gauge in the prompt input.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/rules.md
# INDEX: 70/114
================================================================================

# Rules

Rules provide system-level instructions to Agent. They bundle prompts, scripts, and more together, making it easy to manage and share workflows across your team.

Cursor supports four types of rules:

### Project Rules

Stored in `.cursor/rules`, version-controlled and scoped to your codebase.

### User Rules

Global to your Cursor environment. Used by Agent (Chat).

### Team Rules

Team-wide rules managed from the dashboard. Available on Team and [Enterprise](https://cursor.com/docs/enterprise.md) plans.

### AGENTS.md

Agent instructions in markdown format. Simple alternative to
`.cursor/rules`.

## How rules work

Large language models don't retain memory between completions. Rules provide persistent, reusable context at the prompt level.

When applied, rule contents are included at the start of the model context. This gives the AI consistent guidance for generating code, interpreting edits, or helping with workflows.

![Rule applied in context with chat](/docs-static/images/context/rules/rules-applied.png)

## Project rules

Project rules live in `.cursor/rules` as markdown files and are version-controlled. They are scoped using path patterns, invoked manually, or included based on relevance.

Use project rules to:

- Encode domain-specific knowledge about your codebase
- Automate project-specific workflows or templates
- Standardize style or architecture decisions

### Rule file structure

Each rule is a markdown file that you can name anything you want. Cursor supports `.md` and `.mdc` extensions. Use `.mdc` files with frontmatter to specify `description` and `globs` for more control over when rules are applied.

```bash
.cursor/rules/
  react-patterns.mdc       # Rule with frontmatter (description, globs)
  api-guidelines.md        # Simple markdown rule
  frontend/                # Organize rules in folders
    components.md
```

### Rule anatomy

Each rule is a markdown file with frontmatter metadata and content. Control how rules are applied from the type dropdown which changes properties `description`, `globs`, `alwaysApply`.

| Rule Type                 | Description                                           |
| :------------------------ | :---------------------------------------------------- |
| `Always Apply`            | Apply to every chat session                           |
| `Apply Intelligently`     | When Agent decides it's relevant based on description |
| `Apply to Specific Files` | When file matches a specified pattern                 |
| `Apply Manually`          | When @-mentioned in chat (e.g., `@my-rule`)           |

```md
---
globs:
alwaysApply: false
---

- Use our internal RPC pattern when defining services
- Always use snake_case for service names.

@service-template.ts
```

### Creating a rule

Create rules using the `New Cursor Rule` command or going to `Cursor Settings > Rules, Commands`. This creates a new rule file in `.cursor/rules`. From settings you can see all rules and their status.

![Comparison of concise vs long rules](/docs-static/images/context/rules/rule-settings.png)

## Best practices

Good rules are focused, actionable, and scoped.

- Keep rules under 500 lines
- Split large rules into multiple, composable rules
- Provide concrete examples or referenced files
- Avoid vague guidance. Write rules like clear internal docs
- Reuse rules when repeating prompts in chat
- Reference files instead of copying their contents—this keeps rules short and prevents them from becoming stale as code changes

### What to avoid in rules

- **Copying entire style guides**: Use a linter instead. Agent already knows common style conventions.
- **Documenting every possible command**: Agent knows common tools like npm, git, and pytest.
- **Adding instructions for edge cases that rarely apply**: Keep rules focused on patterns you use frequently.
- **Duplicating what's already in your codebase**: Point to canonical examples instead of copying code.

Start simple. Add rules only when you notice Agent making the same mistake repeatedly. Don't over-optimize before you understand your patterns.

Check your rules into git so your whole team benefits. When you see Agent make a mistake, update the rule. You can even tag `@cursor` on a GitHub issue or PR to have Agent update the rule for you.

## Rule file format

Each rule is a markdown file with frontmatter metadata and content. The frontmatter metadata is used to control how the rule is applied. The content is the rule itself.

```markdown
---
description: "This rule provides standards for frontend components and API validation"
alwaysApply: false
---

...rest of the rule content
```

If alwaysApply is true, the rule will be applied to every chat session. Otherwise, the description of the rule will be presented to the Cursor Agent to decide if it should be applied.

## Examples

### Standards for frontend components and API validation

This rule provides standards for frontend components:

When working in components directory:

- Always use Tailwind for styling
- Use Framer Motion for animations
- Follow component naming conventions

This rule enforces validation for API endpoints:

In API directory:

- Use zod for all validation
- Define return types with zod schemas
- Export types generated from schemas

### Templates for Express services and React components

This rule provides a template for Express services:

Use this template when creating Express service:

- Follow RESTful principles
- Include error handling middleware
- Set up proper logging

@express-service-template.ts

This rule defines React component structure:

React components should follow this layout:

- Props interface at top
- Component as named export
- Styles at bottom

@component-template.tsx

### Automating development workflows and documentation generation

This rule automates app analysis:

When asked to analyze the app:

1. Run dev server with `npm run dev`
2. Fetch logs from console
3. Suggest performance improvements

This rule helps generate documentation:

Help draft documentation by:

- Extracting code comments
- Analyzing README.md
- Generating markdown documentation

### Adding a new setting in Cursor

First create a property to toggle in `@reactiveStorageTypes.ts`.

Add default value in `INIT_APPLICATION_USER_PERSISTENT_STORAGE` in `@reactiveStorageService.tsx`.

For beta features, add toggle in `@settingsBetaTab.tsx`, otherwise add in `@settingsGeneralTab.tsx`. Toggles can be added as `<SettingsSubSection>` for general checkboxes. Look at the rest of the file for examples.

```jsx
<SettingsSubSection
  label="Your feature name"
  description="Your feature description"
  value={
    vsContext.reactiveStorageService.applicationUserPersistentStorage
      .myNewProperty ?? false
  }
  onChange={(newVal) => {
    vsContext.reactiveStorageService.setApplicationUserPersistentStorage(
      "myNewProperty",
      newVal,
    );
  }}
/>
```

To use in the app, import reactiveStorageService and use the property:

```js
const flagIsEnabled =
  vsContext.reactiveStorageService.applicationUserPersistentStorage
    .myNewProperty;
```

Examples are available from providers and frameworks. Community-contributed rules are found across crowdsourced collections and repositories online.

## Team Rules

Team and [Enterprise](https://cursor.com/docs/enterprise.md) plans can create and enforce rules across their entire organization from the [Cursor dashboard](https://cursor.com/dashboard?tab=team-content). Admins can configure whether or not each rule is required for team members.

Team Rules work alongside other rule types and take precedence to ensure organizational standards are maintained across all projects. They provide a powerful way to ensure consistent coding standards, practices, and workflows across your entire team without requiring individual setup or configuration.

### Managing Team Rules

Team administrators can create and manage rules directly from the Cursor dashboard:

![Empty team rules dashboard where team administrators can add new rules](/docs-static/images/context/rules/team-rules-empty.png)

Once team rules are created, they automatically apply to all team members and are visible in the dashboard:

![Team rules dashboard showing a single team rule that will be enforced for all team members](/docs-static/images/context/rules/team-rules-1.png)

### Activation and enforcement

- **Enable this rule immediately**: When checked, the rule is active as soon as you create it. When unchecked, the rule is saved as a draft and does not apply until you enable it later.
- **Enforce this rule**: When enabled, the rule is required for all team members and cannot be disabled in their Cursor settings. When not enforced, team members can toggle the rule off in `Cursor Settings → Rules` under the Team Rules section.

By default, non‑enforced Team Rules can be disabled by users. Use Enforce this rule to prevent that.

### Format and how Team Rules are applied

- **Plain text**: Team Rules are free‑form text. They do not use the folder structure of Project Rules and do not support metadata such as `globs`, `alwaysApply`, or rule types.
- **Where they apply**: When a Team Rule is enabled (and not disabled by the user, unless enforced), it is included in the model context for Agent (Chat) across all repositories and projects for that team.
- **Precedence**: Rules are applied in this order: **Team Rules → Project Rules → User Rules**. All applicable rules are merged; earlier sources take precedence when guidance conflicts.

Some teams use enforced rules as part of internal compliance workflows. While this is supported, AI guidance should not be your only security control.

## Importing Rules

You can import rules from external sources to reuse existing configurations or bring in rules from other tools.

### Remote rules (via GitHub)

Import rules directly from any GitHub repository you have access to—public or private.

1. Open **Cursor Settings → Rules, Commands**
2. Click `+ Add Rule` next to `Project Rules`, then select Remote Rule (Github)
3. Paste the GitHub repository URL containing the rule
4. Cursor will pull and sync the rule into your project

Imported rules stay synced with their source repository, so updates to the remote rule are automatically reflected in your project.

### Agent Skills

Cursor can load rules from [Agent Skills](https://cursor.com/docs/context/skills.md), an open standard for extending AI agents with specialized capabilities. These imported skills are always applied as agent-decided rules, meaning Cursor determines when they are relevant based on context.

To enable or disable Agent Skills:

1. Open **Cursor Settings → Rules**
2. Find the **Import Settings** section
3. Toggle **Agent Skills** on or off

Agent Skills are treated as agent-decided rules and cannot be configured as always-apply or manual rules.

## AGENTS.md

`AGENTS.md` is a simple markdown file for defining agent instructions. Place it in your project root as an alternative to `.cursor/rules` for straightforward use cases.

Unlike Project Rules, `AGENTS.md` is a plain markdown file without metadata or complex configurations. It's perfect for projects that need simple, readable instructions without the overhead of structured rules.

Cursor supports AGENTS.md in the project root and subdirectories.

```markdown
# Project Instructions

## Code Style

- Use TypeScript for all new files
- Prefer functional components in React
- Use snake_case for database columns

## Architecture

- Follow the repository pattern
- Keep business logic in service layers
```

### Improvements

### Nested AGENTS.md support

Nested `AGENTS.md` support in subdirectories is now available. You can place `AGENTS.md` files in any subdirectory of your project, and they will be automatically applied when working with files in that directory or its children.

This allows for more granular control of agent instructions based on the area of your codebase you're working in:

```bash
project/
  AGENTS.md              # Global instructions
  frontend/
    AGENTS.md            # Frontend-specific instructions
    components/
      AGENTS.md          # Component-specific instructions
  backend/
    AGENTS.md            # Backend-specific instructions
```

Instructions from nested `AGENTS.md` files are combined with parent directories, with more specific instructions taking precedence.

## User Rules

User Rules are global preferences defined in **Cursor Settings → Rules** that apply across all projects. They are used by Agent (Chat) and are perfect for setting preferred communication style or coding conventions:

```md
Please reply in a concise style. Avoid unnecessary repetition or filler language.
```

## Legacy Cursor Rules

### `.cursorrules`

The `.cursorrules` (legacy) file in your project root is still supported but **will be deprecated**. We recommend migrating to Project Rules or to `AGENTS.md`.

## FAQ

### Why isn't my rule being applied?

Check the rule type. For `Apply Intelligently`, ensure a description is defined. For `Apply to Specific Files`, ensure the file pattern matches referenced files.

### Can rules reference other rules or files?

Yes. Use `@filename.ts` to include files in your rule's context. You can also @mention rules in chat to apply them manually.

### Can I create a rule from chat?

Yes, you can ask the agent to create a new rule for you.

### Do rules impact Cursor Tab or other AI features?

No. Rules do not impact Cursor Tab or other AI features.

### Do User Rules apply to Inline Edit (Cmd/Ctrl+K)?

No. User Rules are not applied to Inline Edit (Cmd/Ctrl+K). They are only
used by Agent (Chat).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/semantic-search.md
# INDEX: 71/114
================================================================================

# Semantic Search

Semantic search finds code by understanding its meaning, not just matching text. Ask natural language questions like "where is authentication handled?" and get relevant results across your entire codebase.

## How it works

Cursor transforms your code into searchable vectors through a 7-step process:

1. Your workspace files are securely synchronized with Cursor's servers to keep the index current and up-to-date.

2. Files are broken down into meaningful chunks that capture the essence of your code—functions, classes, and logical code blocks rather than arbitrary text segments.

3. Each chunk is converted into a vector representation using AI models. This creates a mathematical fingerprint that captures the semantic meaning of your code.

4. These embeddings are stored in a specialized vector database optimized for fast similarity search across millions of code chunks.

5. When you search, your query is converted into a vector using the same AI models that processed your code.

6. The system finds the most similar code chunks by comparing your query's vector against stored embeddings.

7. You get relevant code snippets with file locations and context, ranked by semantic similarity to your search.

```mermaid
graph TD
    A[Your workspace] --> B[File sync]
    B --> C[Chunking]
    C --> D[AI embeddings]
    D --> E[Vector database]
    F[Your search query] --> G[Query embedding]
    G --> E
    E --> H[Search results]
```

## Why semantic search?

While tools like `grep` and `ripgrep` are useful for finding exact string matches, semantic search goes further by understanding the meaning behind your code.

If you ask Agent to "update the top navigation", semantic search can find `header.tsx` even though the word "navigation" doesn't appear in the filename. This works because the embeddings understand that "header" and "top navigation" are semantically related.

### Benefits over grep alone

Semantic search provides several advantages:

- **Faster results**: Compute happens during indexing (offline) rather than at runtime, so Agent searches are faster and cheaper
- **Better accuracy**: Custom-trained models retrieve more relevant results than string matching
- **Fewer follow-ups**: Users send fewer clarifying messages and use fewer tokens compared to grep-only search
- **Conceptual matching**: Find code by what it does, not just what it's named

Agent uses **both** grep and semantic search together. Grep excels at finding
exact patterns, while semantic search excels at finding conceptually similar
code. This combination delivers the best results.

## Getting started

### First-time indexing

Indexing begins automatically when you open a workspace. The system scans your workspace structure, uploads files securely, and processes them through AI models to create embeddings. **Semantic search becomes available at 80% completion.**

## Keeping your index updated

### Automatic sync

Cursor automatically keeps your index synchronized with your workspace through periodic checks every 5 minutes. The system intelligently updates only changed files, removing old embeddings and creating new ones as needed. Files are processed in batches for optimal performance, ensuring minimal impact on your development workflow.

### What gets indexed

| File Type           | Action                                     |
| ------------------- | ------------------------------------------ |
| New files           | Automatically added to index               |
| Modified files      | Old embeddings removed, fresh ones created |
| Deleted files       | Promptly removed from index                |
| Large/complex files | May be skipped for performance             |

### Performance and troubleshooting

**Performance**: Uses intelligent batching and caching for accurate, up-to-date results.

**Troubleshooting steps**:

1. Check internet connection
2. Verify workspace permissions
3. Restart Cursor
4. Contact support if issues persist

The indexing system works reliably in the background to keep your code searchable.

## Privacy and security

### Data protection

Your code's privacy is protected through multiple layers of security. File paths are encrypted before being sent to our servers, ensuring your project structure remains confidential. Your actual code content is never stored in plaintext on our servers, maintaining the confidentiality of your intellectual property. Code is only held in memory during the indexing process, then discarded, so there's no permanent storage of your source code.

## Configuration

Cursor indexes all files except those in [ignore files](https://cursor.com/docs/context/ignore-files.md) (e.g. `.gitignore`, `.cursorignore`).

Click `Show Settings` to:

- Enable automatic indexing for new repositories
- Configure which files to ignore

[Ignoring large content files](https://cursor.com/docs/context/ignore-files.md) improves answer
accuracy.

### View indexed files

To see indexed file paths: `Cursor Settings` > `Indexing & Docs` > `View included files`

This opens a `.txt` file listing all indexed files.

## FAQ

### Where can I see all indexed codebases?

No global list exists yet. Check each project individually by opening it in
Cursor and checking Codebase Indexing settings.

### How do I delete all indexed codebases?

Delete your Cursor account from Settings to remove all indexed codebases.
Otherwise, delete individual codebases from each project's Codebase Indexing
settings.

### How long are indexed codebases retained?

Indexed codebases are deleted after 6 weeks of inactivity. Reopening the
project triggers re-indexing.

### Is my source code stored on Cursor servers?

No. Cursor creates embeddings without storing filenames or source code. Filenames are obfuscated and code chunks are encrypted.

When Agent searches the codebase, Cursor retrieves the embeddings from the server and decrypts the chunks.

### Can I customize path encryption?

Create a `.cursor/keys` file in your workspace root for custom path encryption:

```json
{
  "path_decryption_key": "your-custom-key-here"
}
```

### How does team sharing work?

Indexes can be shared across team members for faster indexing of similar codebases. Respects file access permissions and only shares accessible content.

### What is smart index copying?

For team workspaces, Cursor can accelerate indexing by copying from similar codebases with compatible file structures. Happens automatically and respects privacy permissions.

### Does Cursor support multi-root workspaces?

Yes. The Cursor editor supports [multi-root workspaces](https://code.visualstudio.com/docs/editor/workspaces#_multiroot-workspaces), letting you work with multiple codebases:

- All codebases get indexed automatically
- Each codebase's context is available to AI
- `.cursor/rules` work in all folders
- Some features that rely on a single git root, like worktrees, are disabled for multi-root workspaces.

Cursor Cloud Agents do not support multi-root workspaces.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/skills.md
# INDEX: 72/114
================================================================================

# Agent Skills

Agent Skills is an open standard for extending AI agents with specialized capabilities. Skills package domain-specific knowledge and workflows that agents can use to perform specific tasks.

## What are skills?

A skill is a portable, version-controlled package that teaches agents how to perform domain-specific tasks. Skills can include scripts, templates, and references that agents may act on using their tools.

### Portable

Skills work across any agent that supports the Agent Skills standard.

### Version-controlled

Skills are stored as files and can be tracked in your repository, or installed via GitHub repository links.

### Actionable

Skills can include scripts, templates, and references that agents act on using their tools.

### Progressive

Skills load resources on demand, keeping context usage efficient.

## How skills work

When Cursor starts, it automatically discovers skills from skill directories and makes them available to Agent. The agent is presented with available skills and decides when they are relevant based on context.

Skills can also be manually invoked by typing `/` in Agent chat and searching for the skill name.

## Skill directories

Skills are automatically loaded from these locations:

| Location            | Scope               |
| ------------------- | ------------------- |
| `.agents/skills/`   | Project-level       |
| `.cursor/skills/`   | Project-level       |
| `~/.cursor/skills/` | User-level (global) |

For compatibility, Cursor also loads skills from Claude and Codex directories: `.claude/skills/`, `.codex/skills/`, `~/.claude/skills/`, and `~/.codex/skills/`.

Each skill should be a folder containing a `SKILL.md` file:

```text
.agents/
└── skills/
    └── my-skill/
        └── SKILL.md
```

Skills can also include optional directories for scripts, references, and assets:

```text
.agents/
└── skills/
    └── deploy-app/
        ├── SKILL.md
        ├── scripts/
        │   ├── deploy.sh
        │   └── validate.py
        ├── references/
        │   └── REFERENCE.md
        └── assets/
            └── config-template.json
```

## SKILL.md file format

Each skill is defined in a `SKILL.md` file with YAML frontmatter:

```markdown
---
name: my-skill
description: Short description of what this skill does and when to use it.
---

# My Skill

Detailed instructions for the agent.

## When to Use

- Use this skill when...
- This skill is helpful for...

## Instructions

- Step-by-step guidance for the agent
- Domain-specific conventions
- Best practices and patterns
- Use the ask questions tool if you need to clarify requirements with the user
```

### Frontmatter fields

| Field                      | Required | Description                                                                                                                                    |
| -------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                     | Yes      | Skill identifier. Lowercase letters, numbers, and hyphens only. Must match the parent folder name.                                             |
| `description`              | Yes      | Describes what the skill does and when to use it. Used by the agent to determine relevance.                                                    |
| `license`                  | No       | License name or reference to a bundled license file.                                                                                           |
| `compatibility`            | No       | Environment requirements (system packages, network access, etc.).                                                                              |
| `metadata`                 | No       | Arbitrary key-value mapping for additional metadata.                                                                                           |
| `disable-model-invocation` | No       | When `true`, the skill is only included when explicitly invoked via `/skill-name`. The agent will not automatically apply it based on context. |

## Disabling automatic invocation

By default, skills are automatically applied when the agent determines they are relevant. Set `disable-model-invocation: true` to make a skill behave like a traditional slash command, where it is only included in context when you explicitly type `/skill-name` in chat.

## Including scripts in skills

Skills can include a `scripts/` directory containing executable code that agents can run. Reference scripts in your `SKILL.md` using relative paths from the skill root.

```markdown
---
name: deploy-app
description: Deploy the application to staging or production environments. Use when deploying code or when the user mentions deployment, releases, or environments.
---

# Deploy App

Deploy the application using the provided scripts.

## Usage

Run the deployment script: `scripts/deploy.sh <environment>`

Where `<environment>` is either `staging` or `production`.

## Pre-deployment Validation

Before deploying, run the validation script: `python scripts/validate.py`
```

The agent reads these instructions and executes the referenced scripts when the skill is invoked. Scripts can be written in any language—Bash, Python, JavaScript, or any other executable format supported by the agent implementation.

Scripts should be self-contained, include helpful error messages, and handle edge cases gracefully.

## Optional directories

Skills support these optional directories:

| Directory     | Purpose                                                |
| ------------- | ------------------------------------------------------ |
| `scripts/`    | Executable code that agents can run                    |
| `references/` | Additional documentation loaded on demand              |
| `assets/`     | Static resources like templates, images, or data files |

Keep your main `SKILL.md` focused and move detailed reference material to separate files. This keeps context usage efficient since agents load resources progressively—only when needed.

## Viewing skills

To view discovered skills:

1. Open **Cursor Settings** (Cmd+Shift+J on Mac, Ctrl+Shift+J on Windows/Linux)
2. Navigate to **Rules**
3. Skills appear in the **Agent Decides** section

## Installing skills from GitHub

You can import skills from GitHub repositories:

1. Open **Cursor Settings → Rules**
2. In the **Project Rules** section, click **Add Rule**
3. Select **Remote Rule (Github)**
4. Enter the GitHub repository URL

## Migrating rules and commands to skills

Cursor includes a built-in `/migrate-to-skills` skill in 2.4 that helps you convert existing dynamic rules and slash commands to skills.

The migration skill converts:

- **Dynamic rules**: Rules that use the "Apply Intelligently" configuration—rules with `alwaysApply: false` (or undefined) and no `globs` patterns defined. These are converted to standard skills.
- **Slash commands**: Both user-level and workspace-level commands are converted to skills with `disable-model-invocation: true`, preserving their explicit invocation behavior.

To migrate:

1. Type `/migrate-to-skills` in Agent chat
2. The agent will identify eligible rules and commands and convert them to skills
3. Review the generated skills in `.cursor/skills/`

Rules with `alwaysApply: true` or specific `globs` patterns are not migrated, as they have explicit triggering conditions that differ from skill behavior. User rules are also not migrated since they are not stored on the file system.

## Learn more

Agent Skills is an open standard. Learn more at [agentskills.io](https://agentskills.io).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/context/subagents.md
# INDEX: 73/114
================================================================================

# Subagents

Subagents are specialized AI assistants that Cursor's agent can delegate tasks to. Each subagent operates in its own context window, handles specific types of work, and returns its result to the parent agent. Use subagents to break down complex tasks, do work in parallel, and preserve context in the main conversation.

You can use subagents in the editor, CLI, and [Cloud Agents](https://cursor.com/docs/cloud-agent.md).

### Context isolation

Each subagent has its own context window. Long research or exploration tasks don't consume space in your main conversation.

### Parallel execution

Launch multiple subagents simultaneously. Work on different parts of your codebase without waiting for sequential completion.

### Specialized expertise

Configure subagents with custom prompts, tool access, and models for domain-specific tasks.

### Reusability

Define custom subagents and use them across projects.

If you're on a legacy request-based plan without [Max Mode](https://cursor.com/docs/context/max-mode.md) enabled, subagents run using Composer regardless of any `model` configuration. Enable Max Mode to use your specified model. Usage-based plans use the configured model by default.

## How subagents work

When Agent encounters a complex task, it can launch a subagent automatically. The subagent receives a prompt with all necessary context, works autonomously, and returns a final message with its results.

Subagents start with a clean context. The parent agent includes relevant information in the prompt since subagents don't have access to prior conversation history.

### Foreground vs background

Subagents run in one of two modes:

| Mode           | Behavior                                                             | Best for                                    |
| :------------- | :------------------------------------------------------------------- | :------------------------------------------ |
| **Foreground** | Blocks until the subagent completes. Returns the result immediately. | Sequential tasks where you need the output. |
| **Background** | Returns immediately. The subagent works independently.               | Long-running tasks or parallel workstreams. |

## Built-in subagents

Cursor includes three built-in subagents that handle context-heavy operations automatically. These subagents were designed based on analysis of agent conversations where context window limits were hit.

| Subagent    | Purpose                         | Why it's a subagent                                                                                                                            |
| :---------- | :------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| **Explore** | Searches and analyzes codebases | Codebase exploration generates large intermediate output that would bloat the main context. Uses a faster model to run many parallel searches. |
| **Bash**    | Runs series of shell commands   | Command output is often verbose. Isolating it keeps the parent focused on decisions, not logs.                                                 |
| **Browser** | Controls browser via MCP tools  | Browser interactions produce noisy DOM snapshots and screenshots. The subagent filters this down to relevant results.                          |

### Why these subagents exist

These three operations share common traits: they generate noisy intermediate output, benefit from specialized prompts and tools, and can consume significant context. Running them as subagents solves several problems:

- **Context isolation** — Intermediate output stays in the subagent. The parent only sees the final summary.
- **Model flexibility** — The explore subagent uses a faster model by default. This enables running 10 parallel searches in the time a single main-agent search would take.
- **Specialized configuration** — Each subagent has prompts and tool access tuned for its specific task.
- **Cost efficiency** — Faster models cost less. Isolating token-heavy work in subagents with appropriate model choices reduces overall cost.

You don't need to configure these subagents. Agent uses them automatically when appropriate.

## When to use subagents

| Use subagents when...                                     | Use skills when...                                      |
| :-------------------------------------------------------- | :------------------------------------------------------ |
| You need context isolation for long research tasks        | The task is single-purpose (generate changelog, format) |
| Running multiple workstreams in parallel                  | You want a quick, repeatable action                     |
| The task requires specialized expertise across many steps | The task completes in one shot                          |
| You want an independent verification of work              | You don't need a separate context window                |

If you find yourself creating a subagent for a simple, single-purpose task like "generate a changelog" or "format imports," consider using a [skill](https://cursor.com/docs/context/skills.md) instead.

## Quick start

Agent automatically uses subagents when appropriate. You can also create a custom subagent by asking Agent:

Create a subagent file at .cursor/agents/verifier.md with YAML frontmatter (name, description) followed by the prompt. The verifier subagent should validate completed work, check that implementations are functional, run tests, and report what passed vs what's incomplete.

For more control, create custom subagents manually in your project or user directory.

## Custom subagents

Define custom subagents to encode specialized knowledge, enforce team standards, or automate repetitive workflows.

### File locations

| Type                  | Location            | Scope                                                |
| :-------------------- | :------------------ | :--------------------------------------------------- |
| **Project subagents** | `.cursor/agents/`   | Current project only                                 |
|                       | `.claude/agents/`   | Current project only (Claude compatibility)          |
|                       | `.codex/agents/`    | Current project only (Codex compatibility)           |
| **User subagents**    | `~/.cursor/agents/` | All projects for current user                        |
|                       | `~/.claude/agents/` | All projects for current user (Claude compatibility) |
|                       | `~/.codex/agents/`  | All projects for current user (Codex compatibility)  |

Project subagents take precedence when names conflict. When multiple locations contain subagents with the same name, `.cursor/` takes precedence over `.claude/` or `.codex/`.

### File format

Each subagent is a markdown file with YAML frontmatter:

```markdown
---
name: security-auditor
description: Security specialist. Use when implementing auth, payments, or handling sensitive data.
model: inherit
---

You are a security expert auditing code for vulnerabilities.

When invoked:
1. Identify security-sensitive code paths
2. Check for common vulnerabilities (injection, XSS, auth bypass)
3. Verify secrets are not hardcoded
4. Review input validation and sanitization

Report findings by severity:
- Critical (must fix before deploy)
- High (fix soon)
- Medium (address when possible)
```

### Configuration fields

| Field           | Required | Description                                                                                   |
| :-------------- | :------- | :-------------------------------------------------------------------------------------------- |
| `name`          | No       | Unique identifier. Use lowercase letters and hyphens. Defaults to filename without extension. |
| `description`   | No       | When to use this subagent. Agent reads this to decide delegation.                             |
| `model`         | No       | Model to use: `fast`, `inherit`, or a specific model ID. Defaults to `inherit`.               |
| `readonly`      | No       | If `true`, the subagent runs with restricted write permissions.                               |
| `is_background` | No       | If `true`, the subagent runs in the background without waiting for completion.                |

## Using subagents

### Automatic delegation

Agent proactively delegates tasks based on:

- The task complexity and scope
- Custom subagent descriptions in your project
- Current context and available tools

Include phrases like "use proactively" or "always use for" in your description field to encourage automatic delegation.

### Explicit invocation

Request a specific subagent by using the `/name` syntax in your prompt:

```text
> /verifier confirm the auth flow is complete
> /debugger investigate this error
> /security-auditor review the payment module
```

You can also invoke subagents by mentioning them naturally:

```text
> Use the verifier subagent to confirm the auth flow is complete
> Have the debugger subagent investigate this error
> Run the security-auditor subagent on the payment module
```

### Parallel execution

Launch multiple subagents concurrently for maximum throughput:

```text
> Review the API changes and update the documentation in parallel
```

Agent sends multiple Task tool calls in a single message, so subagents run simultaneously.

## Resuming subagents

Subagents can be resumed to continue previous conversations. This is useful for long-running tasks that span multiple invocations.

Each subagent execution returns an agent ID. Pass this ID to resume the subagent with full context preserved:

```text
> Resume agent abc123 and analyze the remaining test failures
```

Background subagents write their state as they run. You can resume a subagent after it completes to continue the conversation with preserved context.

## Common patterns

### Verification agent

A verification agent independently validates whether claimed work was actually completed. This addresses a common issue where AI marks tasks as done but implementations are incomplete or broken.

```markdown
---
name: verifier
description: Validates completed work. Use after tasks are marked done to confirm implementations are functional.
model: fast
---

You are a skeptical validator. Your job is to verify that work claimed as complete actually works.

When invoked:
1. Identify what was claimed to be completed
2. Check that the implementation exists and is functional
3. Run relevant tests or verification steps
4. Look for edge cases that may have been missed

Be thorough and skeptical. Report:
- What was verified and passed
- What was claimed but incomplete or broken
- Specific issues that need to be addressed

Do not accept claims at face value. Test everything.
```

Create a subagent file at .cursor/agents/verifier.md with YAML frontmatter containing name, description, and model: fast. The description should be 'Validates completed work. Use after tasks are marked done to confirm implementations are functional.' The prompt body should instruct it to be skeptical, verify implementations actually work by running tests, and look for edge cases.

This pattern is useful for:

- Validating that features work end-to-end before marking tickets complete
- Catching partially implemented functionality
- Ensuring tests actually pass (not just that test files exist)

### Orchestrator pattern

For complex workflows, a parent agent can coordinate multiple specialist subagents in sequence:

1. **Planner** analyzes requirements and creates a technical plan
2. **Implementer** builds the feature based on the plan
3. **Verifier** confirms the implementation matches requirements

Each handoff includes structured output so the next agent has clear context.

## Example subagents

### Debugger

```markdown
---
name: debugger
description: Debugging specialist for errors and test failures. Use when encountering issues.
---

You are an expert debugger specializing in root cause analysis.

When invoked:
1. Capture error message and stack trace
2. Identify reproduction steps
3. Isolate the failure location
4. Implement minimal fix
5. Verify solution works

For each issue, provide:
- Root cause explanation
- Evidence supporting the diagnosis
- Specific code fix
- Testing approach

Focus on fixing the underlying issue, not symptoms.
```

Create a subagent file at .cursor/agents/debugger.md with YAML frontmatter containing name and description. The debugger subagent should specialize in root cause analysis: capture stack traces, identify reproduction steps, isolate failures, implement minimal fixes, and verify solutions.

### Test runner

```markdown
---
name: test-runner
description: Test automation expert. Use proactively to run tests and fix failures.
---

You are a test automation expert.

When you see code changes, proactively run appropriate tests.

If tests fail:
1. Analyze the failure output
2. Identify the root cause
3. Fix the issue while preserving test intent
4. Re-run to verify

Report test results with:
- Number of tests passed/failed
- Summary of any failures
- Changes made to fix issues
```

Create a subagent file at .cursor/agents/test-runner.md with YAML frontmatter containing name and description (mentioning 'Use proactively'). The test-runner subagent should proactively run tests when it sees code changes, analyze failures, fix issues while preserving test intent, and report results.

## Best practices

- **Write focused subagents** — Each subagent should have a single, clear responsibility. Avoid generic "helper" agents.
- **Invest in descriptions** — The `description` field determines when Agent delegates to your subagent. Spend time refining it. Test by making prompts and checking if the right subagent gets triggered.
- **Keep prompts concise** — Long, rambling prompts dilute focus. Be specific and direct.
- **Add subagents to version control** — Check `.cursor/agents/` into your repository so the team benefits.
- **Start with Agent-generated agents** — Let Agent help you draft the initial configuration, then customize.
- **Use hooks for file output** — If you need subagents to produce structured output files, consider using [hooks](https://cursor.com/docs/agent/hooks.md) to process and save their results consistently.

### Anti-patterns to avoid

**Don't create dozens of generic subagents.** Having 50+ subagents with vague instructions like "helps with coding" is ineffective. Agent won't know when to use them, and you'll waste time maintaining them.

- **Vague descriptions** — "Use for general tasks" gives Agent no signal about when to delegate. Be specific: "Use when implementing authentication flows with OAuth providers."
- **Overly long prompts** — A 2,000-word prompt doesn't make a subagent smarter. It makes it slower and harder to maintain.
- **Duplicating slash commands** — If a task is single-purpose and doesn't need context isolation, use a [slash command](https://cursor.com/docs/agent/chat/commands.md) instead.
- **Too many subagents** — Start with 2-3 focused subagents. Add more only when you have clear, distinct use cases.

## Managing subagents

### Creating subagents

The easiest way to create a subagent is to ask Agent to create one for you:

Create a subagent file at .cursor/agents/security-reviewer.md with YAML frontmatter containing name and description. The security-reviewer subagent should check code for common vulnerabilities like injection, XSS, and hardcoded secrets.

You can also create subagents manually by adding markdown files to `.cursor/agents/` (project) or `~/.cursor/agents/` (user).

### Viewing subagents

Agent includes all custom subagents in its available tools. You can see which subagents are configured by checking the `.cursor/agents/` directory in your project.

## Performance and cost

Subagents have trade-offs. Understanding them helps you decide when to use them.

| Benefit            | Trade-off                                                     |
| :----------------- | :------------------------------------------------------------ |
| Context isolation  | Startup overhead (each subagent gathers its own context)      |
| Parallel execution | Higher token usage (multiple contexts running simultaneously) |
| Specialized focus  | Latency (may be slower than main agent for simple tasks)      |

### Token and cost considerations

- **Subagents consume tokens independently** — Each subagent has its own context window and token usage. Running five subagents in parallel uses roughly five times the tokens of a single agent.
- **Evaluate the overhead** — For quick, simple tasks, the main agent is often faster. Subagents shine for complex, long-running, or parallel work.
- **Subagents can be slower** — The benefit is context isolation, not speed. A subagent doing a simple task may be slower than the main agent because it starts fresh.

## FAQ

### What are the built-in subagents?

Cursor includes three built-in subagents: `explore` for codebase search, `bash` for running shell commands, and `browser` for browser automation via MCP. These handle context-heavy operations automatically. You don't need to configure them.

### Can subagents launch other subagents?

Subagents run as single-level helpers. Nested subagents are unsupported today.

### How do I see what a subagent is doing?

Background subagents write output to `~/.cursor/subagents/`. The parent agent can read these files to check progress.

### What happens if a subagent fails?

The subagent returns an error status to the parent agent. The parent can retry, resume with additional context, or handle the failure differently.

### Can I use MCP tools in subagents?

Yes. Subagents inherit all tools from the parent, including MCP tools from configured servers.

### How do I debug a misbehaving subagent?

Check the subagent's description and prompt. Ensure the instructions are specific and unambiguous. You can also test the subagent by invoking it explicitly with a simple task.

### Why is my subagent using a different model?

If you're on a legacy request-based plan without [Max Mode](https://cursor.com/docs/context/max-mode.md) enabled, subagents run using Composer regardless of any `model` configuration. Enable Max Mode from the model picker to use your specified model. Usage-based plans use the configured model by default.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/agent-workflows.md
# INDEX: 74/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/bugbot-rules.md
# INDEX: 75/114
================================================================================

# Reviewing Database Migrations with Bugbot Rules

Bugbot rules automate code review by catching issues before they reach human reviewers. At Cursor, we use them for a variety of things, including catching database migration issues before they're merged.

## Review guidelines

Bugbot rules are markdown files that tell Bugbot exactly what to look for during code reviews. `.cursor/BUGBOT.md` files can be placed anywhere in the repository. Bugbot automatically includes the root file and traverses upward from changed files to find relevant context. When a PR opens, Bugbot reviews changes against these rules and comments on issues instantly.

## Database migrations get caught before merge

Database migrations can lock tables, cause downtime, or corrupt data if done incorrectly. Bugbot has eliminated most manual review work for DB migrations. By the time a human reviewer opens the PR, Bugbot has already flagged most things they would have caught.

Here's an example of a recent migration issue Bugbot caught:

![Bugbot catching a database migration issue](/docs-static/images/cookbook/bugbot-rules.png)

To catch Cursor infra-specific bugs, we've defined a set of review guidelines that Bugbot follows extra carefully when scanning code. Here's the rule we're using for catching the bug seen above:

```text
# Review Guidelines

## Database migrations

- When reviewing database migrations, ensure that they are backwards compatible. Specifically:

  - New tables, and new nullable or default columns on existing tables are OK.

  - New indices on existing tables (not brand new ones) must be created with keyword CONCURRENTLY. The statement should be isolated to its own migration file to avoid a prisma transaction error. You should warn on index creation and flag it for careful review.

  - Removing foreign keys and constraints is OK

  - Adding foreign keys is NOT OK

  - Removing indices is OK

  - Dropping columns is NOT OK. Instead, you should mark it as deprecated in the schema, and add a `@map` that corresponds to the original column name. For example, to deprecate the `hostname` column, you can change `hostname String?` to `hostname_DEPRECATED String? @map("hostname")`.

  - Renaming columns in the database, changing column types, or changing default values are NOT OK.

    - Exception: It is OK to increase the size of a VARCHAR column.

    - Exception: It is OK to make a non-null column nullable.

  - Dropping tables is NOT OK

- Enforce good guidelines when creating new tables and columns:

  - Prefer BIGINTEGER and BIGSERIAL over INTEGER and SERIAL, unless if you are absolutely sure that it will remain small (O(teams) or lower cardinality)

  - Using foreign keys for new tables is NOT OK. Handle this in the application layer instead.

  - Using cascading deletes for new tables is NOT OK, since a single delete may require the database to do an unbounded amount of work. Handle this in the application layer instead.

  - Prefer TEXT over VARCHAR

- Migrations and their corresponding schema.prisma changes should be isolated to their own PR when possible. We do not want unnecessary code changes that may need to be reverted to be coupled with migrations that have already been applied to production.

## Queries

- All new queries to maindb MUST use an index. It is NOT OK for the query to potentially execute a full table scan.

- All new queries to maindb MUST NOT do a `GROUP BY` or `JOIN`. Handle this in the application layer instead.

- Avoid Prisma's `skip` or SQL `OFFSET/LIMIT` on large tables - use cursor-based pagination instead by ordering on an indexed column
```

When an engineer creates an index without `CONCURRENTLY`, Bugbot flags it with a clear explanation and fix before any human opens the PR:

## Enforce team standards automatically

Bugbot rules work for any mechanical, rule-based review process. Some other examples we've seen:

- **Security reviews** block exposed secrets, unsafe API calls, or missing authentication checks.

- **Analytics standards** verify proper event tracking and naming conventions.

- **Code cleanliness** prevents untracked `TODO` comments:

```text
If any changed file contains /(?:^|\s)(TODO|FIXME)(?:\s*:|\s+)/, then:
- Add a non-blocking Bug titled "TODO/FIXME comment found"
- Body: "Replace TODO/FIXME with a tracked issue reference, e.g., `TODO(#1234): ...`, or remove it."
- If the TODO already references an issue pattern /#\d+|[A-Z]+-\d+/, mark the Bug as resolved automatically.
```

Bugbot handles mechanical review instantly and consistently. Engineers get immediate feedback, dangerous changes are caught before merge, and human reviewers focus on architecture and logic instead of style guides.

Create `.cursor/BUGBOT.md` in your repo with your team's rules. Bugbot will automatically enforce them on every PR. [Read more about Bugbot rules](https://cursor.com/docs/bugbot.md).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/building-mcp-server.md
# INDEX: 76/114
================================================================================

# Building an MCP Server

## Introduction

MCP servers let you connect custom data sources and make them available for use inside Cursor. This is particularly useful when you need context from places such as browsers, databases, or error and system logs. Setting up an MCP server is straightforward, and with Cursor it can be done quickly.

In this guide, we will walk through how to build an MCP server for Postgres. Our goal is to enable Cursor to run SQL queries directly against a Postgres database and to expose table schemas in a structured way.

This tutorial is designed to teach the fundamentals of building MCP servers.

[Media](/docs-static/images/guides/tutorials/building-mcp-server/demo.mp4)

Your browser does not support the video tag.

```mermaid
graph LR
    A[User in Cursor] --> B[Cursor]
    B <--> C["MCP Server (stdio)"]
    C <--> D[(Postgres Database)]

    subgraph Local Machine
      B
      C
    end
    class B cursor
    class C mcp
    class D db
```

## What is an MCP Server?

An [MCP server](/en/context/mcp) is a process that communicates with Cursor and provides access to external data or actions. It can be implemented in several ways, but here we will use the simplest method: a server that runs locally on your computer over [stdio](https://en.wikipedia.org/wiki/Standard_streams) (standard input/output streams). This avoids complicated security considerations and allows us to focus on the MCP logic itself.

One of the most common use cases for MCP is database access. When building dashboards, running analyses, or creating migrations, it is often necessary to query and inspect a database. Our Postgres MCP server will support two core capabilities: running arbitrary queries and listing table schemas.

Although both of these tasks could be performed with plain SQL, MCP offers features that make them more powerful and more generally useful. Tools provide a way to expose actions such as executing queries, while resources allow us to share standardized context such as schema information. Later in this guide we will also look at prompts, which enable more advanced workflows.

Under the hood, we will rely on the postgres npm package to execute SQL statements against the database. The MCP SDK will serve as a wrapper around these calls, letting us integrate Postgres functionality seamlessly into Cursor.

## How to Build the MCP Server

The first step in building the server is to setup a new project. We'll start with creating a new folder and initializing a Bun project

```bash
> mkdir postgres-mcp-server
> Bun init
```

From here, we'll select `Blank` project. Once our boilerplate is setup, we need to install the required dependencies. `zod` is required to define schemas for i/o in MCP sdk

```bash
bun add postgres @modelcontextprotocol/sdk zod
```

From here, we'll go to the repositories for each of the libraries and get the link to the raw file contents of each respective README files. We'll use these for context when building the server

- `postgres`
  - Repo:  [https://github.com/porsager/postgres](https://github.com/porsager/postgres),
  - README: [https://raw.githubusercontent.com/porsager/postgres/refs/heads/master/README.md](https://raw.githubusercontent.com/porsager/postgres/refs/heads/master/README.md)
- `@modelcontextprotocol/sdk`:
  - Repo: [https://github.com/modelcontextprotocol/typescript-sdk](https://github.com/modelcontextprotocol/typescript-sdk)
  - README: [https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/refs/heads/main/README.md](https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/refs/heads/main/README.md)

Now, we'll define how we want the server to behave. To do that, we'll create a `spec.md` and write out the high level goals

```markdown
# Spec

- Allow defining DATABASE_URL through MCP env configuration
- Query postgres data through tool
  - By default, make it readonly
  - Allow write ops by setting ENV `DANGEROUSLY_ALLOW_WRITE_OPS=true|1`
- Access tables as `resources`
- Use Zod for schema definitions
```

As you can see, this is quite a lightweight spec. Feel free to add more details as needed. Together with the README links, we'll construct the final prompt

```markdown
Read the following and follow @spec.md to understand what we want. All necessary dependencies are installed
- @https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/refs/heads/main/README.md
- @https://raw.githubusercontent.com/porsager/postgres/refs/heads/master/README.md
```

With these three components in place (the specification, the MCP SDK documentation, and the Postgres library documentation), we can use Cursor to scaffold the server implementation. Cursor will help us stitch the pieces together, generating the code that connects the MCP SDK with Postgres.

After some back and forth prompting, we now have a first version of the MCP server going. To try it out, we can use the [MCP Inspector](https://modelcontextprotocol.io/legacy/tools/inspector)

```bash
npx @modelcontextprotocol/inspector bun run index.ts
```

## Testing the MCP Server

Once the initial implementation is complete, we can test it using the MCP Inspector. The inspector provides a way to see what the server exposes and to verify that the tools and resources behave as expected. We should confirm that queries can be executed and that schema information is returned correctly.

![MCP Inspector interface](/docs-static/images/guides/tutorials/building-mcp-server/inspector.png)

When everything looks good, we can connect the server to Cursor itself and test it in a real environment. At this point, Cursor will be able to use the Postgres MCP server as if it were a built-in capability, letting us query and inspect the database directly.

[Media](/docs-static/images/guides/tutorials/building-mcp-server/mcp-mermaid.mp4)

Your browser does not support the video tag.

## Next Steps

Running the MCP server locally over stdio is a great starting point, but teams often require shared access to the same database through their MCP server. In these scenarios, deploying the MCP server as a centralized HTTP service becomes necessary.

A deployed MCP server offers several advantages over individual stdio instances:

- **Shared database access:** Multiple team members can query the same database instance through Cursor
- **Centralized configuration:** Schema updates and permission changes are managed in one location
- **Enhanced security:** Proper authentication, rate limiting, and access controls can be implemented
- **Observability:** Usage patterns and performance metrics can be monitored across the team

To achieve this, you would switch the transport method from stdio to HTTP.

While we won't cover the whole setup, here's a good starting prompt you can give to Cursor

Based on the existing MCP server, create a new file that implements the HTTP protocol. Move shared logic to mcp-core, and name each transport implementation by name (mcp-server-stdio, mcp-server-http). @https\://raw\.githubusercontent.com/modelcontextprotocol/typescript-sdk/refs/heads/main/README.md

The final results can be seen here: [pg-mcp-server](https://github.com/ericzakariasson/pg-mcp-server)

```mermaid
graph LR
    subgraph Team_Network_or_Cloud["VPC"]
      SVC["MCP Server (HTTP transport)"] <--> DB[(Postgres DB)]
    end

    Dev1["Developer 1 on Cursor"] -->|HTTP| SVC
    Dev2["Developer 2 on Cursor"] -->|HTTP| SVC
    Dev3["Developer 3 on Cursor"] -->|HTTP| SVC

    subgraph SVC_Internals["Internals"]
      direction TB
      T1["Auth and ACLs"]
      T2["Rate limiting and logging"]
      T3["Tool: query"]
      T4["Resource: table_schemas"]
      T5["Prompts"]
      T1 --> T2 --> T3
      T3 --> T4
      T3 --> T5
    end

    SVC --> SVC_Internals

    class SVC svc
    class DB db
    class T1,T2,T3,T4,T5 internals
    class Dev1,Dev2,Dev3 dev
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/data-science.md
# INDEX: 77/114
================================================================================

# Data Science

Cursor provides integrated tooling for data science development through reproducible environments, notebook
support, and AI-powered code assistance. This guide covers essential setup patterns for Python, R, and SQL
workflows.

## Notebook development

For full notebook support, download the Jupyter (id: ms-toolsai.jupyter) extension, published by ms-toolsai.

Cursor supports both `.ipynb` and `.py` files with integrated cell execution. Tab, Inline Edit, and Agents
work within notebooks, just as they do in other code files.

Key capabilities:

- **Inline cell execution** runs code directly within the editor interface
- **Tab, Inline Edit, and Agent** all understand data science libraries including pandas, NumPy, scikit-learn, and SQL magic commands

## Database integration

Databases can be integrated with Cursor through two main mechanisms: MCP servers and Extensions.

- **MCP Servers** let your Agents connect with your databases
- **Extensions** integrate your broader editor with your databases

### Via MCP

MCP servers allow your agent to make queries directly against your database. This allows your agent to choose to query your database, write the appropriate query, run the command and analyze outputs, all as part of an ongoing task.

For example, you can connect a Postgres database to your Cursor instance by adding the following [MCP config](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/postgres) to Cursor:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://localhost/mydb"
      ]
    }
  }
}
```

For more on MCP, see our [MCP documentation](https://cursor.com/docs/context/mcp.md).

[Media](/docs-static/images/guides/advanced/datascience/postgres-mcp.mp4)

Your browser does not support the video tag.

### Via Extensions

Install database-specific extensions (PostgreSQL, BigQuery, SQLite, Snowflake) to execute queries directly from the editor. This eliminates context switching between tools and enables AI assistance for query optimization.

```sql
-- Cursor provides suggestions for indexes, window functions, and query optimization
SELECT
    user_id,
    event_type,
    COUNT(*) as event_count,
    RANK() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC) as frequency_rank
FROM events
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY user_id, event_type;
```

Use Agents to analyze slow queries, suggest performance improvements, or generate visualization code for query results. Cursor understands SQL context and can recommend appropriate chart types based on your data structure.

![Snowflake Extension](/docs-static/images/guides/advanced/datascience/snowflake-extension.png)

## Data visualization

Cursor's AI assistance extends to data visualization libraries including Matplotlib, Plotly, and Seaborn. The agent can generate code for data visualization, helping you quickly and easily explore data, while creating a replicable and shareable artifact.

```python
import plotly.express as px
import pandas as pd

# AI suggests relevant plot types based on data columns
df = pd.read_csv('sales_data.csv')
fig = px.scatter(df, x='advertising_spend', y='revenue',
                 color='region', size='customer_count',
                 title='Revenue vs Advertising Spend by Region')
fig.show()
```

[Media](/docs-static/images/guides/advanced/datascience/datascience-visualization.mp4)

Your browser does not support the video tag.

## Frequently asked questions

**Can I use existing Jupyter notebooks?**
Yes, Cursor opens `.ipynb` files with full cell execution and AI completion support.

**How do I handle large datasets that don't fit in memory?**
Use distributed computing libraries like Dask or connect to Spark clusters through Remote-SSH connections to larger machines.

**Does Cursor support R and SQL files?**
Yes, Cursor provides AI assistance and syntax highlighting for R scripts (`.R`) and SQL files (`.sql`).

**What's the recommended way to share development environments?**
Commit the `.devcontainer` folder to version control. Team members can rebuild the environment automatically when opening the project.

**How do I debug data processing pipelines?**
Use Cursor's integrated debugger with breakpoints in Python scripts, or leverage Agent to analyze and explain complex data transformations step by step.

## Environment reproducibility

### Development containers

Development containers help you ensure consistent runtimes and dependencies across team members and deployment environments. They can eliminate environment-specific bugs and reduce onboarding time for new team members.

To use a development container, start by creating a `.devcontainer` folder in your repository root. Next, create a `devcontainer.json`, `Dockerfile`, and `requirements.txt` file.

```json
{
  "name": "ds-env",
  "build": { "dockerfile": "Dockerfile" },
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.11" }
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

```dockerfile
# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.11
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
```

```txt
# requirements.txt
pandas==2.3.0
numpy
# add other dependencies you need for your project
```

Cursor will automatically detect the devcontainer and prompt you to reopen your project within a container. Alternatively, you can manually reopen in a container using the Command Palette (Cmd+Shift+P) and searching for `Reopen in Container`.

Development containers provide several advantages:

- **Dependency isolation** prevents conflicts between projects
- **Reproducible builds** ensure consistent behavior across development and production environments
- **Simplified onboarding** allows new team members to start immediately without manual setup

### Remote development with SSH

When your analysis requires additional compute resources, GPUs, or access to private datasets, connect to remote machines while maintaining your local development environment.

1. Provision a cloud instance or access an on-premises server with required resources
2. Clone your repository to the remote machine, including the `.devcontainer` configuration
3. Connect through Cursor: Cmd+Shift+P → "Remote-SSH: Connect to Host"

This approach maintains consistent tooling while scaling compute resources as needed. The same development container configuration works across local and remote environments.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/large-codebases.md
# INDEX: 78/114
================================================================================

# Large Codebases

Cursor is built to work well with large codebases out of the box. [Semantic Search](https://cursor.com/docs/context/semantic-search.md) powered by [Large Codebase Indexing](https://cursor.com/blog/secure-codebase-indexing) enables Cursor to quickly understand and navigate even the largest repositories, making it easy to find relevant code and get accurate answers about your codebase.

Beyond these built-in capabilities, there are additional techniques you can use to further improve performance and get even better results. Drawing from both our experience scaling Cursor's own codebase and insights from customers managing massive codebases, we've discovered some useful patterns for handling increased complexity.

Let's explore some of these techniques that we've found useful for large codebases.

## Use Chat to quickly get up to speed on unfamiliar code

Navigating a large codebase, especially if it's new to you, can be challenging. You often grep, search, and click around to find the specific parts of the codebase you're looking for. With [Chat](https://cursor.com/docs/chat/overview.md), you can start asking questions to find what you're looking for and get a detailed explanation of how it works.

Here we're getting help to find implementation details of semantic search in Cursor, and even asking for some examples to make it easier to understand.

[Media](/docs-static/images/guides/advanced/large-codebases/qa.mp4)

## Write rules for domain-specific knowledge

If you were onboarding a new collaborator into your codebase, what context would you give them to make sure they can start doing meaningful contributions?

Your answer to this question is likely valuable information for Cursor to understand as well. For every organization or project, there's latent knowledge that might not be fully captured in your documentation. Using rules effectively is the single best way to ensure Cursor is getting the full picture.

For example, if you're writing instructions for how to implement a new feature or service, consider writing a short rule to document it for posterity.

```markdown
---
description: Add a new VS Code frontend service
---

1. **Interface Definition:**
   - Define a new service interface using `createDecorator` and ensure `_serviceBrand` is included to avoid errors.

2. **Service Implementation:**
   - Implement the service in a new TypeScript file, extending `Disposable`, and register it as a singleton with `registerSingleton`.

3. **Service Contribution:**
   - Create a contribution file to import and load the service, and register it in the main entrypoint.

4. **Context Integration:**
   - Update the context to include the new service, allowing access throughout the application.
```

If there are common formatting patterns that you want to make sure Cursor adheres to, consider auto-attaching rules based on glob patterns.

```markdown
---
globs: *.ts
---
- Use bun as package manager. See [package.json](mdc:backend/reddit-eval-tool/package.json) for scripts
- Use kebab-case for file names
- Use camelCase for function and variable names
- Use UPPERCASE_SNAKE_CASE for hardcoded constants
- Prefer `function foo()` over `const foo = () =>`
- Use `Array<T>` instead of `T[]`
- Use named exports over default exports, e.g (`export const variable ...`, `export function `)
```

## Stay close to the plan-creation process

For larger changes, spending an above-average amount of thought to create a precise, well-scoped plan can significantly improve Cursor's output.

If you find that you're not getting the result you want after a few different variations of the same prompt, consider zooming out and creating a more detailed plan from scratch, as if you were creating a PRD for a coworker. Oftentimes **the hard part is figuring out what** change should be made, a task suited well for humans. With the right instructions, we can delegate some parts of the implementation to Cursor.

One way to use AI to augment the plan-creation process is to use Ask mode. To create a plan, turn on Ask mode in Cursor and dump whatever context you have from your project management systems, internal docs, or loose thoughts. Think about what files and dependencies you have in the codebase that you already know you want to include. This can be a file that includes pieces of code you want to integrate with, or perhaps a whole folder.

Here's an example prompt:

```mdc title="Planning prompt"
- create a plan for how we should create a new feature (just like @existingfeature.ts)
- ask me questions (max 3) if anything is unclear
- make sure to search the codebase

here's some more context from [project management tool]:
[pasted ticket description]
```

We're asking the model to create a plan and gather context by asking the human questions, referencing any earlier exploration prompts and also the ticket descriptions. Using a thinking model like `claude-opus-4.6`, `gpt-5.3-codex`, or `gemini-3.1-pro` is recommended as they can understand the intent of the change and better synthesize a plan.

From this, you can iteratively formulate the plan with the help of Cursor before starting implementation.

## Pick the right tool for the job

One of the most important skills in using Cursor effectively is choosing the right tool for the job. Think about what you're trying to accomplish and pick the approach that will keep you in flow.

| **Tool**                                                           | **Use case**               | **Strength**                     | **Limitation**        |
| :----------------------------------------------------------------- | :------------------------- | :------------------------------- | :-------------------- |
| **[Tab](https://cursor.com/docs/tab/overview.md)**                 | Quick, manual changes      | Full control, fast               | Single-file           |
| **[Inline Edit](https://cursor.com/docs/inline-edit/overview.md)** | Scoped changes in one file | Focused edits                    | Single-file           |
| **[Chat](https://cursor.com/docs/chat/overview.md)**               | Larger, multi-file changes | Auto-gathers context, deep edits | Slower, context-heavy |

Each tool has its sweet spot:

- Tab is your go-to for quick edits where you want to be in the driver's seat
- Inline Edit shines when you need to make focused changes to a specific section of code
- Chat is perfect for those bigger changes where you need Cursor to understand the broader context

When you're using Chat mode (which can feel a bit slower but is incredibly powerful), help it help you by providing good context. Use [@files](https://cursor.com/docs/context/mentions.md) to point to similar code you want to emulate, or [@folder](https://cursor.com/docs/context/mentions.md) to give it a better understanding of your project structure. And don't be afraid to break bigger changes into smaller chunks - starting fresh chats helps keep things focused and efficient.

## Takeaways

- Scope down changes and don't try to do too much at once
- Include relevant context when you can
- Use Chat, Inline Edit & Tab for what they're best at
- Create new chats often
- Plan with [Ask mode](https://cursor.com/docs/agent/modes.md), implement with [Agent mode](https://cursor.com/docs/agent/overview.md)


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/mermaid-diagrams.md
# INDEX: 79/114
================================================================================

# Mermaid Diagrams

Architectural diagrams help you make sense of how your system works. You can use them to explore logic, track data, and communicate structure. Cursor supports generating these diagrams directly using tools like Mermaid, so you can go from code to visual in just a few prompts.

![Example of an architectural diagram](/docs-static/images/guides/tutorials/architectural-diagrams/postgres-flowchart.png)

## Why diagrams matter

Diagrams clarify how data flows and how components interact. They're useful when you:

- Want to understand flow control in your codebase
- Need to trace data lineage from input to output
- Are onboarding others or documenting your system

They're also great for debugging and asking smarter questions. Visuals help you (and the model) see the bigger picture.

## Two dimensions to consider

There are a few different angles to think about:

- **Purpose**: Are you mapping logic, data flow, infrastructure, or something else?
- **Format**: Do you want something quick (like a Mermaid diagram) or formal (like UML)?

## How to prompt

Start with a clear goal. Here are some common ways to ask:

- **Flow control**: "Show me how requests go from the controller to the database."
- **Data lineage**: "Trace this variable from where it enters to where it ends up."
- **Structure**: "Give me a component-level view of this service."

You can include start and end points, or ask Cursor to find the full path.

## Working with Mermaid

Mermaid is simple to learn and renders directly in Markdown (with the right extension). Cursor can generate diagrams like:

- `flowchart` for logic and sequences
- `sequenceDiagram` for interactions
- `classDiagram` for object structure
- `graph TD` for simple directional maps

```mermaid
sequenceDiagram
    participant User
    participant Server
    participant Database

    User->>Server: Submit Form
    Server->>Database: Save Entry
    Database-->>Server: Success
    Server-->>User: Confirmation

```

You can install the [Mermaid extension](https://marketplace.cursorapi.com/items?itemName=bierner.markdown-mermaid) to preview diagrams.

1. Go to Extensions tab
2. Search for Mermaid and install the extension

## Diagram strategy

Start small. Don't aim to map everything at once.

- Pick one function, route, or process
- Ask Cursor to diagram that part using Mermaid
- Once you have a few, ask it to combine them

This mirrors the **C4 model** – where you start at a low level (code or components) and work upward to higher-level overviews.

### Recommended flow

1. Start with a detailed, low-level diagram
2. Summarize it into a mid-level view
3. Repeat until you reach the level of abstraction you want
4. Ask Cursor to merge them into a single diagram or system map

```mermaid
graph TD
    subgraph Level 1: Low-level components
        A1[AuthService] --> A2[TokenValidator]
        A1 --> A3[UserDB]
        B1[PaymentService] --> B2[BillingEngine]
        B1 --> B3[InvoiceDB]
    end

    subgraph Level 2: Mid-level systems
        A[User System] --> A1
        B[Billing System] --> B1
    end

    subgraph Level 3: High-level application
        App[Main App] --> A
        App --> B
    end

```

## Takeaways

- Use diagrams to understand flow, logic, and data
- Start with small prompts and grow your diagram from there
- Mermaid is the easiest format to work with in Cursor
- Start low-level and abstract upward, just like in the C4 model
- Cursor can help you generate, refine, and combine diagrams with ease


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/cookbook/web-development.md
# INDEX: 80/114
================================================================================

# Web Development

Web development involves fast iterations and tight feedback loops between Cursor and external tools like Figma or the browser. At Cursor, we've found workflows that tighten this loop. Clear task scoping, reusing components, and leveraging design systems help keep things fast and consistent.

This guide covers how to set up Cursor to support web development and tighten the feedback loop.

## Start orchestrating in Cursor

**Chat** is great for bootstrapping changes. Once the major pieces are in place, switching to **Inline Edit** and **Tab** helps maintain your flow state.

After setting up Cursor, you'll be able to orchestrate workflows across different tools. Below is a demonstration of what's possible: a snake game created by combining Linear, Figma, and browser tools. While real-world projects are typically more complex, this example showcases the potential of these integrated workflows.

[Media](/docs-static/images/guides/tutorials/web-development/snake.mp4)

## Connect to your project management tools

You can integrate Cursor into your existing project management software using different tooling. In this guide, we'll look at integrating Linear with their MCP server.

### Linear Installation

Add the Linear MCP server to `mcp.json`:

```json
{
  "mcpServers": {
    "Linear": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.linear.app/mcp"
      ]
    }
  }
}
```

Then:

1. Make sure to enable Linear from MCP settings
2. Web browser will open and you will be prompted to authorize with Linear

### Using Linear in Cursor

Linear MCP servers expose different tools that Cursor can use to read and manage issues. Go to MCP settings and locate the Linear server to see a list of all tools. To verify, try this prompt in Chat:

```text
list all issues related to this project
```

![linear.png](/docs-static/images/guides/tutorials/web-development/linear.png)

It should return a list of issues if the integration is set up properly.

## Bring in your Figma designs

Designs and mockups are core to web development. Using the official MCP server for Figma, you can directly access and work with design files in Cursor. To get started, follow the set up instructions at [Figma Dev Mode MCP Server](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Dev-Mode-MCP-Server).

### Figma Installation

Add the Figma MCP server to `mcp.json`:

```json
{
  "mcpServers": {
    "Figma": {
      "url": "http://127.0.0.1:3845/sse"
    }
  }
}
```

### Usage

The server exposes multiple tools you can use in your prompts. E.g try to ask for the designs of the current selection in Figma. Read more in the [documentation](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Dev-Mode-MCP-Server).

![figma.png](/docs-static/images/guides/tutorials/web-development/figma.png)

## Keep your code scaffolding consistent

You probably have existing code, a design system, or established conventions you want to reuse. When working with models, it's helpful to reference patterns already in your codebase, such as dropdown menus or other common components.

Working in a large web-based codebase ourselves, we've found that declarative code works especially well, particularly for React and JSX.

If you have a design system, you can help the agent discover it by providing a rule for it. Here's a `ui-components.mdc` file where we try to enforce reuse of components when possible:

```markdown
---
description: Implementing designs and building UI
---
- reuse existing UI components from `/src/components/ui`. these are the primitives we can build with
- create new components by orchestrating ui components if you can't find any existing that solves the problem
- ask the human how they want to proceed when there are missing components and designs
```

As your component library grows, add new rules accordingly. When the rules become too numerous, consider splitting them into more specific categories, such as "only apply when working with user inputs."

![ui-components.png](/docs-static/images/guides/tutorials/web-development/components.png)

## Use Cursor Browser for testing

Cursor Browser is a built-in browser tool that allows Cursor to interact with web applications directly. With Cursor Browser, the agent can navigate pages, fill forms, click elements, inspect console logs, and monitor network requests - all without leaving Cursor.

This tight integration makes it easy to verify changes, debug issues, and iterate on your web application. You can ask Cursor to test your implementation, check for console errors, or even perform multi-step user flows to ensure everything works as expected.

To use Cursor Browser, simply reference the browser in your prompts. For example:

- "Open the app in the browser and check for console errors"
- "Navigate to the login page and test the form submission"
- "Take a screenshot of the current page"

For more details on browser capabilities, security settings, and advanced features, see the [Browser documentation](https://cursor.com/docs/agent/browser.md).

## Takeaways

- Tight feedback loops are essential in web development. Use Cursor alongside tools like Figma, Linear, and the browser to move quickly and stay in flow.
- MCP servers let you integrate external systems directly into Cursor, reducing context switching and improving task execution.
- Reusing components and design systems helps the model produce cleaner, more consistent code and outputs.
- Clear, scoped tasks lead to better results. Be intentional with how you prompt and what you ask for.
- If you're not getting good outputs, try adjusting instructions (use rules, prompts, and give access to more context like MCP servers) or systems (patterns, abstractions, and clarity help the model understand and work more autonomously).
- You can extend the model's context by including runtime info like console logs, network requests, and UI element data.
- Not everything needs to be automated. If your system becomes too complex, fall back to more surgical edits with Tab and Inline Edit.
- Cursor is most powerful when it's a co-pilot, not an autopilot. Use it to improve, not replace, your own decision-making.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/downloads.md
# INDEX: 81/114
================================================================================

# Downloads

## Platform support

Cursor is available for all major operating systems with native installation packages.

### Windows

- Windows 10 and later
- Native installer (.exe)

### macOS

- macOS 10.15 (Catalina) and later
- Native installer (.dmg)
- Apple Silicon and Intel support

### Linux

#### Debian/Ubuntu (recommended)

Install Cursor from the official apt repository. This is the recommended method for Debian, Ubuntu, and other Debian-based distributions.

```bash
# Add Cursor's GPG key
curl -fsSL https://downloads.cursor.com/keys/anysphere.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/cursor.gpg > /dev/null

# Add the Cursor repository
echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/cursor.gpg] https://downloads.cursor.com/aptrepo stable main" | sudo tee /etc/apt/sources.list.d/cursor.list > /dev/null

# Update and install
sudo apt update
sudo apt install cursor
```

This installs Cursor to `/opt/Cursor`, adds a desktop entry, and configures the `cursor` command for terminal use. Updates are handled through your system's package manager.

You can also download the `.deb` file directly from [cursor.com/downloads](https://cursor.com/downloads) and install it with `sudo apt install ./cursor-*.deb`.

#### RHEL/Fedora

Install Cursor from the official yum/dnf repository:

```bash
# Add Cursor's repository
sudo tee /etc/yum.repos.d/cursor.repo << 'EOF'
[cursor]
name=Cursor
baseurl=https://downloads.cursor.com/yumrepo
enabled=1
gpgcheck=1
gpgkey=https://downloads.cursor.com/keys/anysphere.asc
EOF

# Install Cursor
sudo dnf install cursor
```

For older systems using yum instead of dnf, replace `dnf` with `yum`.

You can also download the `.rpm` file directly from [cursor.com/downloads](https://cursor.com/downloads) and install it with `sudo dnf install ./cursor-*.rpm`.

#### AppImage (portable)

AppImage works on any Linux distribution without installation:

1. Download the `.AppImage` file from [cursor.com/downloads](https://cursor.com/downloads)
2. Make it executable and run:

```bash
chmod +x Cursor-*.AppImage
./Cursor-*.AppImage
```

The apt and yum packages are preferred over AppImage. They provide desktop icons, automatic updates through your system's package manager, and CLI tools that AppImage doesn't include.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise.md
# INDEX: 82/114
================================================================================

# Enterprise

Cursor provides enterprise-grade security, compliance, and administrative controls for organizations deploying AI-assisted development at scale.

## Security and compliance resources

For security reviews and compliance assessments, start with these resources:

- [Trust Center](https://trust.cursor.com/) - Security practices, certifications, and compliance information
- [Security page](https://cursor.com/security) - Detailed security architecture and controls
- [Privacy Overview](https://cursor.com/privacy-overview) - Data handling and privacy guarantees
- [Data Processing Agreement](https://cursor.com/terms/dpa) - GDPR-compliant DPA with data protection commitments

Our certifications include SOC2 Type II, and we maintain GDPR compliance. Visit the [Trust Center](https://trust.cursor.com/) for the latest certification documents and third-party assessment reports.

## Enterprise documentation

Learn how to deploy, configure, and manage Cursor for your organization. This documentation covers:

- [Identity & access](https://cursor.com/docs/enterprise/identity-and-access-management.md) - SSO, SCIM, RBAC, and MDM policies
- [Privacy & data governance](https://cursor.com/docs/enterprise/privacy-and-data-governance.md) - Data flows, Privacy Mode, and data residency
- [Network configuration](https://cursor.com/docs/enterprise/network-configuration.md) - Proxy setup, IP allowlisting, and encryption
- [LLM safety & controls](https://cursor.com/docs/enterprise/llm-safety-and-controls.md) - Hooks, terminal sandboxing, and agent controls
- [Models & integrations](https://cursor.com/docs/enterprise/model-and-integration-management.md) - Model controls, MCP, and third-party integrations
- [Spend Limits](https://cursor.com/docs/account/billing/spend-limits.md) - Configure spending limits to control costs
- [Compliance & monitoring](https://cursor.com/docs/enterprise/compliance-and-monitoring.md) - Audit logs and tracking
- [Deployment patterns](https://cursor.com/docs/enterprise/deployment-patterns.md) - MDM-managed editor vs self-hosted CLI

## Key features

### Identity and access

- [SSO and SAML](https://cursor.com/docs/account/teams/sso.md) - Single sign-on for streamlined authentication
- [SCIM](https://cursor.com/docs/account/teams/scim.md) - Automated user provisioning and deprovisioning
- [MDM policies](https://cursor.com/docs/enterprise/identity-and-access-management.md#mdm-policies) - Enforce allowed team IDs and extensions on user devices

### Privacy and security

- [Privacy Mode](https://cursor.com/privacy-overview) - Zero data retention with AI providers
- [Agent Security](https://cursor.com/docs/agent/security.md) - Guardrails for agent tool execution
- [Hooks](https://cursor.com/docs/agent/hooks.md) - Custom security and compliance workflows

### Administrative controls

- [Dashboard](https://cursor.com/docs/account/teams/dashboard.md) - Team management, settings, and monitoring
- [Admin API](https://cursor.com/docs/account/teams/admin-api.md) - Programmatic access to admin features
- [Analytics](https://cursor.com/docs/account/teams/analytics.md) - Usage metrics and insights
- [Conversation Insights](https://cursor.com/docs/account/teams/analytics.md#conversation-insights) - Understand the type of work being done with Cursor (Enterprise only)
- [AI Code Tracking API](https://cursor.com/docs/account/teams/ai-code-tracking-api.md) - Per-commit AI usage metrics (Enterprise only)
- [Cursor Blame](https://cursor.com/docs/integrations/cursor-blame.md) - AI-aware git blame that shows AI vs human code attribution (Enterprise only)
- [Analytics API](https://cursor.com/docs/account/teams/analytics-api.md) - Usage metrics and insights
- [Billing Groups](https://cursor.com/docs/account/enterprise/billing-groups.md) - Manage spend across groups of users for reporting and chargebacks (Enterprise only)
- [Service Accounts](https://cursor.com/docs/account/enterprise/service-accounts.md) - Non-human accounts for automated workflows (Enterprise only)

### Models and integrations

- [Models](https://cursor.com/docs/models.md) - Available models and configuration
- [MCP](https://cursor.com/docs/context/mcp.md) - Model Context Protocol server trust management
- [Slack](https://cursor.com/docs/integrations/slack.md) - Cloud Agents in Slack
- [GitHub](https://cursor.com/docs/integrations/github.md) - Repository integration
- [Linear](https://cursor.com/docs/integrations/linear.md) - Issue tracking integration
- [Bugbot](https://cursor.com/docs/bugbot.md) - Automated bug detection and fixing

### Monitoring and compliance

- Audit logs - Track authentication, user management, and administrative actions (Enterprise only)
- SIEM integration - Stream audit logs to your security tools

## Getting started

1. Review the [Trust Center](https://trust.cursor.com/) and [Security page](https://cursor.com/security) for your security assessment
2. Read through the [enterprise documentation](https://cursor.com/docs/enterprise.md) to understand deployment options
3. Set up [SSO](https://cursor.com/docs/account/teams/sso.md) and [SCIM](https://cursor.com/docs/account/teams/scim.md) for user management
4. Deploy Cursor and configure [MDM policies](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) to enforce team IDs and extensions
5. Review the [Dashboard](https://cursor.com/docs/account/teams/dashboard.md) to monitor team usage

## Plan Comparison

### Team Admin & Billing

| Capability                                                                                                          | Individual Plans | Teams                                                                     | Enterprise                                                                                                                                                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Centralized Billing                                                                                                 |                  | ✓                                                                         | ✓                                                                                                                                                                                                                                                                 |
| Usage Spend Controls                                                                                                | Personal limits  | Team limits                                                               | [Pooled usage + admin-only controls](https://cursor.com/docs/account/billing/spend-limits.md#enterprise)                                                                                                                                                          |
| [Billing Groups](https://cursor.com/docs/account/enterprise/billing-groups.md)                                      |                  |                                                                           | ✓                                                                                                                                                                                                                                                                 |
| [Team Usage Analytics](https://cursor.com/docs/account/teams/analytics.md#analytics)                                |                  | [Analytics Dashboard](https://cursor.com/docs/account/teams/analytics.md) | [Analytics Dashboard](https://cursor.com/docs/account/teams/analytics.md),[AI Code Tracking API](https://cursor.com/docs/account/teams/ai-code-tracking-api.md),[Conversation Insights](https://cursor.com/docs/account/teams/analytics.md#conversation-insights) |
| [Cursor Blame](https://cursor.com/docs/integrations/cursor-blame.md)                                                |                  |                                                                           | ✓                                                                                                                                                                                                                                                                 |
| [SSO (SAML/OIDC)](https://cursor.com/docs/enterprise/identity-and-access-management.md#single-sign-on-sso-and-saml) |                  | ✓                                                                         | ✓                                                                                                                                                                                                                                                                 |
| [SCIM Provisioning](https://cursor.com/docs/account/teams/scim.md)                                                  |                  |                                                                           | ✓                                                                                                                                                                                                                                                                 |
| [Audit Logs](https://cursor.com/docs/enterprise/compliance-and-monitoring.md#audit-logs)                            |                  |                                                                           | ✓                                                                                                                                                                                                                                                                 |
| [Service Accounts](https://cursor.com/docs/account/enterprise/service-accounts.md)                                  |                  |                                                                           | ✓                                                                                                                                                                                                                                                                 |

### Centralized Agent Controls

| Capability                                                                                                              | Individual Plans | Teams                  | Enterprise                                                                                 |
| ----------------------------------------------------------------------------------------------------------------------- | ---------------- | ---------------------- | ------------------------------------------------------------------------------------------ |
| [Privacy Mode](https://cursor.com/docs/enterprise/privacy-and-data-governance.md#privacy-mode-enforcement)              | User choice      | Enforce org-wide       | Enforce org-wide                                                                           |
| [Team Rules](https://cursor.com/docs/context/rules.md#team-rules)                                                       |                  | Enforceable + Optional | Enforceable + Optional                                                                     |
| [Hooks for Logging,Auditing, and more](https://cursor.com/docs/agent/hooks.md#hooks)                                    | ✓                | MDM Distribution       | [MDM & Server-side distribution](https://cursor.com/docs/agent/hooks.md#team-distribution) |
| [Agent Sandbox Mode](https://cursor.com/docs/agent/terminal.md#sandbox)                                                 | ✓                | ✓                      | Enforce org-wide                                                                           |
| [Repository Blocklist](https://cursor.com/docs/enterprise/model-and-integration-management.md#git-repository-blocklist) |                  |                        | ✓                                                                                          |
| [Model Access Restrictions](https://cursor.com/docs/enterprise/model-and-integration-management.md)                     |                  |                        | ✓                                                                                          |
| [Auto-run, Browser, and Network Controls](https://cursor.com/docs/enterprise/llm-safety-and-controls.md)                |                  |                        | ✓                                                                                          |

### User Access Controls

| Capability   | Individual & Teams Plans | Enterprise                                     |
| ------------ | ------------------------ | ---------------------------------------------- |
| Cursor CLI   |                          | Restrict which users can access agents via CLI |
| Cloud Agents |                          | Restrict which users can create Cloud Agents   |
| Analytics    |                          | Restrict analytics dashboard to admins only    |
| BYOK         |                          | Disable users from using their own API keys    |

### Support & Legal

| Capability        | Individual Plans                                          | Teams                                                     | Enterprise                                |
| ----------------- | --------------------------------------------------------- | --------------------------------------------------------- | ----------------------------------------- |
| Technical Support | [Community & Standard Support](https://forum.cursor.com/) | [Community & Standard Support](https://forum.cursor.com/) | Priority Support                          |
| Terms             | [Online Terms](https://cursor.com/terms-of-service)       | [MSA & DPA](https://cursor.com/terms/msa)                 | [MSA & DPA](https://cursor.com/terms/msa) |

For security vulnerabilities, see our [responsible disclosure program](https://cursor.com/docs/agent/security.md#responsible-disclosure).

### Ready to deploy Cursor at scale?

Contact our team to discuss your organization's needs.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/compliance-and-monitoring.md
# INDEX: 83/114
================================================================================

# Compliance and Monitoring

Compliance requires visibility into who did what, when, and why. This documentation covers audit logs, AI code tracking, certifications, and how to meet regulatory requirements.

## Audit logs

Audit logs provide a record of security events and administrative actions. Available on the [Enterprise plan](https://cursor.com/contact-sales?source=docs-audit-logs), audit logs help you meet compliance requirements and investigate security incidents.

We log the following events:

- **Authentication events:** Logins and logouts
- **User management:** User additions (via SSO, invite, signup, team creation, or auto-enrollment), removals, role changes, and individual spend limits
- **API key management:** Team and user API key creation and revocation
- **Team settings:** Team-wide and per-user spending limits, admin settings, team name changes, Slack integration settings, and repository mappings
- **Repository management:** Repository creation, deletion, and settings updates
- **Directory groups:** Directory group creation, updates, deletion, membership changes, and permission modifications
- **Privacy settings:** Privacy Mode changes at user or team level
- **Team rules:** Team rule management (including Bugbot rules) for custom workflows
- **Team commands:** Custom command creation, updates, and deletion

We do not log agent responses or generated code content.

Instead, we recommend using [hooks](https://cursor.com/docs/agent/hooks.md) to log prompts and code.

### Accessing audit logs

View audit logs in the [team dashboard](https://cursor.com/dashboard?tab=audit-log). This is available on Enterprise plans, and requires admin access.

### Streaming audit logs

For compliance and security monitoring, stream audit logs to your existing systems:

- SIEM systems (Splunk, Sumo Logic, Datadog, etc.)
- Webhook endpoints for custom processing
- S3 buckets for long-term retention
- Log aggregators like Elasticsearch or CloudWatch

Please contact [hi@cursor.com](mailto:hi@cursor.com) if you would like to receive streaming audit logs.

### Log format

Audit logs are delivered as JSON and include metadata and event-specific fields:

```json
{
  "metadata": {
    "timestamp": "2024-10-14T18:30:45Z",
    "event_id": "evt_abc123xyz789"
  },
  "team_id": "team_xyz789",
  "ip_address": "203.0.113.42",
  "user_email": "alice@company.com",
  "event": { /* event-specific fields */ }
}
```

The event types include:

- `login` - User login events (web or app)
- `logout` - User logout events
- `add_user` - User additions (with source: `sso`, `invite`, `signup`, `createTeam`, or `autoEnroll`)
- `remove_user` - User removals from team
- `update_user_role` - Role changes (OWNER, ADMIN, MEMBER)
- `user_spend_limit` - Individual user spending limit changes
- `team_api_key` - Team API key actions (create, revoke)
- `user_api_key` - User API key actions (create, revoke)
- `team_settings` - Team setting modifications, including:
- `team_hard_limit_dollars` - Team-wide spending hard limit
- `team_hard_limit_per_user_dollars` - Per-user hard limit
- `per_user_monthly_limit_dollars` - Monthly spending limits per user
- `admin_only_usage_pricing` - Admin-only usage pricing settings
- `team_admin_settings` - General admin settings
- `team_name` - Team name changes
- `slack_default_repo` - Slack integration repository settings
- `slack_default_branch` - Slack integration branch settings
- `slack_default_model` - Slack integration model settings
- `slack_share_summary` - Slack summary sharing settings
- `slack_share_summary_in_external_channel` - External channel sharing
- `slack_channel_repo_mappings` - Slack channel to repository mappings
- `team_repo` - Repository actions (create, delete, update\_settings)
- `create_directory_group` - Directory group creation
- `update_directory_group` - Directory group updates
- `update_directory_group_permissions` - Directory group permission changes
- `delete_directory_group` - Directory group deletion
- `add_user_to_directory_group` - Adding users to directory groups
- `remove_user_from_directory_group` - Removing users from directory groups
- `privacy_mode` - Privacy Mode changes (scope: "user" or "team")
- `team_rule` - Team rule management (create, update, delete)
- `bugbot_team_rule` - Bugbot-specific rule management (create, update, delete)
- `team_command` - Custom team command management (create, update, delete)

### Searching and filtering

Filter audit logs in the dashboard by:

- Date range
- Event type (authentication, user management, settings)
- Actor (specific user)

Export filtered results to CSV for analysis or compliance reports.

## Using hooks for compliance logging

Audit logs track administrative actions, but some compliance requirements need logging of development activity. Use hooks to log:

### Prompts submitted hook

```bash
#!/bin/bash
input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt')
user_id=$(echo "$input" | jq -r '.user_id')

# Log to your compliance system
curl -X POST "https://compliance.company.com/log" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"prompt\",\"user\":\"$user_id\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

cat << EOF
{
  "continue": true
}
EOF
```

### Code generated hook

```bash
#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | jq -r '.file_path')
edits=$(echo "$input" | jq -r '.edits')

# Log the code generation event (not the actual code)
curl -X POST "https://compliance.company.com/log" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"generation\",\"file\":\"$file_path\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

exit 0
```

**Important:** Be careful logging actual code or prompts. They may contain sensitive information. Log metadata (who, when, what file) rather than content when possible.

See [Hooks](https://cursor.com/docs/agent/hooks.md) for hook implementation details.

## Certifications and compliance

Cursor maintains compliance with industry standards, including SOC 2 Type II, GDPR, and more.

Access compliance documentation through the [Trust Center](https://trust.cursor.com/) including:

- SOC 2 reports
- Penetration test summaries
- Security architecture documentation
- Data flow diagrams

## Responsible disclosure

If you discover a security vulnerability in Cursor, report it through our responsible disclosure program:

Email [security-reports@cursor.com](mailto:security-reports@cursor.com) with the following information:

1. A detailed description of the vulnerability
2. Steps to reproduce the issue
3. Any relevant screenshots or proof of concept

### Audit logs are available on the Enterprise plan

Contact our team to learn more about compliance features.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/deployment-patterns.md
# INDEX: 84/114
================================================================================

# Deployment Patterns

This guide covers how to deploy the Cursor editor and CLI tools to developer machines in your organization. Most organizations deploy both the editor (for daily development work) and the CLI (for automation, CI/CD, and scripting).

For other deployment options like SCM integrations (bugbot, BGA apps) or web-based access, see the relevant integration documentation.

## Editor deployment with MDM

Deploy the Cursor editor and agent to user workstations and enforce policies through Mobile Device Management (MDM) systems.

### How it works

1. Your IT team packages the Cursor application for deployment
2. Push to user machines via MDM (Jamf, Intune, etc.)
3. Users receive Cursor on their primary development machines

MDM allows you to enforce policies for Cursor, such as allowed team IDs and extensions.

You can also enforce settings like workspace trust, and control auto-updates and deployment of new versions.

### MDM Configuration

You can centrally manage specific features of Cursor through device management solutions to ensure it meets the needs of your organization. When you specify a Cursor policy, its value overrides the corresponding Cursor setting on users' devices.

Cursor supports policies on Windows (Group Policy), macOS (configuration profiles), and Linux (JSON policy files, version 2.0+).

Cursor currently provides policies to control the following admin-controlled features:

| Policy                     | Description                                                                                                | Cursor setting                     |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| AllowedExtensions          | Controls which extensions can be installed.                                                                | `extensions.allowed`               |
| AllowedTeamId              | Controls which team IDs are allowed to log in. Users with unauthorized team IDs are forcefully logged out. | `cursorAuth.allowedTeamId`         |
| ExtensionGalleryServiceUrl | Configures a custom extension marketplace URL.                                                             | `extensions.gallery.serviceUrl`    |
| NetworkDisableHttp2        | Disables HTTP/2 for all requests, using HTTP/1.1 instead.                                                  | `cursor.general.disableHttp2`      |
| UpdateMode                 | Controls automatic update behavior. Set to 'none' to disable updates.                                      | `update.mode`                      |
| WorkspaceTrustEnabled      | Controls whether Workspace Trust is enabled.                                                               | `security.workspace.trust.enabled` |

#### Windows Group Policy

Cursor has support for Windows Registry-based Group Policy. When policy definitions are installed, admins can use the Local Group Policy Editor to manage the policy values.

To add a policy:

1. Copy the Policy ADMX and ADML files from `AppData\Local\Programs\cursor\policies`.
2. Paste the ADMX file into the `C:\Windows\PolicyDefinitions` directory, and the ADML file into the `C:\Windows\PolicyDefinitions\<your-locale>\` directory.
3. Restart the Local Group Policy Editor.
4. Set the appropriate policy values (e.g. `{"anysphere": true, "github": true}` for the `AllowedExtensions` policy) in the Local Group Policy Editor.

Policies can be set both at the Computer level and the User level. If both are set, Computer level will take precedence.

**Important:** When a policy value is set, it overrides the Cursor setting value configured at any level (default, user, workspace, etc.). This is a global override that prevents users from changing these settings.

In Cursor 2.1, we renamed the category name to Cursor in the Group Policy Editor. Old keys still work. We recommend using the current ADMX policy file.

#### Windows Installer

The Windows installer is based on Inno Setup. To install Cursor fully in the background without user interaction, use the following command-line flags:

**For fresh installations:**

```cmd
CursorSetup-x64-2.0.exe /SILENT /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /LOG=install.log
```

**For updating existing installations:**

When updating an existing Cursor installation, you must use different flags that include the `/update` parameter pointing to a flag file. The flag file is an empty file that signals to the installer this is an update operation.

Create a temporary flag file and pass its path to the installer:

```cmd
CursorSetup-x64-2.0.exe /VERYSILENT /update="%TEMP%\cursor-update.flag" /CLOSEAPPLICATIONS /LOG=update.log
```

**Note:** Installers pre-2.0 may incorrectly not respect `/SILENT` flags. Future installers (version 2.0 and later) will ensure that silent installs work correctly.

#### macOS Configuration Profiles

Configuration profiles manage settings on macOS devices. A profile is an XML file with key/value pairs that correspond to available policy. These profiles can be deployed using Mobile Device Management (MDM) solutions like Jamf, Kandji, or Microsoft Intune, or installed manually.

**Bundle ID per channel:**

The `PayloadType` in your configuration profile must match the Cursor bundle ID for your channel:

| Channel    | Bundle ID                     |
| ---------- | ----------------------------- |
| Production | com.todesktop.230313mzl4w4u92 |
| Nightly    | co.anysphere.cursor.nightly   |

For most enterprise deployments, use the production bundle ID: `com.todesktop.230313mzl4w4u92`.

### Example .mobileconfig file

An example `.mobileconfig` file for macOS is shown below:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
	<dict>
		<key>PayloadContent</key>
		<array>
			<dict>
				<key>PayloadDisplayName</key>
				<string>Cursor</string>
				<key>PayloadIdentifier</key>
				<string>com.todesktop.230313mzl4w4u92.J6B5723A-6539-4F31-8A4E-3CC96E51F48C</string>
				<key>PayloadType</key>
				<string>com.todesktop.230313mzl4w4u92</string>
				<key>PayloadUUID</key>
				<string>J6B5723A-6539-4F31-8A4E-3CC96E51F48C</string>
				<key>PayloadVersion</key>
				<integer>1</integer>
				<key>AllowedExtensions</key>
				<string>{"anysphere":true}</string>
				<key>AllowedTeamId</key>
				<string>1,2</string>
				<key>ExtensionGalleryServiceUrl</key>
				<string>https://marketplace.example.com</string>
				<key>NetworkDisableHttp2</key>
				<true/>
				<key>UpdateMode</key>
				<string>none</string>
				<key>WorkspaceTrustEnabled</key>
				<true/>
			</dict>
		</array>
		<key>PayloadDescription</key>
		<string>This profile manages Cursor.</string>
		<key>PayloadDisplayName</key>
		<string>Cursor</string>
		<key>PayloadIdentifier</key>
		<string>com.todesktop.230313mzl4w4u92</string>
		<key>PayloadOrganization</key>
		<string>Anysphere</string>
		<key>PayloadType</key>
		<string>Configuration</string>
		<key>PayloadUUID</key>
		<string>F2C1A7B3-9D4E-4B2C-8E1F-7A6C5D4B3E2F</string>
		<key>PayloadVersion</key>
		<integer>1</integer>
		<key>TargetDeviceType</key>
		<integer>5</integer>
	</dict>
</plist>
```

##### String policies

The example below demonstrates configuration of the `AllowedExtensions` policy. The policy value starts empty in the sample file (no extensions are allowed).

```bash
<key>AllowedExtensions</key>
<string></string>
```

Add the appropriate JSON string defining your policy between the `<string>` tags.

```bash
<key>AllowedExtensions</key>
<string>{"anysphere": true, "github": true}</string>
```

**Extension control semantics:**

The `AllowedExtensions` policy accepts a JSON object where:

- Keys can be publisher names (e.g., `"github"`) or full extension IDs (e.g., `"ms-azuretools.vscode-docker"`)
- Values are booleans indicating whether extensions from that publisher or specific extension are allowed
- If a publisher is set to `true`, all extensions from that publisher are allowed
- Specific extension IDs take precedence over publisher rules

For the `AllowedTeamId` policy, add the comma-separated list of team IDs:

```bash
<key>AllowedTeamId</key>
<string>1,3,7</string>
```

For the `NetworkDisableHttp2` policy, use a boolean value to disable HTTP/2:

```bash
<key>NetworkDisableHttp2</key>
<true/>
```

##### Boolean policies

For boolean policies like `WorkspaceTrustEnabled`, use `<true/>` or `<false/>` tags:

```bash
<key>WorkspaceTrustEnabled</key>
<false/>
```

Or to enable the feature:

```bash
<key>WorkspaceTrustEnabled</key>
<true/>
```

##### UpdateMode policy

The `UpdateMode` policy controls how Cursor handles automatic updates. This is useful for organizations that want to control when and how updates are deployed.

Available values:

- `none` - Disables all automatic updates
- `manual` - Users can manually check for updates
- `start` - Check for updates when Cursor starts
- `default` - Default behavior (same as `start`)
- `silentlyApplyOnQuit` - Download updates in the background and apply when Cursor quits

To disable automatic updates:

```bash
<key>UpdateMode</key>
<string>none</string>
```

##### WorkspaceTrustEnabled policy

The `WorkspaceTrustEnabled` policy controls whether [Workspace Trust](https://code.visualstudio.com/docs/editing/workspaces/workspace-trust) is enabled. When enabled, Cursor prompts users to choose between normal or restricted mode for new workspaces.

Use a boolean value:

```bash
<key>WorkspaceTrustEnabled</key>
<true/>
```

##### ExtensionGalleryServiceUrl policy

The `ExtensionGalleryServiceUrl` policy configures the extension marketplace URL. This is useful for organizations that want to use a custom extension marketplace or mirror.

Set the URL as a string value:

```bash
<key>ExtensionGalleryServiceUrl</key>
<string>https://marketplace.example.com</string>
```

##### Deploying with MDM solutions

The `.mobileconfig` file can be uploaded directly to your MDM solution:

- **Jamf**: Upload as a custom configuration profile
- **Kandji**: Add as a custom profile in Library
- **Microsoft Intune**: Deploy as a custom profile with the correct payload domain

Ensure the `PayloadType` matches your Cursor channel's bundle ID.

##### Reference configuration file

A complete example configuration profile is included with Cursor at:

```bash
# Production channel
/Applications/Cursor.app/Contents/Resources/app/policies/com.todesktop.230313mzl4w4u92.mobileconfig

# Nightly channel
/Applications/Cursor Nightly.app/Contents/Resources/app/policies/co.anysphere.cursor.nightly.mobileconfig
```

The file path varies by channel. Use the appropriate path for your Cursor installation.

**Important security considerations:**

- The provided `.mobileconfig` file initializes **all** policies available in that version of Cursor
- Delete any policies that are not needed to avoid unintentionally restrictive defaults
- If you do not edit or remove a policy from the sample, that policy will be enforced with its default value
- Policy values override all user and workspace settings globally

Manually install a configuration profile by double-clicking on the `.mobileconfig` profile in Finder and then enabling it in System Preferences under **General** > **Device Management**. Removing the profile from System Preferences will remove the policies from Cursor.

For more information on configuration profiles, refer to Apple's documentation.

#### Linux Policy File

Linux distributions don't have a standardized enterprise policy system like Windows Registry or macOS configuration profiles. Cursor reads policies from a JSON file to provide equivalent functionality.

**Note:** Linux policy file support is available in Cursor version 2.0 and later.

The policy file is located at `~/.cursor/policy.json`.

##### Creating a policy file

Create a JSON file at the location above with policy names as keys and their values. All policies are optional?include only the policies you want to enforce.

### Example policy.json file

```json
{
  "AllowedExtensions": "{\"anysphere\": true, \"github\": true}",
  "AllowedTeamId": "1,3,7",
  "WorkspaceTrustEnabled": true
}
```

##### Policy format

Each policy in the JSON file maps to a policy name:

- **AllowedExtensions**: A JSON string defining allowed extension publishers
  ```json
  "AllowedExtensions": "{\"anysphere\": true, \"github\": true}"
  ```

- **AllowedTeamId**: A comma-separated string of team IDs
  ```json
  "AllowedTeamId": "1,3,7"
  ```

- **WorkspaceTrustEnabled**: A boolean controlling workspace trust
  ```json
  "WorkspaceTrustEnabled": true
  ```

**Note:** The `AllowedExtensions` value must be a JSON string (escaped quotes), not a JSON object. This matches the format used on Windows and macOS.

##### Deploying policies

Deploy the policy file using your organization's configuration management tools:

- Ansible, Puppet, or Chef for automated deployment
- NFS or shared network storage for centralized policy files
- Package managers with post-install scripts
- Container base images for containerized environments

Changes to the policy file take effect when Cursor restarts. The file is monitored for changes, so updates propagate automatically to running instances.

If the policy file doesn't exist, Cursor runs without policy restrictions.

### Automatic updates for non-admin users

Due to Electron framework limitations, Cursor updates require administrator privileges on macOS.

**Recommended approaches:**

- **MDM deployment**: Use MDM tools (Jamf, Kandji, Intune) to deploy updates centrally with appropriate privileges
- **Automated deployment tools**: Consider tools like [Installomator](https://github.com/Installomator/Installomator) for scripted updates
- **Disable update prompts**: Set the `UpdateMode` policy to `none` to prevent users from seeing failed update notifications

For organizations with non-admin users, the most reliable approach is to manage Cursor updates through your existing software deployment pipeline and disable automatic updates via MDM policy.

## CLI deployment

Run Cursor agents as a headless CLI tool on your infrastructure.

### How it works

1. Deploy the CLI to your environment (on-prem, corporate cloud, Kubernetes clusters, CI/CD systems)
2. The CLI is scripted or run in the background or as part of CI
3. The CLI can access whatever the user can access from their machine (VPN, internal APIs, private package registries, etc.)

### Installation and setup

Install the Cursor CLI:

```bash
# Install Cursor CLI (macOS, Linux, WSL)
curl https://cursor.com/install -fsS | bash

# Install Cursor CLI (Windows PowerShell)
irm 'https://cursor.com/install?win32=true' | iex

# Set API key for scripts
export CURSOR_API_KEY=your_api_key_here
agent -p "Analyze this code"
```

See [CLI headless mode documentation](https://cursor.com/docs/cli/headless.md) for full details.

### GitHub Actions integration

Cursor CLI works in GitHub Actions and other CI systems.

See [GitHub Actions integration](https://cursor.com/docs/cli/github-actions.md) for examples.

## Cursor CLI considerations

Whether running in the desktop app or as a standalone CLI, Cursor agents have the same security controls:

**Same features:**

- Privacy Mode applies equally
- Hooks work for both the desktop app and CLI
- Same model access controls
- Same audit logging
- Same usage tracking

**Same requirements:**

- Both need network access to Cursor services
- Both send code to LLMs (with Privacy Mode protections)
- Both require appropriate authentication

The CLI is the same agent with a different interface.

## Network considerations

User machines need access to the following endpoints. Configure firewall and proxy rules accordingly:

- `*.cursor.sh` - Backend services and API endpoints
- `cursor-cdn.com` - Application downloads and updates
- `marketplace.cursorapi.com` - Extension marketplace
- Third-party AI provider endpoints (OpenAI, Anthropic, Google, etc.)

When using the `UpdateMode` policy set to `none`, you can restrict access to update endpoints while maintaining access to other services.

The Cursor editor inherits the machine's network configuration, including VPN access, internal service endpoints, and private package registries.

This means agents running in the editor can access whatever the user can access from their machine.

See [Network Configuration](https://cursor.com/docs/enterprise/network-configuration.md) for detailed firewall and proxy requirements.

## Minimum Versions

We recommend users stay within one version of our most recent release. Users three or more versions behind our current release will start to see a warning indicating that they need to upgrade. Users four or more versions behind our latest release will see an error forcing them to update. This allows users to experience our latest features, while also staying up to date with our latest performance improvements, stability updates and bug fixes.

For example, if the latest release is 1.7, we recommend all users to be on version 1.6 or 1.7. Users on 1.4 or below will see a warning telling them to update. Users on 1.3 or below will see an error forcing them to update.

When managing Cursor deployments for your organization, we recommend updating your Cursor version regularly.

## Troubleshooting

- Proxy configuration problems (see [Network Configuration](https://cursor.com/docs/enterprise/network-configuration.md))
- Model access issues (check [Model and Integration Management](https://cursor.com/docs/enterprise/model-and-integration-management.md) or your [team dashboard](https://cursor.com/docs/account/teams/dashboard.md))
- Spending limit reached (see [Spend Limits](https://cursor.com/docs/account/billing/spend-limits.md))

## Frequently asked questions

### Does Cursor support policies on Linux?

Yes, starting with version 2.0. Linux uses a file-based policy system at `~/.cursor/policy.json`. See the "Linux Policy File" section above for details on the format and deployment.

### Can I use environment variables in the policy file?

No. The policy file must be a valid JSON file with static values. Use your configuration management tools to generate the file dynamically if needed.

### What happens if the policy file has invalid JSON?

Cursor logs an error and runs without policy restrictions. Check the main process logs for parsing errors.

### What is my team ID?

You can find your team ID by clicking on your team name from [https://cursor.com/dashboard](https://cursor.com/dashboard).

### Need help deploying Cursor at scale?

Contact our team for MDM deployment guidance and priority support.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/identity-and-access-management.md
# INDEX: 85/114
================================================================================

# Identity and Access Management

Identity and access management controls who can use Cursor in your organization and what they can do. You'll set up authentication, automate user provisioning, and enforce policies through device management.

We recommend implementing identity controls in this order:

1. **Set up SSO**: Get centralized authentication working first
2. **Enable SCIM**: Automate user lifecycle management
3. **Deploy MDM policies**: Enforce allowed team IDs and extensions
4. **Assign roles**: Grant admin access to the right people

## Single Sign-On (SSO) and SAML

SSO lets your users authenticate to Cursor using your existing identity provider. Instead of creating separate Cursor passwords, users log in with their corporate credentials.

Cursor supports SAML 2.0 integration with providers like Okta, Azure AD, Google Workspace, and OneLogin. When you enable SSO, you can require it for all team members, preventing password-based authentication entirely.

See [SSO and SAML setup](https://cursor.com/docs/account/teams/sso.md) for detailed configuration instructions.

## SCIM provisioning

SCIM 2.0 provisioning automatically manages your team members and directory groups through your identity provider. Available on Enterprise plans with SSO enabled.

Without SCIM, you need to manually add users to your Cursor team and remove them when they leave. With SCIM:

- New employees get Cursor access automatically when added to the right group
- Departing employees lose access when removed from your IDP
- Group membership changes propagate automatically

See [SCIM provisioning](https://cursor.com/docs/account/teams/scim.md) for setup instructions.

## Role-Based Access Control (RBAC)

Cursor teams have three roles: Members, Admins, and Unpaid Admins.

See [Members & Roles](https://cursor.com/docs/account/teams/members.md) for more information.

## MDM policies

Mobile Device Management (MDM) systems let you enforce policies on user devices. Cursor supports MDM-based policies on macOS and Intune / Group Policy on Windows to ensure users comply with organizational requirements.

See [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for platform-specific MDM configuration instructions.

### Allowed Team IDs

The most important MDM policy prevents users from logging into personal Cursor accounts on corporate devices.

When you set an allowed team ID policy, Cursor only permits authentication to those specific team IDs. If a user tries to log in with a different team ID (like a personal account), Cursor logs them out immediately.

For example, if your employees have corporate laptops, you can set the allowed team ID to your enterprise team ID. This prevents them from accidentally using personal accounts that might not have Privacy Mode enabled.

The `cursorAuth.allowedTeamId` Cursor setting controls which team IDs are permitted to log into Cursor. This setting accepts a comma-separated list of team IDs that are authorized for access.

For example, setting `cursorAuth.allowedTeamId` to `"1,3,7"` allows users from those specific team IDs to log in.

When a user attempts to log in with a team ID that is not in the allowed list:

- They are forcefully logged out immediately
- An error message is displayed
- The application prevents further authentication attempts until a valid team ID is used

To centrally manage allowed team IDs for your organization, configure the `AllowedTeamId` policy using your device management solution. This policy overrides the `cursorAuth.allowedTeamId` setting on users' devices. The value of this policy is a string containing the comma-separated list of authorized team IDs.

See [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for platform-specific MDM configuration instructions.

### Allowed Extensions

Control which extensions users can install in Cursor. Extensions can access your workspace, so you want to ensure only trusted extensions run.

**How it works:**

The `extensions.allowed` Cursor setting controls which extensions can be installed. This setting accepts a JSON object where keys are publisher names and values are booleans indicating whether extensions from that publisher are allowed.

For example, setting `extensions.allowed` to `{"anysphere": true, "github": true}` allows extensions from Anysphere and GitHub publishers, while setting it to `{"anysphere": false}` blocks Anysphere extensions.

You can be more specific by including the full extension ID:

```json
{
  "anysphere": true,
  "github": true,
  "esbenp.prettier-vscode": true,
  "ms-azuretools.vscode-containers": false,
  "dbaeumer.vscode-eslint": ["3.0.0"],
  "github.vscode-pull-request-github": "stable"
}
```

**Admin Portal Configuration:**

Team admins can configure allowed extensions through the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) in the Security & Identity section. The configuration is applied automatically to all team members' Cursor clients. Leave the field empty to allow all extensions.

> **Note:** Admin portal configuration for this feature requires Cursor client version 2.1 or later. Users on older versions will not have extension restrictions applied.

**MDM Configuration:**

To centrally manage allowed extensions using device management, configure the `AllowedExtensions` policy. This policy overrides both the admin portal setting and user-configured `extensions.allowed` settings. The value of this policy is a JSON string that defines the allowed extensions.

To centrally manage allowed extensions for your organization, configure the `AllowedExtensions` policy using your device management solution. This policy overrides the `extensions.allowed` setting on users' devices. The value of this policy is a JSON string that defines the allowed publishers.

See [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for platform-specific MDM configuration instructions.

### The .cursor folder

When you open a project in Cursor, the editor creates a `.cursor` folder at the root of your repository. This folder contains:

- Project-specific settings
- Indexing cache
- Project rules and context

This folder can be checked into source control. Your team members benefit from shared rules and settings, but be aware that these configurations are visible to anyone with repository access.

For repositories you don't control access to, review the `.cursor` folder contents before committing. Don't put sensitive information in rules files.

You can also manage rules and commands through the server on the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md).

### Workspace Trust

The `security.workspace.trust.enabled` Cursor setting controls whether the Workspace Trust feature is enabled. This setting accepts a boolean value that determines if users will be prompted to trust workspaces before full functionality is enabled.

For example, setting `security.workspace.trust.enabled` to `true` enables workspace trust prompts, while setting it to `false` disables the feature entirely (all workspaces are automatically trusted).

When workspace trust is enabled:

- Users are prompted to trust each new workspace when opening it for the first time
- Untrusted workspaces run in a restricted mode with limited functionality
- Trust decisions are saved and remembered for each workspace

To centrally manage workspace trust for your organization, configure the `WorkspaceTrustEnabled` policy using your device management solution. This policy overrides the `security.workspace.trust.enabled` setting on users' devices. The value of this policy is a boolean (`true` or `false`).

See [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for platform-specific MDM configuration instructions.

### Advanced identity controls are available on Enterprise

Contact our team to learn about SCIM, MDM policies, and more.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/llm-safety-and-controls.md
# INDEX: 86/114
================================================================================

# LLM Safety and Controls

AI models can behave unexpectedly. This documentation covers how to control what agents can do, set up safety guardrails, and guide LLM behavior toward desired outcomes.

## Understanding model behavior

LLMs generate text based on probability distributions, not by retrieving facts from a database or executing deterministic logic. They can produce different outputs for the same input, hallucinate facts or code that seems plausible but is wrong, and be influenced by carefully crafted prompts (prompt injection).

You can't rely on LLMs to always make safe decisions. Instead, you combine two approaches: **security controls** that enforce hard boundaries on what agents can do, and **steering mechanisms** that guide LLM behavior toward better outcomes.

For a deeper understanding of how LLMs work, see [How AI Models Work](https://cursor.com/learn/how-ai-models-work.md).

## Two approaches to safety

Cursor provides two complementary approaches to managing AI agent behavior:

**Security controls (deterministic enforcement)**: Hard boundaries that block dangerous operations regardless of what the LLM suggests. These include terminal command restrictions, enforcement hooks that reject operations, approval workflows, and sandboxing. Security controls are your primary defense against harmful agent actions.

**LLM steering (non-deterministic guidance)**: Mechanisms that guide the LLM toward better behavior by shaping its context and available actions. These include Rules that add instructions to prompts, Commands that provide reusable workflows, and integrations that enrich the agent's knowledge. Steering improves agent quality but doesn't guarantee prevention of harmful actions.

Use both approaches together. Security controls provide the safety net. Steering reduces how often agents attempt problematic actions in the first place.

## Security controls

These deterministic controls enforce hard boundaries on what agents can do. They work regardless of what the LLM suggests.

### Terminal command restrictions

By default, Cursor requires your approval before executing any terminal command. This protects against destructive commands (deleting files, dropping databases), commands that expose sensitive data, and commands with unintended side effects.

When an agent wants to run a command, you see a prompt showing the full command. You can approve and run it, deny it, or modify it before running.

#### Auto-approval risks

You can enable auto-approval for terminal commands, but understand the risks. Agents might run destructive commands without your knowledge, commands execute before you can review them, and bugs or prompt injection could cause unintended operations.

#### Auto-run configuration

Enterprise teams can configure auto-run policies in the team dashboard. You can create an allowlist of commands that don't require approval, such as `npm install`, `pip install`, `cargo build`, or `make test`.

The allowlist is best-effort, not a security boundary. Determined agents or prompt injection might bypass it. Always combine allowlists with other security controls like hooks.

See [Agent Security](https://cursor.com/docs/agent/security.md) for details on terminal command controls.

### Enforcement hooks

Hooks let you run custom logic at key points in the agent loop.

- Before prompt submission: Scan prompts for sensitive data before they're sent to LLMs. Block submissions that contain API keys or credentials, personal identifiable information (PII), or proprietary information.
- Before file reading: Scan files before agents read them. Redact or block access to configuration files with secrets, PII in databases or logs, or proprietary algorithms.
- After code generation: Scan generated code before it's written to disk. Check for security vulnerabilities (SQL injection, XSS), licensed code that might cause IP issues, or API keys and credentials in code.
- Before terminal execution: Block dangerous commands or route them through approval workflows. For example, block all `git push` commands, require approval for any `sudo` command, or block database `DROP` statements.

#### Example: Blocking git commands

This hook intercepts shell commands and blocks raw git usage, directing users to the GitHub CLI instead:

```bash
#!/bin/bash
input=$(cat)
command=$(echo "$input" | jq -r '.command')

if [[ "$command" =~ git[[:space:]] ]]; then
    cat << EOF
{
  "permission": "deny",
  "userMessage": "Git command blocked. Please use gh tool instead.",
  "agentMessage": "Use 'gh' commands instead of raw git."
}
EOF
fi
```

#### Example: Redacting secrets

This hook scans file contents for GitHub API keys and blocks access if found:

```bash
#!/bin/bash
input=$(cat)
content=$(echo "$input" | jq -r '.content')

if echo "$content" | grep -qE 'gh[ps]_[A-Za-z0-9]{36}'; then
    cat << EOF
{
  "permission": "deny"
}
EOF
    exit 3
fi
```

See [Hooks](https://cursor.com/docs/agent/hooks.md) for complete documentation and more examples.

### Protecting sensitive files

Not all files in your repositories should be accessible to AI. Configuration files, secrets, and sensitive data need protection.

#### .cursorignore

The `.cursorignore` file works like `.gitignore` but controls what Cursor can access. Files matching patterns in `.cursorignore` are excluded from:

- [Semantic search](https://cursor.com/docs/context/semantic-search.md)
- Agent file reading
- Context selection
- Semantic search

`.cursorignore` is not a security boundary. It's a convenience feature to exclude files from AI processing, but:

- Users can manually read ignored files
- Agents might find ways to access ignored content
- It doesn't prevent file access, only excludes from indexing

For true security, use file system permissions or encrypt sensitive data.

See [Ignore Files](https://cursor.com/docs/context/ignore-files.md) for detailed syntax.

#### .cursor directory protection

The `.cursor` directory in repositories contains project-specific settings, rules, and cache files. Enterprise teams can prevent agents from modifying this directory.

When enabled, agents cannot:

- Modify files in `.cursor/`
- Delete the `.cursor/` directory
- Change cursor rules or settings files

Users can still manually edit these files, but agents require approval.

Configure in the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) under ".cursor Directory Protection" (Enterprise only).

#### Browser origin controls

Enterprise teams can restrict which websites agents can navigate to when using the [browser tool](https://cursor.com/docs/agent/browser.md). Define an allowlist of approved domains—agents attempting to visit other origins are blocked.

Configure in the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) under "Browser Controls" (Enterprise only).

### Integration with DLP tools

Many enterprises have existing Data Loss Prevention (DLP) tools that scan for sensitive data. You can integrate Cursor with your DLP tools in three ways.

#### Endpoint DLP agents

Most endpoint DLP software can inspect Cursor's network traffic. Configure your DLP to monitor traffic to `*.cursor.sh` domains, scan for sensitive patterns in outbound requests, and block or alert on policy violations.

Network DLP may impact performance. See [Network Configuration](https://cursor.com/docs/enterprise/network-configuration.md) for proxy considerations.

#### Hooks-based DLP

Use Cursor's hooks feature to implement custom DLP logic:

**Before prompt submission:**
Scan prompts for sensitive patterns before sending to LLMs:

```bash
#!/bin/bash
input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt')

# Check for API keys
if echo "$prompt" | grep -qE 'api[_-]?key.*[A-Za-z0-9]{32}'; then
    cat << EOF
{
  "continue": false,
  "userMessage": "Prompt contains what looks like an API key. Remove it and try again."
}
EOF
    exit 1
fi

# Allow if no sensitive data found
cat << EOF
{
  "continue": true
}
EOF
```

**After code generation:**
Scan generated code before it's written to disk:

```bash
#!/bin/bash
input=$(cat)
file_path=$(echo "$input" | jq -r '.file_path')
edits=$(echo "$input" | jq -r '.edits[].new_string')

# Check for hardcoded credentials
if echo "$edits" | grep -qE 'password.*=.*["\047][^"\047]+["\047]'; then
    # Send to your DLP API for analysis
    curl -X POST "https://dlp.yourcompany.com/scan" \
      -H "Content-Type: application/json" \
      -d "{\"content\":\"$edits\",\"file\":\"$file_path\"}"
    
    # Check API response and act accordingly
fi
```

#### Third-party DLP integration

Call your existing DLP vendor's API from hooks:

```bash
#!/bin/bash
input=$(cat)
content=$(echo "$input" | jq -r '.content')

# Send to DLP API
response=$(curl -s -X POST "https://dlp-api.company.com/analyze" \
  -H "Authorization: Bearer $DLP_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"text\":\"$content\"}")

# Parse response
is_allowed=$(echo "$response" | jq -r '.allowed')

if [ "$is_allowed" = "true" ]; then
    cat << EOF
{
  "permission": "allow"
}
EOF
else
    violation=$(echo "$response" | jq -r '.violation_type')
    cat << EOF
{
  "permission": "deny",
  "userMessage": "Content blocked by DLP policy: $violation"
}
EOF
fi
```

This approach gives you centralized DLP policy management across all development tools.

### Approval workflows

You can configure Cursor to ask for approval on every agent action. Users can set their agent to always ask before reading files, editing files, running terminal commands, or making network requests.

However, this approach significantly slows down the development experience. Agents need multiple actions to complete tasks, and requiring approval for each action makes the workflow tedious. Most teams instead choose to use hooks to block dangerous operations automatically.

### Model provider safety

All model providers (OpenAI, Anthropic, Google, xAI) implement safety systems that filter harmful content. These systems reject prompts requesting harmful information, refuse to generate dangerous code, and filter outputs for safety.

Cursor works with providers to ensure models meet safety standards before deployment to users. Providers continuously evaluate models for safety issues. However, these are not security boundaries. Safety systems can be bypassed or tricked. Always implement your own controls through hooks and access policies.

### Sandboxing considerations

Cursor agents run on your local machine by default. They can read files you can read, write files you can write, execute commands you can execute, and access network resources you can access.

There is no security boundary between agents and your user account. If your account can delete files, agents can delete files (with approval by default).

#### Sandboxing options

If you need stronger isolation, run Cursor in a separate VM using Cloud Agents, use file system permissions to limit what the Cursor process can access, or run Cursor on a dedicated development machine with limited access to production systems.

For most enterprises, the built-in approval requirements and hooks provide sufficient control.

### File system permissions

For further defense, use file system permissions to protect sensitive files:

**Restrict access to secret files:**

```bash
# Make secrets readable only by specific users
chmod 600 .env
chown app-user:app-user .env

# Or use separate directories with restricted access
chmod 700 /etc/app/secrets
```

**Separate sensitive repos:**
Keep highly sensitive code in separate repositories with restricted access. Don't clone these repositories to machines where Cursor runs.

**Encrypted filesystems:**
For very sensitive data, use encrypted filesystems that require explicit mounting. Don't mount these filesystems in directories where Cursor has access.

## LLM steering

Security controls block harmful actions after the LLM suggests them. Steering mechanisms guide the LLM to make better suggestions in the first place. These are non-deterministic. They improve outcomes but don't guarantee prevention.

### Rules

Rules add instructions to the LLM's context window before every request. Use rules to establish coding standards, enforce architectural patterns, set security requirements, or define project-specific conventions.

Rules work at three scopes:

**User rules**: Apply to all projects for a specific user. Use these for personal preferences like code style or preferred libraries.

**Project rules**: Apply to everyone working on a project. Use these for project-specific standards like naming conventions or framework usage.

**Team rules**: Apply to all projects in your organization. Use these for company-wide standards like security requirements or compliance rules.

The LLM sees all applicable rules when generating responses. It will attempt to follow them, but rules are suggestions, not guarantees. Combine rules with enforcement hooks for requirements that must be followed.

See [Rules](https://cursor.com/docs/context/rules.md) for configuration and examples.

### Commands and workflows

Commands package reusable prompts that agents can invoke with slash commands like `/test` or `/deploy`. Commands help standardize common workflows across your team.

**Workflows**: Create multi-step processes that guide agents through complex tasks. For example, a `/security-review` command might instruct the agent to scan for SQL injection, check for exposed secrets, validate input sanitization, and generate a security report.

**Prompt libraries**: Build a collection of tested prompts for common tasks. This reduces variation in agent behavior and captures institutional knowledge.

Commands are scoped to teams, projects, or users. Team admins can create organization-wide commands that appear for all developers.

See [Commands](https://cursor.com/docs/context/commands.md) for configuration and examples.

### Context enrichment with MCPs

Model Context Protocol (MCP) servers let agents access external data sources. Use MCPs to pull in company documentation, query internal APIs, access knowledge bases, or integrate with development tools.

MCPs enrich the agent's context with information it wouldn't otherwise have. For example, an MCP might provide access to your API specifications, so agents can generate code that correctly calls your internal services.

MCPs are scoped to teams or users. Unlike hooks, MCPs don't enforce policies—they provide information that helps agents make better decisions.

See [MCP Integration](https://cursor.com/docs/agent/mcp.md) for configuration and examples.

### Advanced safety controls for Enterprise

Contact our team to learn about org-wide enforcement and security policies.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/model-and-integration-management.md
# INDEX: 87/114
================================================================================

# Model and Integration Management

Your team can access multiple AI models and integrate Cursor with various services. This documentation covers how to control which models are available, manage MCP server trust, and set up integrations with tools like Slack, GitHub, and Linear.

## Model access control

Enterprise teams can control which AI models team members can use, [contact sales](https://cursor.com/contact-sales?source=docs-model-controls) to get access. This helps manage costs, ensure appropriate usage, and comply with organizational policies.

Model access controls are configured through the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md). Navigate to Settings and look for "Model Access Control" (Enterprise only).

### How enterprise model rollout works

When new models become available, Cursor doesn't immediately enable them for all enterprise teams.

Instead, Enterprise teams can opt in to new models for their organization.

See [Models](https://cursor.com/docs/models.md) for the current list of available models.

## Restrict personal API keys (BYOK controls)

Enterprise teams can prevent team members from using their own API keys with third-party providers (OpenAI, Anthropic, Azure, AWS Bedrock) in Cursor. All usage goes through Cursor's included models and usage pool.

Configure this in the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) under Settings (Enterprise only).

## MCP server trust management

The Model Context Protocol (MCP) lets you connect external tools and data sources to Cursor. MCP servers can:

- Read files from external systems
- Execute operations on your behalf
- Access databases and APIs
- Integrate with third-party services

MCP servers are designed and implemented by external vendors, not Cursor. We work with partners to provide a [vetted directory](https://cursor.com/docs/context/mcp/directory.md) of trusted servers, but you should review each server's capabilities and permissions before enabling it for your team.

Because MCP servers have significant capabilities, you need to manage which servers your team can use.

### MCP Allowlist

Enterprise teams can control which MCP servers team members are allowed to use. Configure this in the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) under "MCP Configuration" (Enterprise only).

When an allowlist is active, only servers matching an allowlist entry can run. Servers that don't match are blocked.

Adding a server to the allowlist does not push it to users' machines. Team members still need to configure the server in their own [Cursor settings](https://cursor.com/docs/context/mcp.md).

All allowlist entries support wildcards using `*` to match any sequence of characters.

#### Command-based servers (stdio)

For local MCP servers configured with `command` and `args`, the allowlist matches against the **full command string**: the `command` value and all `args` values joined with spaces.

Given this `mcp.json` config:

```json
{
  "mcpServers": {
    "my-tool": {
      "command": "npx",
      "args": ["-y", "@acme/mcp-tool@latest"]
    }
  }
}
```

The full command string is `npx -y @acme/mcp-tool@latest`. On most systems, the shell resolves `npx` to a full path like `/usr/local/bin/npx` or `/opt/homebrew/bin/npx`, so the actual string becomes `/usr/local/bin/npx -y @acme/mcp-tool@latest`.

Use a leading `*` wildcard to match regardless of the install path:

| Allowlist entry                               | Matches                                                           |
| :-------------------------------------------- | :---------------------------------------------------------------- |
| `*npx -y @acme/mcp-tool@latest`               | `npx` at any path, with these exact arguments                     |
| `/usr/local/bin/npx -y @acme/mcp-tool@latest` | Only this exact path                                              |
| `*npx -y @acme/*`                             | Any `@acme`-scoped MCP package                                    |
| `*python */scripts/mcp-server.py*`            | A Python server at any matching path, with any trailing arguments |

#### URL-based servers (HTTP/SSE)

For remote MCP servers configured with `url`, the allowlist matches against the URL.

Given this `mcp.json` config:

```json
{
  "mcpServers": {
    "acme-tools": {
      "url": "https://mcp.acme.com/sse"
    }
  }
}
```

The allowlist entry matches against the full URL `https://mcp.acme.com/sse`:

| Allowlist entry            | Matches                                 |
| :------------------------- | :-------------------------------------- |
| `https://mcp.acme.com/sse` | This exact URL                          |
| `https://*.acme.com/*`     | Any subdomain and path under `acme.com` |
| `https://mcp.acme.com/*`   | Any path on this host                   |

## Git repository blocklist

You can prevent Cursor from accessing specific repositories.

Add repository URLs or patterns in the [team dashboard](https://cursor.com/docs/account/teams/dashboard.md) under "Repository Blocklist" (Enterprise only). Cursor will refuse to index or work with blocked repositories.

## Integration: Slack

The Slack integration enables Cloud Agents to run directly from Slack. Team members can mention `@cursor` with a prompt and get automated code changes delivered as pull requests.

Cursor requires permissions to read messages, post responses, and access channel metadata. See the [Slack integration documentation](https://cursor.com/docs/integrations/slack.md#permissions) for the full list.

See [Slack integration](https://cursor.com/docs/integrations/slack.md) for detailed setup and usage instructions.

## Integration: GitHub, GHES, and GitLab

Connect Cursor to your version control system to work with Cloud Agents.

Cursor requires read access to repositories and write access to create PRs. You control which repositories the Cursor app can access.

See [GitHub integration](https://cursor.com/docs/integrations/github.md) for setup.

## Integration: Linear

Connect Linear to start Cloud Agents from issues.

Cursor requires read access to issues and write access to update issue status.

See [Linear integration](https://cursor.com/docs/integrations/linear.md) for details.

### Model controls are available on the Enterprise plan

Contact our team to learn about model restrictions and MCP management.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/network-configuration.md
# INDEX: 88/114
================================================================================

# Network Configuration

Cursor needs to communicate with backend services and AI providers. This documentation covers how to configure Cursor to work within your network infrastructure, including proxies, firewalls, and encryption requirements.

## Proxy configuration

Many enterprises route traffic through proxy servers for monitoring and security. Cursor works with most proxy configurations, but some proxy settings can cause issues with streaming responses.

### HTTP/2 vs HTTP/1.1

Cursor uses HTTP/2 bidirectional streaming by default for real-time chat and agent experiences. Some enterprise proxies don't support HTTP/2 streaming correctly. Zscaler is the most widely used proxy with this limitation.

If you experience issues with streaming, Cursor automatically falls back to HTTP/1.1 Server-Side Events (SSE) mode. This fallback was specifically designed to work with Zscaler and similar proxies that buffer or break HTTP/2 streams. The fallback happens transparently when HTTP/2 bidirectional streaming doesn't work.

### SSL inspection and DLP

Many corporate proxies perform SSL man-in-the-middle inspection to scan traffic for security threats or data loss prevention (DLP). This replaces Cursor's SSL certificates with your proxy's certificates.

When Cursor traffic goes through Secure Web Gateways (SWG), SSL inspection, or DLP, it often causes timeouts, slowness, or errors when using Cursor's Agent capabilities. This is one of the most common deployment blockers for enterprise customers.

Cursor's services are already encrypted end-to-end. We recommend disabling SSL inspection for these domains:

- `.cursor.sh`
- `cursor-cdn.com`
- `marketplace.cursorapi.com`
- `authenticate.cursor.sh`
- `authenticator.cursor.sh`

If your security policy requires SSL inspection on all traffic, your proxy must support:

- HTTP/2 bidirectional streaming (or that Cursor's HTTP/1.1 fallback works)
- Server-Sent Events (SSE) passthrough without buffering
- Long-running connections without forced timeouts
- Disabling response buffering for streaming content types

### Testing proxy connectivity

If you experience connection issues, you can test connectivity manually using curl commands. These commands simulate the requests Cursor makes to backend services.

**Test basic connectivity:**

```bash
curl -v https://api2.cursor.sh |& grep -C1 issuer:
```

This shows which SSL certificate is in use. You should see Amazon RSA. If you see your proxy provider (like Zscaler), SSL inspection is active.

**Test HTTP/1.1 streaming:**

```bash
echo -ne "\x0\x0\x0\x0\x11{\"payload\":\"foo\"}" | \
  curl --http1.1 -No - -XPOST \
  -H "Content-Type: application/connect+json" \
  --data-binary @- \
  https://api2.cursor.sh/aiserver.v1.HealthService/StreamSSE
```

You should see output appear line by line over 5 seconds. If it appears all at once after 5 seconds, your proxy is buffering streaming responses.

**Test HTTP/2 bidirectional streaming:**

```bash
(for i in 1 2 3 4 5; do \
  echo -ne "\x0\x0\x0\x0\x12{\"payload\":\"foo$i\"}"; \
  sleep 1; \
done) | curl -No - -XPOST \
  -H "Content-Type: application/connect+json" \
  -T - \
  https://api2.cursor.sh/aiserver.v1.HealthService/StreamBidi
```

Output should appear once per second. If buffered for 5 seconds, your proxy doesn't support HTTP/2 bidirectional streaming.

## IP allowlisting

If your network uses IP-based access controls, you need to allow traffic to Cursor's backend services.

Rather than maintaining IP address lists (which can change), configure your firewall to allow traffic to these domain patterns:

- `*.cursor.sh`
- `*.cursor-cdn.com`
- `*.cursorapi.com`

## VPC peering

Cursor doesn't currently offer VPC peering or private connectivity options.

However, when you run Cursor agents (either in the editor or via the CLI), they inherit your existing network configuration. If you run Cursor on a machine within your VPC, agent operations inherit:

- Your network security groups
- Your firewall rules
- Your DNS configuration
- Your VPN or private network access

This means Cursor agents can access internal resources that the machine can reach, while following your existing network security controls.

## Encryption

Cursor encrypts data both in transit and at rest.

### In transit

- TLS 1.2 or higher for all connections to Cursor services
- TLS for connections to third-party AI providers
- Certificate pinning for critical services

### At rest

- AES-256 encryption for stored data
- Encrypted vector database storage
- Encrypted code storage for Cloud Agents (when enabled)

### Key management

Cursor manages encryption keys. Keys are rotated according to security best practices and stored in secure key management systems.

For enhanced security control, enterprise customers can use Customer Managed Encryption Keys (CMEK) for encrypting data stored in Cursor's infrastructure. See [Data Encryption](https://cursor.com/docs/enterprise/privacy-and-data-governance.md#data-encryption) for details.

## LLM gateways

Some enterprises want to route LLM traffic through their own gateways for additional monitoring and control.

Custom gateways can introduce additional latency, rate limiting, and compatibility issues. We instead recommend using Cursor's built-in hooks feature to implement your own security controls.

Cursor's [Zero Data Retention policy](https://cursor.com/docs/account/teams/dashboard.md#privacy-settings) does not apply when using your own API keys. Your data handling will be subject to the privacy policies of your chosen AI provider (OpenAI, Anthropic, Google, Azure, or AWS).

See [Hooks](https://cursor.com/docs/agent/hooks.md) and [Security Guardrails](https://cursor.com/docs/enterprise/llm-safety-and-controls.md) for details.

## Cloud Agents networking

Cloud Agents run on Cursor's infrastructure, not your local network. They can access:

- Public GitHub repositories
- GitHub Enterprise Cloud repositories you've granted access to
- GitHub Enterprise Server (self-hosted GitHub Enterprise)
- On-prem + cloud-based GitLab and Bitbucket
- Public package registries (npm, PyPI, etc.)

Cloud Agents cannot access:

- Resources behind your corporate firewall
- On-premises GitHub Enterprise Server
- Private package registries without internet access

If your development workflow requires access to internal resources, use the Cursor editor on machines within your network instead of Cloud Agents.

## Troubleshooting checklist

If you experience connection issues:

1. **Test basic connectivity** to `api2.cursor.sh`
2. **Check if SSL inspection is active** and consider excluding Cursor domains
3. **Verify streaming works** using the curl tests above
4. **Check firewall rules** allow traffic to `*.cursor.sh` and related domains
5. **Review proxy logs** for connection errors or timeouts
6. **Test from a machine outside your network** to isolate network-specific issues

Most connectivity issues stem from proxies buffering streaming responses. Work with your network team to disable buffering for Cursor domains or implement proper streaming support.

### Need help with enterprise network setup?

Contact our team for deployment assistance and priority support.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/enterprise/privacy-and-data-governance.md
# INDEX: 89/114
================================================================================

# Privacy and Data Governance

Understanding how data flows through Cursor is critical for security reviews and compliance assessments. This documentation explains what data goes where, what guarantees you have, and where that data lives geographically.

## Three data flows

There are three ways data leaves your local environment when using Cursor:

### 1. The indexing process

When you open a project in Cursor, we create embeddings that represent your code. These embeddings power semantic search across your codebase.

**What gets sent:**

- Your code, temporarily, to create embeddings
- Nothing is stored; embeddings are generated and the original code is discarded

**What gets stored:**

- One-way mathematical embeddings (vectors) that represent code semantics
- Obfuscated file paths
- Line numbers

**How it works:**
When you ask a question or use Cmd K, we create an embedding from your request and search for similar embeddings in the vector database. The search returns obfuscated file paths and line numbers. We then look up the actual code on your local machine using those coordinates.

The vector database never sees your raw code. It only stores mathematical representations that can't be reverse-engineered back to source code.

### 2. LLM requests

When you use AI features, we send prompts and code context to language model providers like OpenAI, Anthropic, and Google.

**With Privacy Mode enabled:**

- Code is never stored by model providers
- Code is never used for training
- We maintain Zero Data Retention (ZDR) agreements with all providers

**Zero Data Retention agreements:**
We have contractual ZDR policies with OpenAI, Anthropic, Google Vertex AI, and xAI Grok. These agreements legally prevent providers from storing inputs or outputs or using your data for training.

Privacy Mode is on by default for Enterprise teams. See [Privacy Overview](https://cursor.com/privacy-overview) for details.

### 3. Cloud Agents

Cloud Agents are the only feature that requires Cursor to store code. Unlike the indexing process or LLM requests, Cloud Agents need access to your repository over time to make changes.

**Architecture:**

- Agents run in isolated virtual machines
- Each agent has a dedicated environment
- Isolated from other agents and users

**What gets stored:**

- Encrypted copies of repositories that Cloud Agents work on
- Stored temporarily while the agent runs
- Deleted after the agent completes

Cloud Agents are optional. If your security policy prohibits code storage, don't enable Cloud Agents. You can still use all other Cursor features.

See [Cloud Agents](https://cursor.com/docs/cloud-agent.md) for details.

## Privacy Mode enforcement

Privacy Mode can be enabled at the team level to ensure all team members benefit from ZDR guarantees.

**Team-level enforcement:**

1. Go to your [team dashboard](https://cursor.com/dashboard)
2. Navigate to Settings
3. Enable Privacy Mode for the team
4. Optionally enforce it so members can't disable it

**MDM enforcement:**
For additional assurance, use the Allowed Team IDs policy. This prevents users from logging into personal accounts (which might not have Privacy Mode enabled) on corporate devices.

See [Identity and Access Management](https://cursor.com/docs/enterprise/identity-and-access-management.md#allowed-team-ids) for policy details and [Deployment Patterns](https://cursor.com/docs/enterprise/deployment-patterns.md#mdm-configuration) for MDM configuration.

## Compliance and contracts

Our [DPA](https://cursor.com/terms/dpa) includes comprehensive data protection commitments that follow industry standards, including data minimization, access control, and secure processing.

All [sub-processors](https://trust.cursor.com/subprocessors) are covered by appropriate data processing agreements.

## Data encryption

Cursor encrypts data for all infrastructure, including:

- TLS 1.2+ in transit
- AES-256 at rest

For enhanced security control, enterprise customers can use Customer Managed Encryption Keys (CMEK) for encrypting data stored in Cursor's infrastructure.

With CMEK enabled:

- Embeddings are encrypted using your customer encryption key
- Cloud Agent data is encrypted using your customer encryption key
- You control key rotation and access
- Provides additional layer of security beyond standard encryption

[Contact sales](https://cursor.com/contact-sales?source=docs-cmek) to enable CMEK for your organization.

### Enterprise privacy and data controls

Contact our team to learn about CMEK, Privacy Mode enforcement, and more.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/get-started/concepts.md
# INDEX: 90/114
================================================================================

# Concepts

Check out our [learning guides](https://cursor.com/learn.md) covering [AI models](https://cursor.com/learn/how-ai-models-work.md), [context](https://cursor.com/learn/context.md), [agents](https://cursor.com/learn/agents.md), and more.

Tab

Code completion that predicts multi-line edits. Press Tab to accept
suggestions based on your current code and recent changes.

![Tab autocomplete](/docs-static/images/tab/tab-simple.png)

Agent

An AI that can read and modify code across multiple files. Describe
changes in natural language and Agent executes them.

![Agent mode](/docs-static/images/chat/agent.png)

Inline Edit

Edit selected code with natural language. Press Cmd+K to
describe changes and see them applied in place.

![Inline editing](/docs-static/images/inline-edit/qq.png)

Chat

Interface for AI conversations. Supports multiple tabs, conversation
history, checkpoints, and export functionality.

[Media](/docs-static/images/chat/chat-tabs.mp4)

Rules

Custom instructions that define AI behavior. Set coding standards,
framework preferences, and project-specific conventions.

![AI rules](/docs-static/images/context/rules/mdc-editor.png)

Semantic Search

Find code by meaning, not just text. Enables natural language code search
and context-aware suggestions.

![Semantic Search](/docs-static/images/get-started/codebase-indexing.png)

MCP

Model Context Protocol for integrating external tools. Connects to
databases, APIs, and documentation sources.

[Media](/docs-static/images/context/mcp/simple-mcp-call.mp4)

Context

Information provided to AI models during code generation. Includes files,
symbols, and conversation history.

![Context management](/docs-static/images/context/mentions/context-menu.png)

Models

Different AI models available for code generation. Each model has
different speed and capability characteristics.

![Model selection](/docs-static/images/models/model-picker.png)


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/get-started/quickstart.md
# INDEX: 91/114
================================================================================

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


================================================================================
# SOURCE: https://cursor.com/docs/inline-edit/overview.md
# INDEX: 92/114
================================================================================

# Inline Edit

Inline Edit lets you edit code or ask questions directly in your editor with Cmd+K, which opens an input field where your selected code and instructions create your request.

![Inline Edit empty state](/docs-static/images/inline-edit/empty.png)

## Modes

### Edit Selection

With code selected, Cmd+K edits that specific code based on your instructions.

![Inline Edit selection](/docs-static/images/inline-edit/selection.png)

Without selection, Cursor generates new code at your cursor position. The AI includes relevant surrounding code for context. For example, triggering on a function name includes the entire function.

### Quick Question

Press Opt+Return in the inline editor to ask questions about selected code.

After getting an answer, type "do it" or similar wording to convert the suggestion into code. This lets you explore ideas before implementing.

![Inline Edit quick question](/docs-static/images/inline-edit/qq.png)

### Full File Edits

For file-wide changes, use Cmd+Shift+Return. This mode enables comprehensive changes while maintaining control.

![Inline Edit full file](/docs-static/images/inline-edit/full-file.png)

### Send to Chat

For multi-file edits or advanced features, use Cmd+L to send selected code to [Chat](https://cursor.com/docs/agent/modes.md#agent). This provides multi-file editing, detailed explanations, and advanced AI capabilities.

[Media](/docs-static/images/inline-edit/send-to-chat.mp4)

## Follow-up instructions

After each edit, refine results by adding instructions and pressing Return. The AI updates changes based on your feedback.

## Default context

Inline Edit includes default context to improve code generation beyond any [@ mentions](https://cursor.com/docs/context/mentions/files-and-folders.md) you add.

This includes related files, recently viewed code, and relevant information. Cursor prioritizes the most relevant context for better results.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/inline-edit/terminal.md
# INDEX: 93/114
================================================================================

# Terminal

In Cursor terminal, press Cmd+K to open a prompt bar at the bottom.
Describe your desired action and Inline Edit generates a command.

![Inline Edit terminal](/docs-static/images/inline-edit/terminal.png)

Inline Edit in terminal uses your recent terminal history, instructions, and prompt content as context.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/cursor-blame.md
# INDEX: 94/114
================================================================================

# Cursor Blame

Cursor Blame is available on the Enterprise plan.

Cursor Blame extends traditional git blame with AI attribution, showing you exactly what was AI-generated versus human-written in your codebase.

## Overview

When reviewing or revisiting code, Cursor Blame helps you understand the origin of each line:

- **Tab**: Code generated or accepted from Cursor's Tab suggestions
- **Agent**: Code generated by Agent, with model attribution
- **Human**: Code written directly by developers

Hover over AI-attributed lines to see conversation summaries. Click to open the full commit view with detailed AI attribution.

## How it works

Cursor Blame analyzes committed code to determine AI attribution. When you view a file or commit, it retrieves attribution data that identifies which lines came from AI assistance, which models were used, and the conversations that produced them.

### AI attribution

See at a glance which lines came from AI assistance and which were written manually.

### Model tracking

Agent-generated code shows which model produced it, helping you understand AI tool usage across your codebase.

### Conversation context

View summaries of the conversations that produced AI-generated code, with links to the full commit details.

### Contribution breakdown

See percentage attribution for each contributor (AI models and human) in the commit view.

## Using Cursor Blame

### Enabling Cursor Blame

Cursor Blame is disabled at the team level by default. A team admin can enable it for all team members in the [Team settings](https://cursor.com/dashboard?tab=settings).

### Line annotations

1. Open the Command Palette (Cmd+Shift+P) and search for "Cursor Blame: Toggle editor decorations"

**In-editor ghost text** displays:

- **Author**: The team member who committed the change
- **Subject**: The commit message
- **Time**: When the change was made (relative time)

**Hover over the ghost text** to see:

- Author with AI co-authorship indicator
- Conversation summary (for AI-attributed lines)
- Commit statistics (files, additions, deletions)

**Open the commit view** to see:

- Full AI contribution breakdown by source
- Percentage attribution for Composer, each Agent model, and human edits
- Related conversations with summaries

### File blame view

1. Open a file in the editor
2. Right-click and select **Cursor Blame > Toggle file blame** from the context menu, or use the Command Palette (Cmd+Shift+P) and search for "Cursor Blame: Open File Blame"
3. The file blame view shows attribution alongside each line

## Privacy considerations

Cursor Blame caches attribution data locally for performance. When you view files and commits, data is fetched from Cursor's servers. Conversation summaries are retrieved on-demand and show brief descriptions rather than full conversation history.

## Requirements

- Enterprise plan
- Git repository with Cursor-tracked changes


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/deeplinks.md
# INDEX: 95/114
================================================================================

# Deeplinks

Deeplinks allow you to share prompts, commands, and rules with others, enabling collaboration and knowledge sharing across teams and communities.

[Media](/docs-static/images/integrations/deeplinks.mp4)

Links can also be opened via [cursor.com](https://cursor.com). Append the path and url params to the end of the url, for example: [cursor.com/link/prompt?text=...](https://cursor.com/link/prompt?text=Research+and+find+one+bug+in+this+codebase)

Always review your prompts and commands before sharing to ensure they don't contain sensitive information like API keys, passwords, or proprietary code.

## Prompts

Share prompts that others can use to get started quickly with specific tasks or workflows. When someone clicks a prompt deeplink, it opens Cursor with the prompt pre-filled in the chat. The user must review and confirm the prompt before it gets executed. Deeplinks never trigger automatic execution.

Research and find one bug in this codebase

### Playground

### TypeScript

```typescript
const IS_WEB = false; // Set to true for web format

function generatePromptDeeplink(promptText: string): string {
  const baseUrl = IS_WEB
    ? 'https://cursor.com/link/prompt'
    : 'cursor://anysphere.cursor-deeplink/prompt';
  const url = new URL(baseUrl);
  url.searchParams.set('text', promptText);
  return url.toString();
}

const deeplink = generatePromptDeeplink("Create a React component for user authentication");
console.log(deeplink);
```

### Python

```python
from urllib.parse import urlencode, urlparse, urlunparse

IS_WEB = False  # Set to True for web format

def generate_prompt_deeplink(prompt_text: str) -> str:
    base_url = "https://cursor.com/link/prompt" if IS_WEB else "cursor://anysphere.cursor-deeplink/prompt"
    params = {"text": prompt_text}
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"

deeplink = generate_prompt_deeplink("Create a React component for user authentication")
print(deeplink)
```

## Commands

Share commands that others can execute directly in their Cursor environment. Command deeplinks allow you to share custom commands defined in your `.cursor/commands` directory. When someone clicks a command deeplink, it opens Cursor and creates a new command with the specified name and content. The user must review and confirm the command before it gets executed.

debug-api

Add console.log statements to debug API responses

### Playground

### TypeScript

```typescript
const IS_WEB = false; // Set to true for web format

function generateCommandDeeplink(commandName: string, commandContent: string): string {
  const baseUrl = IS_WEB
    ? 'https://cursor.com/link/command'
    : 'cursor://anysphere.cursor-deeplink/command';
  const url = new URL(baseUrl);
  url.searchParams.set('name', commandName);
  url.searchParams.set('text', commandContent);
  return url.toString();
}

const deeplink = generateCommandDeeplink("debug-api", "Add console.log statements to debug API responses");
console.log(deeplink);
```

### Python

```python
from urllib.parse import urlencode, urlparse, urlunparse

IS_WEB = False  # Set to True for web format

def generate_command_deeplink(command_name: str, command_content: str) -> str:
    base_url = "https://cursor.com/link/command" if IS_WEB else "cursor://anysphere.cursor-deeplink/command"
    params = {"name": command_name, "text": command_content}
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"

deeplink = generate_command_deeplink("debug-api", "Add console.log statements to debug API responses")
print(deeplink)
```

## Rules

Share rules that others can add to their Cursor environment. Rule deeplinks allow you to share custom rules defined in your `.cursor/rules` directory. When someone clicks a rule deeplink, it opens Cursor and creates a new rule with the specified name and content. The user must review and confirm the rule before it gets added.

typescript-strict

Always use strict TypeScript types and avoid 'any'

### Playground

### TypeScript

```typescript
const IS_WEB = false; // Set to true for web format

function generateRuleDeeplink(ruleName: string, ruleContent: string): string {
  const baseUrl = IS_WEB
    ? 'https://cursor.com/link/rule'
    : 'cursor://anysphere.cursor-deeplink/rule';
  const url = new URL(baseUrl);
  url.searchParams.set('name', ruleName);
  url.searchParams.set('text', ruleContent);
  return url.toString();
}

const deeplink = generateRuleDeeplink("typescript-strict", "Always use strict TypeScript types and avoid 'any'");
console.log(deeplink);
```

### Python

```python
from urllib.parse import urlencode, urlparse, urlunparse

IS_WEB = False  # Set to True for web format

def generate_rule_deeplink(rule_name: str, rule_content: str) -> str:
    base_url = "https://cursor.com/link/rule" if IS_WEB else "cursor://anysphere.cursor-deeplink/rule"
    params = {"name": rule_name, "text": rule_content}
    query_string = urlencode(params)
    return f"{base_url}?{query_string}"

deeplink = generate_rule_deeplink("typescript-strict", "Always use strict TypeScript types and avoid 'any'")
print(deeplink)
```

## FAQ

### What is the maximum length for deeplink URLs?

Deeplink URLs have a maximum length of 8,000 characters. When generating deeplinks programmatically, ensure your content doesn't exceed this limit when URL-encoded. The interactive generators above will show you the current URL length and remaining characters as you type.

### How do I use deeplinks on the web instead of in the Cursor app?

You can swap the deeplink protocol for web links by changing the base URL from `cursor://anysphere.cursor-deeplink/` to `https://cursor.com/link/`. For example:

```text
cursor://anysphere.cursor-deeplink/prompt?text=Hello%20world
```

```text
https://cursor.com/link/prompt?text=Hello%20world
```

Web links will redirect users to cursor.com where they can open the deeplink in their browser or copy it to use in Cursor.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/git.md
# INDEX: 96/114
================================================================================

# Git

Cursor provides AI-powered Git features to streamline your workflow, including automatic commit message generation and intelligent merge conflict resolution.

## AI Commit Message

Cursor generates commit messages from staged changes.

1. Stage files to commit
2. Open the Git tab in the sidebar
3. Click the sparkle (✨) icon next to the commit message input

Generated messages use staged changes and repository git history. If you use conventions like [Conventional Commits](https://www.conventionalcommits.org/), messages follow the same pattern.

### Add shortcut

To bind to a keyboard shortcut:

1. Go to Keyboard Shortcuts (Cmd+R Cmd+S or Cmd+Shift+P and search "Open Keyboard Shortcuts (JSON)")

2. Add this binding for Cmd+M:

   ```json
   {
     "key": "cmd+m",
     "command": "cursor.generateGitCommitMessage"
   }
   ```

3. Save

You cannot customize commit message generation. Cursor adapts to your existing
commit style.

## AI Resolve Conflicts

When merge conflicts occur, Cursor Agent can help resolve them by understanding both sides of the conflict and proposing a resolution.

### How to use

1. When a merge conflict occurs, you'll see the conflict markers in your file
2. Click the **Resolve in Chat** button that appears in the merge conflict UI
3. Agent will analyze both versions and suggest a resolution
4. Review the proposed changes and apply them

## Agent Attribution

Cursor can automatically add attribution to commits and pull requests made by the Agent, making it easy to identify AI-assisted contributions in your git history.

### Settings

Both settings are enabled by default. Configure in **Cursor Settings > Agent > Attribution**.

### Commit Attribution

When enabled, Agent commits include a `Co-authored-by` trailer:

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

This trailer is automatically appended to any git commit command the Agent runs.

### PR Attribution

When enabled, pull requests created by the Agent include a footer:

```
Made with [Cursor](https://cursor.com)
```

This is automatically added to the body of any `gh pr create` command the Agent runs.

Attribution is only added to commits and PRs created by the Agent. The modifications are idempotent: if the attribution already exists, it won't be added again.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/github.md
# INDEX: 97/114
================================================================================

# GitHub

[Cloud Agents](https://cursor.com/docs/cloud-agent.md) and [Bugbot](https://cursor.com/docs/bugbot.md) require the Cursor GitHub app to clone repositories and push changes.

## Installation

1. Go to [Integrations in Dashboard](https://cursor.com/dashboard?tab=integrations)
2. Click **Connect** next to GitHub
3. Choose repository either **All repositories** or **Selected repositories**

To disconnect your GitHub account, return to the integrations dashboard and click **Disconnect Account**.

## Using Agent in GitHub

The GitHub integration enables cloud agent workflows directly from pull requests and issues. You can trigger an agent to read context, implement fixes, and push commits by commenting `@cursor [prompt]` on any PR or issue.

If you have [Bugbot](https://cursor.com/docs/bugbot.md) enabled, you can comment `@cursor fix` to read the suggested fix from Bugbot to trigger a cloud agent to address the issue.

## Permissions

The GitHub app requires specific permissions to work with cloud agents:

| Permission                | Purpose                                          |
| ------------------------- | ------------------------------------------------ |
| **Repository access**     | Clone your code and create working branches      |
| **Pull requests**         | Create PRs with agent changes for your review    |
| **Issues**                | Track bugs and tasks that agents discover or fix |
| **Checks and statuses**   | Report on code quality and test results          |
| **Actions and workflows** | Monitor CI/CD pipelines and deployment status    |

All permissions follow the principle of least privilege needed for cloud agent functionality.

## IP Allow List Configuration

If your organization uses GitHub's IP allow list feature to restrict access to your repositories, Cursor can be configured to use a hosted GitHub proxy with a narrow set of egress IPs.

Before configuring IP allowlists, contact [hi@cursor.com](mailto:hi@cursor.com) to enable this feature for your team. This is required for either configuration method below.

### Enable IP allow list configuration for installed GitHub Apps (recommended)

The Cursor GitHub app has the IP list already pre-configured. You can enable the allowlist for installed apps to automatically inherit this list. This is the **recommended approach**, as it allows us to update the list and your organization receives updates automatically.

To enable this:

1. Go to your organization's Security settings
2. Navigate to IP allow list settings
3. Check **"Allow access by GitHub Apps"**

For detailed instructions, see [GitHub's documentation](https://docs.github.com/en/enterprise-cloud@latest/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/managing-allowed-ip-addresses-for-your-organization#allowing-access-by-github-apps).

### Add IPs directly to your allowlist

If your organization uses IdP-defined allowlists in GitHub or otherwise cannot use the pre-configured allowlist, you can manually add the IP addresses:

```text
184.73.225.134
3.209.66.12
52.44.113.131
```

The list of IP addresses may infrequently change. Teams using IP allow lists
will be given advanced notice before IP addresses are added or removed.

## Troubleshooting

### Agent can't access repository

- Install the GitHub app with repository access
- Check repository permissions for private repos
- Verify your GitHub account permissions

### Permission denied for pull requests

- Grant the app write access to pull requests
- Check branch protection rules
- Reinstall if the app installation expired

### App not visible in GitHub settings

- Check if installed at organization level
- Reinstall from [github.com/apps/cursor](https://github.com/apps/cursor)
- Contact support if installation is corrupted


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/gitlab.md
# INDEX: 98/114
================================================================================

# GitLab

[Cloud Agents](https://cursor.com/docs/cloud-agent.md) and [Bugbot](https://cursor.com/docs/bugbot.md) support GitLab for repository access and merge request reviews.

## Setup

For setup instructions (GitLab.com or self-hosted), see the [Bugbot documentation](https://cursor.com/docs/bugbot.md#setup) under the **GitLab.com** or **GitLab Self-Hosted** tabs.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/linear.md
# INDEX: 99/114
================================================================================

# Linear

Use [Cloud Agents](https://cursor.com/docs/cloud-agent.md) directly from Linear by delegating issues to Cursor or mentioning `@Cursor` in comments.

[Media](/docs-static/images/integrations/linear/linear-agent.mp4)

## Get started

### Installation

You must be a Cursor admin to connect the Linear integration. Other team
settings are available to non-admin members.

1. Go to [Cursor integrations](https://www.cursor.com/dashboard?tab=integrations)
2. Click *Connect* next to Linear
3. Connect your Linear workspace and select team
4. Click *Authorize*
5. Complete any remaining Cloud Agent setup in Cursor:
   - Connect GitHub and select default repository
   - Enable usage-based pricing
   - Confirm privacy settings

### Account linking

First use prompts account linking between Cursor and Linear. GitHub connection required for PR creation.

## How to use

Delegate issues to Cursor or mention `@Cursor` in comments. Cursor analyzes issues and filters out non-development work automatically.

### Delegating issues

1. Open Linear issue
2. Click assignee field
3. Select "Cursor"

![Delegating an issue to Cursor in Linear](/docs-static/images/integrations/linear/linear-delegate.png)

### Mentioning Cursor

Mention `@Cursor` in a comment to assign a new agent or provide additional instructions, for example: `@Cursor fix the authentication bug described above`.

## Workflow

Cloud Agents show real-time status in Linear and create PRs automatically when complete. Track progress in [Cursor dashboard](https://www.cursor.com/dashboard?tab=cloud-agents).

![Cloud Agent status updates in Linear](/docs-static/images/integrations/linear/linear-activity.png)

### Follow-up instructions

You can respond in the agent session and it'll get sent as a follow-up to the agent. Simply mention `@Cursor` in a Linear comment to provide additional guidance to a running Cloud Agent.

## Configuration

Configure Cloud Agent settings from [Dashboard → Cloud Agents](https://www.cursor.com/dashboard?tab=cloud-agents).

| Setting                | Location         | Description                                               |
| :--------------------- | :--------------- | :-------------------------------------------------------- |
| **Default Repository** | Cursor Dashboard | Primary repository when no project repository configured  |
| **Default Model**      | Cursor Dashboard | AI model for Cloud Agents                                 |
| **Base Branch**        | Cursor Dashboard | Branch to create PRs from (typically `main` or `develop`) |

### Configuration options

You can configure Cloud Agent behavior using several methods:

**Issue description or comments**: Use `[key=value]` syntax, for example:

- `@cursor please fix [repo=anysphere/everysphere]`
- `@cursor implement feature [model=claude-3.5-sonnet] [branch=feature-branch]`

**Issue labels**: Use parent-child label structure where the parent label is the configuration key and the child label is the value.

**Project labels**: Same parent-child structure as issue labels, applied at the project level.

Supported configuration keys:

- `repo`: Specify target repository (e.g., `owner/repository`)
- `branch`: Specify base branch for PR creation
- `model`: Specify AI model to use

### Repository selection

Cursor determines which repository to work on using this priority order:

1. **Issue description/comments**: `[repo=owner/repository]` syntax in issue text or comments
2. **Issue labels**: Repository labels attached to the specific Linear issue
3. **Project labels**: Repository labels attached to the Linear project
4. **Default repository**: Repository specified in Cursor dashboard settings

#### Setting up repository labels

To create repository labels in Linear:

1. Go to **Settings** in your Linear workspace
2. Click **Labels**
3. Click **New group**
4. Name the group "repo" (case insensitive - must be exactly "repo", not "Repository" or other variations)
5. Within that group, create labels for each repository using the format `owner/repo`

These labels can then be assigned to issues or projects to specify which repository the Cloud Agent should work on.

![Configuring repository labels in Linear](/docs-static/images/integrations/linear/linear-project-labels.png)

## Advanced features

### Triage rules (Advanced)

Set up automation rules in Linear to automatically delegate issues to Cursor:

1. Go to Linear project settings
2. Navigate to triage rules
3. Create rules that automatically:
   - Add specific labels
   - Assign issues to Cursor
   - Trigger Cloud Agents based on conditions

Triage rules are an advanced feature with some current limitations. Linear
requires a human assignee for rules to fire, though this requirement may be
removed in future updates.

### Getting help

Check [agent activity](https://www.cursor.com/dashboard?tab=cloud-agents) and include request IDs when contacting support.

## Feedback

Share feedback through Linear comments or your Cursor dashboard support channels.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/integrations/slack.md
# INDEX: 100/114
================================================================================

# Slack

With Cursor's integration for Slack, you can use [Cloud Agents](https://cursor.com/docs/cloud-agent.md) to work on your tasks directly from Slack by mentioning `@cursor` with a prompt.

[Media](/docs-static/images/cloud-agent/slack/slack-agent.mp4)

## Get started

### Installation

1. Go to [Cursor integrations](https://www.cursor.com/dashboard?tab=integrations)

2. Click *Connect* next to Slack or go to [installation page](https://cursor.com/api/install-slack-app) from here

3. You'll be prompted to install the Cursor app for Slack in your workspace.

4. After installing in Slack, you'll be redirected back to Cursor to finalize setup

   1. Connect GitHub (if not already connected) and pick a default repository
   2. Enable usage-based pricing
   3. Confirm privacy settings

5. Start using Cloud Agents in Slack by mentioning `@cursor`

[Media](/docs-static/images/cloud-agent/slack/cursor-slack-install.mp4)

## How to use

Mention `@cursor` and give your prompt. Cursor automatically picks the right repository and model based on your message and your recent agent activity.

To use a specific repository, include its name in your message:

- `@Cursor in cursor-app, fix the login bug`
- `@Cursor fix the auth issue in backend-api`

To use a specific model, mention it in your message:

- `@Cursor with opus, fix the login bug`
- `@Cursor use gpt-5.2 to refactor the auth module`

### Commands

Run `@Cursor help` for an up-to-date command list.

| Command                      | Description                                                                      |
| :--------------------------- | :------------------------------------------------------------------------------- |
| `@Cursor [prompt]`           | Start a Cloud Agent. In threads with existing agents, adds followup instructions |
| `@Cursor settings`           | Configure defaults and channel's default repository                              |
| `@Cursor [options] [prompt]` | Use advanced options: `branch`, `autopr`                                         |
| `@Cursor agent [prompt]`     | Force create a new agent in a thread                                             |
| `@Cursor list my agents`     | Show your running agents                                                         |

#### Options

Customize Cloud Agent behavior with these options:

| Option   | Description                          | Example        |
| :------- | :----------------------------------- | :------------- |
| `branch` | Specify base branch                  | `branch=main`  |
| `autopr` | Enable/disable automatic PR creation | `autopr=false` |

#### Syntax Formats

Natural:

```bash
@Cursor with opus, fix the login bug in backend-api
```

Inline:

```bash
@Cursor branch=dev autopr=false Fix the login bug in backend-api
```

#### Option precedence

When combining options:

- **Explicit values** override defaults
- **Later values** override earlier ones if duplicated
- **Inline options** take precedence over settings modal defaults

The bot parses options from anywhere in the message, allowing natural command writing.

#### Using thread context

Cloud Agents understand and use context from existing thread discussions. Useful when your team discusses an issue and you want the agent to implement the solution based on that conversation.

Cloud Agents read the entire thread for context when invoked,
understanding and implementing solutions based on the team's discussion.

#### When to use force commands

**When do I need `@Cursor agent`?**

In threads with existing agents, `@Cursor [prompt]` adds followup instructions (only works if you own the agent). Use `@Cursor agent [prompt]` to launch a separate agent.

**When do I need `Add follow-up` (from context menu)?**

Use the context menu (⋯) on an agent's response for followup instructions. Useful when multiple agents exist in a thread and you need to specify which one to follow up on.

### Status updates & handoff

When Cloud Agent runs, you first get an option to *Open in Cursor*.

![Open in Cursor button in Slack](/docs-static/images/cloud-agent/slack/slack-open-in-cursor.png)

When Cloud Agent completes, you get a notification in Slack and an option to view the created PR in GitHub.

![View PR in GitHub in Slack](/docs-static/images/cloud-agent/slack/slack-view-pr.png)

### Managing agents

To see all running agents, run `@Cursor list my agents`.

Manage Cloud Agents using the context menu by clicking the three dots (⋯) on any agent message.

![Slack agent context menu](/docs-static/images/cloud-agent/slack/slack-context-menu.png)

Available options:

- **Add follow-up**: Add instructions to an existing agent
- **Delete**: Stop and archive the Cloud Agent
- **View request ID**: View unique request ID for troubleshooting (include when contacting support)
- **Give feedback**: Provide feedback about agent performance

## Configuration

Manage default settings and privacy options from [Dashboard → Cloud Agents](https://www.cursor.com/dashboard?tab=cloud-agents).

### Settings

#### Default Model

Used when no model is specified in your message. See [settings](https://www.cursor.com/dashboard?tab=cloud-agents) for available options.

#### Repository Selection

Cursor automatically selects the right repository based on:

1. **Your message content** — Repository names or keywords in your prompt
2. **Recent agent activity** — Repositories you've used recently
3. **Routing rules** — Custom keyword-to-repo mappings (see below)
4. **Default repository** — Fallback when no match is found

To use a specific repository, include its name in your message. For example: `@Cursor in mobile-app, fix the login bug`.

#### Base Branch

Starting branch for Cloud Agent. Leave blank to use the repository's default branch (often `main`)

### Channel Settings

Configure default settings at the channel level using `@Cursor settings`. These settings are per team and override your personal defaults for that channel.

Particularly useful when:

- Different channels work on different repositories
- Teams want consistent settings across all members

To configure channel settings:

1. Run `@Cursor settings` in the desired channel
2. Set the default repository for that channel
3. All team members using Cloud Agents in that channel use these defaults

Channel settings take precedence over personal defaults but can be overridden
by mentioning a specific repo in your message.

### Routing Rules

Routing rules let you define keywords that automatically map to specific repositories. When your message contains specific keywords, Cursor routes the agent to the associated repo.

#### Setting up routing rules

1. Go to [Dashboard → Cloud Agents](https://www.cursor.com/dashboard?tab=cloud-agents)
2. Find the **Routing Rules** section
3. Add keyword-to-repository mappings

#### Example rules

| Keyword    | Repository              |
| :--------- | :---------------------- |
| `frontend` | `acme/web-app`          |
| `mobile`   | `acme/mobile-app`       |
| `api`      | `acme/backend-services` |
| `docs`     | `acme/documentation`    |

With these rules configured:

- `@Cursor fix the frontend nav bug` → routes to `acme/web-app`
- `@Cursor update the mobile onboarding flow` → routes to `acme/mobile-app`
- `@Cursor add rate limiting to the api` → routes to `acme/backend-services`

#### How routing works

Cursor evaluates your message in this order:

1. **Your message content** — Repository names or keywords in your prompt
2. **Recent agent activity** — Repositories you've used recently
3. **Routing rules** — Custom keyword-to-repo mappings
4. **Channel default** — The repository set for this channel
5. **Default repository** — Fallback when no match is found

### Privacy

Cloud Agents support Privacy Mode.

Read more about [Privacy Mode](https://www.cursor.com/privacy-overview) or manage your [privacy settings](https://www.cursor.com/dashboard?tab=cloud-agents).

Privacy Mode (Legacy) is not supported. Cloud Agents require temporary
code storage while running.

#### Display Agent Summary

Display agent summaries and diff images. May contain file paths or code snippets. Can be turned On/Off.

#### Display Agent Summary in External Channels

For Slack Connect with other workspaces or channels with external members like Guests, choose to display agent summaries in external channels.

## Permissions

Cursor requests these Slack permissions for Cloud Agents to work within your workspace:

| Permission          | Description                                                                         |
| :------------------ | :---------------------------------------------------------------------------------- |
| `app_mentions:read` | Detects @mentions to start Cloud Agents and respond to requests                     |
| `channels:history`  | Reads previous messages in threads for context when adding follow-up instructions   |
| `channels:join`     | Automatically joins public channels when invited or requested                       |
| `channels:read`     | Accesses channel metadata (IDs and names) to post replies and updates               |
| `chat:write`        | Sends status updates, completion notifications, and PR links when agents finish     |
| `files:read`        | Downloads shared files (logs, screenshots, code samples) for additional context     |
| `files:write`       | Uploads visual summaries of agent changes for quick review                          |
| `groups:history`    | Reads previous messages in private channels for context in multi-turn conversations |
| `groups:read`       | Accesses private channel metadata to post responses and maintain conversation flow  |
| `im:history`        | Accesses direct message history for context in continued conversations              |
| `im:read`           | Reads DM metadata to identify participants and maintain proper threading            |
| `im:write`          | Initiates direct messages for private notifications or individual communication     |
| `mpim:history`      | Accesses group DM history for multi-participant conversations                       |
| `mpim:read`         | Reads group DM metadata to address participants and ensure proper delivery          |
| `reactions:read`    | Observes emoji reactions for user feedback and status signals                       |
| `reactions:write`   | Adds emoji reactions to mark status - ⏳ for running, ✅ for completed, ❌ for failed  |
| `team:read`         | Identifies workspace details to separate installations and apply settings           |
| `users:read`        | Matches Slack users with Cursor accounts for permissions and secure access          |

## Disclaimer

Cursor can make mistakes. Please double-check code and responses.

## Privacy Policy

For information about how Cursor collects, uses, and protects your data, see our [Privacy Policy](https://cursor.com/privacy).


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/models.md
# INDEX: 101/114
================================================================================

# Models

Cursor supports all frontier coding models from all major model providers.

| Model                                                                                         | Provider  | Default context | Max mode | Capabilities            | Notes                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------- | --------- | --------------- | -------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Claude 4 Sonnet](https://www.anthropic.com/claude/sonnet)                                    | Anthropic | 200k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Claude 4 Sonnet 1M](https://www.anthropic.com/claude/sonnet)                                 | Anthropic | -               | 1M       | Agent, Thinking, Images | Hidden by default; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                        |
| [Claude 4.5 Haiku](https://www.anthropic.com/claude/haiku)                                    | Anthropic | 200k            | -        | Thinking, Images        | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x                                                                                                                                                                                                                                         |
| [Claude 4.5 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | 200k            | 200k     | Agent, Thinking, Images | Hidden by default; Thinking variant counts as 2 requests in legacy pricing                                                                                                                                                                                                                                                                    |
| [Claude 4.5 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | 200k            | 1M       | Agent, Thinking, Images | Hidden by default; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                          |
| [Claude 4.6 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | 200k            | 1M       | Agent, Thinking, Images | The cost is about 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                       |
| [Claude 4.6 Opus (Fast mode)](https://www.anthropic.com/claude/opus)                          | Anthropic | 200k            | 1M       | Agent, Thinking, Images | Hidden by default; Limited research preview; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                |
| [Claude 4.6 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | 200k            | 1M       | Agent, Thinking, Images | The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                             |
| [Composer 1](https://cursor.com)                                                              | Cursor    | 200k            | -        | Agent, Images           | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Composer 1.5](https://cursor.com)                                                            | Cursor    | 200k            | -        | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 2.5 Flash](https://developers.googleblog.com/en/start-building-with-gemini-25-flash/) | Google    | 200k            | 1M       | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Flash](https://ai.google.dev/gemini-api/docs)                                       | Google    | 200k            | 1M       | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro](https://ai.google.dev/gemini-api/docs)                                         | Google    | 200k            | 1M       | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro Image Preview](https://ai.google.dev/gemini-api/docs)                           | Google    | 200k            | 1M       | Images                  | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (\~$0.134 per 1K/2K image, \~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| [Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs)                                       | Google    | 200k            | 1M       | Agent, Thinking, Images | -                                                                                                                                                                                                                                                                                                                                             |
| [GPT-5](https://openai.com/index/gpt-5/)                                                      | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high                                                                                                                                                                                                                                       |
| [GPT-5 Fast](https://openai.com/index/gpt-5/)                                                 | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast                                                                                                                                                                                                                         |
| [GPT-5 Mini](https://openai.com/index/gpt-5/)                                                 | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5-Codex](https://platform.openai.com/docs/models/gpt-5-codex)                            | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex Max](https://platform.openai.com/docs/models/gpt-5-codex)                      | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5.1 Codex Mini](https://platform.openai.com/docs/models/gpt-5-codex)                     | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex                                                                                                                                                                                                                                               |
| [GPT-5.2](https://openai.com/index/gpt-5/)                                                    | OpenAI    | 272k            | -        | Agent, Thinking, Images | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high                                                                                                                                                                                                                                                        |
| [GPT-5.2 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.3 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | 272k            | -        | Agent, Thinking, Images | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high                                                                                                                                                                                                                                                  |
| [Grok Code](https://docs.x.ai/docs/models#models-and-pricing)                                 | xAI       | 256k            | -        | Agent, Thinking         | -                                                                                                                                                                                                                                                                                                                                             |
| Kimi K2.5                                                                                     | Moonshot  | 262k            | -        | Agent, Thinking, Images | Hidden by default                                                                                                                                                                                                                                                                                                                             |

## Model pricing

Cursor [plans](https://cursor.com/docs/account/pricing.md) include usage at the model API rates. For example, $20 of included usage on the Pro plan will be consumed based on your model selection and its price.

Usage limits are shown in editor based on your current consumption. All prices are per million tokens.

| Model                                                                                         | Provider  | Input | Cache write | Cache read | Output | Notes                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------- | --------- | ----- | ----------- | ---------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Claude 4 Sonnet](https://www.anthropic.com/claude/sonnet)                                    | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Claude 4 Sonnet 1M](https://www.anthropic.com/claude/sonnet)                                 | Anthropic | $6    | $7.5        | $0.6       | $22.5  | Hidden by default; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                        |
| [Claude 4.5 Haiku](https://www.anthropic.com/claude/haiku)                                    | Anthropic | $1    | $1.25       | $0.1       | $5     | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x                                                                                                                                                                                                                                         |
| [Claude 4.5 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | Hidden by default; Thinking variant counts as 2 requests in legacy pricing                                                                                                                                                                                                                                                                    |
| [Claude 4.5 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                          |
| [Claude 4.6 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | The cost is about 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                       |
| [Claude 4.6 Opus (Fast mode)](https://www.anthropic.com/claude/opus)                          | Anthropic | $30   | $37.5       | $3         | $150   | Hidden by default; Limited research preview; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                |
| [Claude 4.6 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                             |
| [Composer 1](https://cursor.com)                                                              | Cursor    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Composer 1.5](https://cursor.com)                                                            | Cursor    | $3.5  | -           | $0.35      | $17.5  | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 2.5 Flash](https://developers.googleblog.com/en/start-building-with-gemini-25-flash/) | Google    | $0.3  | -           | $0.03      | $2.5   | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Flash](https://ai.google.dev/gemini-api/docs)                                       | Google    | $0.5  | -           | $0.05      | $3     | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro](https://ai.google.dev/gemini-api/docs)                                         | Google    | $2    | -           | $0.2       | $12    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro Image Preview](https://ai.google.dev/gemini-api/docs)                           | Google    | $2    | -           | $0.2       | $12    | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (\~$0.134 per 1K/2K image, \~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| [Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs)                                       | Google    | $2    | -           | $0.2       | $12    | -                                                                                                                                                                                                                                                                                                                                             |
| [GPT-5](https://openai.com/index/gpt-5/)                                                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high                                                                                                                                                                                                                                       |
| [GPT-5 Fast](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $2.5  | -           | $0.25      | $20    | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast                                                                                                                                                                                                                         |
| [GPT-5 Mini](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5-Codex](https://platform.openai.com/docs/models/gpt-5-codex)                            | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex Max](https://platform.openai.com/docs/models/gpt-5-codex)                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5.1 Codex Mini](https://platform.openai.com/docs/models/gpt-5-codex)                     | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex                                                                                                                                                                                                                                               |
| [GPT-5.2](https://openai.com/index/gpt-5/)                                                    | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high                                                                                                                                                                                                                                                        |
| [GPT-5.2 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.3 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high                                                                                                                                                                                                                                                  |
| [Grok Code](https://docs.x.ai/docs/models#models-and-pricing)                                 | xAI       | $0.2  | -           | $0.02      | $1.5   | -                                                                                                                                                                                                                                                                                                                                             |
| Kimi K2.5                                                                                     | Moonshot  | $0.6  | -           | $0.1       | $3     | Hidden by default                                                                                                                                                                                                                                                                                                                             |

These prices are from the model's API documentation:

- [OpenAI Pricing](https://openai.com/api/pricing/)
- [Anthropic Pricing](https://www.anthropic.com/pricing#api)
- [Google Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [xAI Pricing](https://docs.x.ai/docs/models)

## Auto

Enabling Auto allows Cursor to select the model best fit for the immediate task and with the highest reliability based on current demand. This feature can detect degraded output performance and automatically switch models to resolve it.

Auto consumes usage at the following API rates:

- **Input + Cache Write**: $1.25 per 1M tokens
- **Output**: $6.00 per 1M tokens
- **Cache Read**: $0.25 per 1M tokens

Both the editor and dashboard will show your usage, which includes Auto. If you prefer to select a model directly, usage is incurred at that model's list API price.

## Context windows

A [context window](https://cursor.com/learn/context.md) is the maximum span of tokens (text and code) an LLM can consider at once, including both the input prompt and output generated by the model.

Each chat in Cursor maintains its own context window. The more prompts, attached files, and responses included in a session, the more context is added, filling up the available context window.

Learn more about [working with context](https://cursor.com/learn/context.md) in Cursor.

## Max Mode

Max Mode extends the context window to the maximum a model supports. More context gives models deeper understanding of your codebase, leading to better results on complex tasks. The models table above shows each model's maximum context size.

Max Mode uses token-based pricing at the model's API rate plus a 20% upcharge. Learn more about [Max Mode](https://cursor.com/docs/context/max-mode.md).

## FAQ

### Where are models hosted?

Models are hosted on US, Canada, & Iceland based infrastructure by the model's provider, a trusted partner, or Cursor directly.

When Privacy Mode is enabled, neither Cursor nor model providers store your data. All data is deleted after each request. For details see our [Privacy Policy](https://cursor.com/privacy) and [Security](https://cursor.com/security) pages.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/plugins.md
# INDEX: 102/114
================================================================================

# Plugins

Plugins package rules, skills, agents, commands, MCP servers, and hooks into distributable bundles. They work across the IDE, CLI, and Cloud. Browse community-built plugins or [build your own](https://cursor.com/docs/plugins/building.md) to share with other developers.

## What plugins contain

A plugin can bundle any combination of these components:

| Component       | Description                                                |
| :-------------- | :--------------------------------------------------------- |
| **Rules**       | Persistent AI guidance and coding standards (`.mdc` files) |
| **Skills**      | Specialized agent capabilities for complex tasks           |
| **Agents**      | Custom agent configurations and prompts                    |
| **Commands**    | Agent-executable command files                             |
| **MCP Servers** | Model Context Protocol integrations                        |
| **Hooks**       | Automation scripts triggered by events                     |

## The marketplace

The [Cursor Marketplace](https://cursor.com/marketplace) is where you discover and install plugins. Plugins are distributed as Git repositories and submitted through the Cursor team. Every plugin is [manually reviewed](https://cursor.com/docs/plugins/security.md) before it's listed. Browse available plugins at [cursor.com/marketplace](https://cursor.com/marketplace) or search by keyword in the marketplace panel.

## Installing plugins

Install plugins from the marketplace. Plugins can be scoped to a project or installed at the user level.

### MCP deeplinks

Share MCP server configurations using install links:

```text
cursor://anysphere.cursor-deeplink/mcp/install?name=$NAME&config=$BASE64_ENCODED_CONFIG
```

See [MCP install links](https://cursor.com/docs/context/mcp/install-links.md) for details on generating these links.

## Managing installed plugins

### MCP servers

Toggle MCP servers on or off from Cursor Settings:

1. Open Settings (Cmd+Shift+J)
2. Go to **Features** > **Model Context Protocol**
3. Click the toggle next to any server

Disabled servers won't load or appear in chat.

### Rules and skills

Manage rules and skills from the Rules section of Cursor Settings. Toggle individual rules between **Always**, **Agent Decides**, and **Manual** modes. Skills appear in the **Agent Decides** section and can be invoked manually with `/skill-name` in chat.

## FAQ

### Are marketplace plugins reviewed for security?

Yes. Every plugin is manually reviewed before it's listed. All plugins must be open source, and we review each update before publishing. See [Marketplace Security](https://cursor.com/docs/plugins/security.md) for details on vetting, update reviews, and how to report issues.

### How do I create a plugin?

Create a directory with a `.cursor-plugin/plugin.json` manifest file, add your rules, skills, agents, commands, or other components, and submit it to the Cursor team. See [Building Plugins](https://cursor.com/docs/plugins/building.md) for the full guide.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/plugins/building.md
# INDEX: 103/114
================================================================================

# Building plugins

Cursor plugins let you package and distribute rules, skills, agents, commands, MCP servers, and hooks. Once installed, plugins work across all Cursor surfaces: the IDE, CLI, and Cloud.

If you're starting from scratch, use the [plugin template repository](https://github.com/cursor/plugin-template). It includes the required layout and starter files.

## Plugin structure

A plugin is a directory with a manifest file and your plugin assets:

```text
my-plugin/
├── .cursor-plugin/
│   └── plugin.json        # Required: plugin manifest
├── rules/                 # Cursor rules (.mdc files)
│   ├── coding-standards.mdc
│   └── review-checklist.mdc
├── skills/                # Agent skills
│   └── code-reviewer/
│       └── SKILL.md
├── agents/                # Custom agent configurations
│   └── security-reviewer.md
├── commands/              # Agent-executable commands
│   └── deploy.md
├── hooks/                 # Hook definitions
│   └── hooks.json
├── .mcp.json              # MCP server definitions
├── assets/                # Logos and static assets
│   └── logo.svg
├── scripts/               # Hook and utility scripts
│   └── format-code.py
└── README.md
```

## Plugin manifest

Every plugin requires a `.cursor-plugin/plugin.json` manifest file.

### Required fields

| Field  | Type   | Description                                                                                                                                                              |
| :----- | :----- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name` | string | Plugin identifier. Lowercase, kebab-case (alphanumerics, hyphens, and periods). Must start and end with an alphanumeric character. Examples: `my-plugin`, `prompts.chat` |

### Optional fields

| Field         | Type                     | Description                                                                                                                                                                                                          |
| :------------ | :----------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `description` | string                   | Brief plugin description                                                                                                                                                                                             |
| `version`     | string                   | Semantic version (e.g., `1.0.0`)                                                                                                                                                                                     |
| `author`      | object                   | Author info: `name` (required), `email` (optional)                                                                                                                                                                   |
| `homepage`    | string                   | URL to plugin homepage                                                                                                                                                                                               |
| `repository`  | string                   | URL to plugin repository                                                                                                                                                                                             |
| `license`     | string                   | License identifier (e.g., `MIT`)                                                                                                                                                                                     |
| `keywords`    | array                    | Tags for discovery and categorization                                                                                                                                                                                |
| `logo`        | string                   | Relative path to a logo file in the repo (e.g., `assets/logo.svg`), or an absolute URL. Relative paths resolve to `raw.githubusercontent.com` URLs. Preferred: commit the logo to your repo and use a relative path. |
| `rules`       | string or array          | Path(s) to rule files or directories                                                                                                                                                                                 |
| `agents`      | string or array          | Path(s) to agent files or directories                                                                                                                                                                                |
| `skills`      | string or array          | Path(s) to skill directories                                                                                                                                                                                         |
| `commands`    | string or array          | Path(s) to command files or directories                                                                                                                                                                              |
| `hooks`       | string or object         | Path to hooks config file, or inline hook config                                                                                                                                                                     |
| `mcpServers`  | string, object, or array | Path to MCP config file, inline MCP server config, or an array of either. Overrides default `.mcp.json` discovery.                                                                                                   |

### Example manifest

```json
{
  "name": "enterprise-plugin",
  "version": "1.2.0",
  "description": "Enterprise development tools with security scanning and compliance checks",
  "author": {
    "name": "ACME DevTools",
    "email": "devtools@acme.com"
  },
  "keywords": ["enterprise", "security", "compliance"],
  "logo": "assets/logo.svg"
}
```

## Component discovery

When the manifest does not specify explicit paths for a component type, the parser uses **automatic folder-based discovery**:

| Component   | Default location          | How it's discovered                                                                        |
| :---------- | :------------------------ | :----------------------------------------------------------------------------------------- |
| Skills      | `skills/`                 | Each subdirectory containing a `SKILL.md` file                                             |
| Rules       | `rules/`                  | All `.md`, `.mdc`, or `.markdown` files                                                    |
| Agents      | `agents/`                 | All `.md`, `.mdc`, or `.markdown` files                                                    |
| Commands    | `commands/`               | All `.md`, `.mdc`, `.markdown`, or `.txt` files                                            |
| Hooks       | `hooks/hooks.json`        | Parsed for hook event names                                                                |
| MCP Servers | `.mcp.json`               | Parsed for server entries                                                                  |
| Root Skill  | `SKILL.md` at plugin root | Treated as a single-skill plugin (only if no `skills/` dir and no manifest `skills` field) |

If a manifest field **is** specified (e.g., `"skills": "./my-skills/"`), it **replaces** folder discovery for that component. The default folder is not also scanned.

## Writing rules

Rules are `.mdc` files providing persistent guidance to the AI. Place them in the `rules/` directory.

Rules require YAML frontmatter with metadata:

```markdown title="rules/prefer-const.mdc"
---
description: Prefer const over let for variables that are never reassigned
alwaysApply: true
---

prefer-const: Always use `const` for variables that are never reassigned.
Only use `let` when the variable needs to be reassigned. Never use `var`.
```

### Rule frontmatter fields

| Field         | Type            | Description                                                                     |
| :------------ | :-------------- | :------------------------------------------------------------------------------ |
| `description` | string          | Brief description of what the rule does                                         |
| `alwaysApply` | boolean         | If `true`, rule applies to all files. If `false`, rule is available on request. |
| `globs`       | string or array | File patterns the rule applies to (e.g., `"**/*.ts"`)                           |

Use `/create-rule` in the Cursor agent to generate rules with proper frontmatter.

For full documentation, see [Rules](https://cursor.com/docs/context/rules.md).

## Writing skills

Skills are specialized capabilities defined in `SKILL.md` files. Each skill lives in its own directory under `skills/`.

Skills require YAML frontmatter with metadata:

```markdown title="skills/api-designer/SKILL.md"
---
name: api-designer
description: Design RESTful APIs following OpenAPI 3.0 specification.
  Use when designing new API endpoints, reviewing API contracts,
  or generating API documentation.
---

# API Designer Skill

## When to use

- Designing new API endpoints
- Reviewing API contracts
- Generating API documentation

## Instructions

1. Follow REST conventions for resource naming
2. Use appropriate HTTP methods (GET, POST, PUT, DELETE, PATCH)
3. Include proper error responses with standard HTTP status codes
4. Document all endpoints with OpenAPI 3.0 specification
5. Use consistent naming conventions (kebab-case for URLs, camelCase for JSON)
```

### Skill frontmatter fields

| Field         | Type   | Description                                           |
| :------------ | :----- | :---------------------------------------------------- |
| `name`        | string | Skill identifier (lowercase, kebab-case)              |
| `description` | string | Description of what the skill does and when to use it |

Use `/create-skill` in the Cursor agent to generate skills with proper frontmatter.

For full documentation, see [Agent Skills](https://cursor.com/docs/context/skills.md).

## Writing agents

Agents are markdown files defining custom agent behaviors and prompts. Place them in the `agents/` directory.

Agents require YAML frontmatter with metadata:

```markdown title="agents/security-reviewer.md"
---
name: security-reviewer
description: Security-focused code reviewer that checks for
  vulnerabilities and proven approaches
---

# Security Reviewer

You are a security-focused code reviewer. When reviewing code:

1. Check for injection vulnerabilities (SQL, XSS, command injection)
2. Verify proper authentication and authorization
3. Look for sensitive data exposure (API keys, passwords, PII)
4. Ensure secure cryptographic practices
5. Review dependency security and known vulnerabilities
6. Check for proper input validation and sanitization
```

### Agent frontmatter fields

| Field         | Type   | Description                              |
| :------------ | :----- | :--------------------------------------- |
| `name`        | string | Agent identifier (lowercase, kebab-case) |
| `description` | string | Brief description of the agent's purpose |

Use `/create-agent` in the Cursor agent to generate agents with proper frontmatter.

## Writing commands

Commands are markdown or text files defining agent-executable actions. Place them in the `commands/` directory.

Commands support `.md`, `.mdc`, `.markdown`, and `.txt` extensions. They can include YAML frontmatter:

```markdown title="commands/deploy-staging.md"
---
name: deploy-staging
description: Deploy the current branch to the staging environment
---

# Deploy to staging

Steps to deploy to staging:
1. Run tests
2. Build the project
3. Push to staging branch
```

### Command frontmatter fields

| Field         | Type   | Description                                |
| :------------ | :----- | :----------------------------------------- |
| `name`        | string | Command identifier (lowercase, kebab-case) |
| `description` | string | Brief description of what the command does |

## Writing hooks

Hooks are automation scripts triggered by agent events. Define them in `hooks/hooks.json`:

```json title="hooks/hooks.json"
{
  "hooks": {
    "afterFileEdit": [
      {
        "command": "./scripts/format-code.sh"
      }
    ],
    "beforeShellExecution": [
      {
        "command": "./scripts/validate-shell.sh",
        "matcher": "rm|curl|wget"
      }
    ],
    "sessionEnd": [
      {
        "command": "./scripts/audit.sh"
      }
    ]
  }
}
```

**Available hook events:**

- **Agent hooks**: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `subagentStart`, `subagentStop`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`
- **Tab hooks**: `beforeTabFileRead`, `afterTabFileEdit`

For full documentation, see [Hooks](https://cursor.com/docs/agent/hooks.md).

## MCP servers

The `.mcp.json` file at the plugin root is detected automatically. You only need to specify the `mcpServers` field in `plugin.json` if using a custom path or inline config.

The MCP config file should contain server entries under a `mcpServers` key:

```json title=".mcp.json"
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "${POSTGRES_URL}"
      }
    }
  }
}
```

For full documentation, see [Model Context Protocol (MCP)](https://cursor.com/docs/context/mcp.md).

## Logos

Commit logos to your repository and reference them using a relative path:

```json
{
  "name": "my-plugin",
  "logo": "assets/logo.svg"
}
```

Relative paths resolve to `raw.githubusercontent.com` URLs based on the repository and commit SHA. For example, `assets/logo.svg` in the `acme/plugins` repo at commit `abc123` resolves to:

```text
https://raw.githubusercontent.com/acme/plugins/abc123/my-plugin/assets/logo.svg
```

Absolute GitHub user content URLs (starting with `http://` or `https://`) are also accepted.

## Multi-plugin repositories

A single Git repository can contain multiple plugins using a **marketplace manifest**. Place it at `.cursor-plugin/marketplace.json` in the repository root.

### Marketplace manifest format

```json
{
  "name": "my-marketplace",
  "owner": {
    "name": "Your Org",
    "email": "plugins@yourorg.com"
  },
  "metadata": {
    "description": "A collection of developer tool plugins"
  },
  "plugins": [
    {
      "name": "plugin-one",
      "source": "plugin-one",
      "description": "First plugin"
    },
    {
      "name": "plugin-two",
      "source": "plugin-two",
      "description": "Second plugin"
    }
  ]
}
```

### Marketplace fields

| Field      | Type   | Description                                                                           |
| :--------- | :----- | :------------------------------------------------------------------------------------ |
| `name`     | string | **(required)** Marketplace identifier (kebab-case)                                    |
| `owner`    | object | **(required)** `name` (required), `email` (optional)                                  |
| `plugins`  | array  | **(required)** Array of plugin entries (max 500)                                      |
| `metadata` | object | Optional. `description`, `version`, `pluginRoot` (prefix path for all plugin sources) |

### Plugin entry fields

Each entry in the `plugins` array supports:

| Field                                   | Type             | Description                                                 |
| :-------------------------------------- | :--------------- | :---------------------------------------------------------- |
| `name`                                  | string           | **(required)** Plugin identifier (kebab-case)               |
| `source`                                | string or object | Path to plugin directory, or object with `path` and options |
| `description`                           | string           | Plugin description                                          |
| `version`                               | string           | Semantic version                                            |
| `author`                                | object           | Author info                                                 |
| `homepage`                              | string           | URL                                                         |
| `repository`                            | string           | URL                                                         |
| `license`                               | string           | License identifier                                          |
| `keywords`                              | array            | Search tags                                                 |
| `logo`                                  | string           | Relative path or URL to logo                                |
| `category`                              | string           | Plugin category                                             |
| `tags`                                  | array            | Additional tags                                             |
| `skills`, `rules`, `agents`, `commands` | string or array  | Path(s) to component files                                  |
| `hooks`                                 | string or object | Path to hooks config or inline config                       |
| `mcpServers`                            | string or object | Path to MCP config or inline config                         |

### How resolution works

For a marketplace entry with `"source": "my-plugin"`:

1. The parser looks for `my-plugin/.cursor-plugin/plugin.json`
2. If found, the per-plugin manifest is merged with the marketplace entry (manifest values take precedence)
3. Component discovery runs within the `my-plugin/` directory, using manifest paths if specified or folder-based discovery as fallback

### Example multi-plugin repo

```text
my-plugins/
├── .cursor-plugin/
│   └── marketplace.json       # Lists all plugins
├── eslint-rules/
│   ├── .cursor-plugin/
│   │   └── plugin.json        # Per-plugin manifest
│   └── rules/
│       ├── prefer-const.mdc
│       └── no-any.mdc
├── docker/
│   ├── .cursor-plugin/
│   │   └── plugin.json
│   ├── skills/
│   │   ├── containerize-app/
│   │   │   └── SKILL.md
│   │   └── setup-docker-compose/
│   │       └── SKILL.md
│   └── .mcp.json
└── README.md
```

## Plugin examples

### Rules-only plugin

```text
eslint-rules/
├── .cursor-plugin/
│   └── plugin.json
└── rules/
    ├── prefer-const.mdc
    ├── no-any.mdc
    └── error-handling.mdc
```

```json title="plugin.json"
{
  "name": "eslint-rules",
  "description": "ESLint-inspired coding rules for TypeScript",
  "author": { "name": "Your Name" },
  "keywords": ["eslint", "typescript", "linting"]
}
```

### Skills plugin

```text
code-review-skills/
├── .cursor-plugin/
│   └── plugin.json
└── skills/
    ├── security-review/
    │   └── SKILL.md
    └── performance-audit/
        ├── SKILL.md
        └── scripts/
            └── analyze.py
```

```json title="plugin.json"
{
  "name": "code-review-skills",
  "description": "Advanced code review skills for security and performance",
  "author": { "name": "Your Name" },
  "keywords": ["code-review", "security", "performance"]
}
```

### MCP-only plugin

```text
database-mcp/
├── .cursor-plugin/
│   └── plugin.json
└── .mcp.json
```

```json title="plugin.json"
{
  "name": "database-mcp",
  "description": "MCP servers for database interactions",
  "author": { "name": "Your Name" }
}
```

### Full-featured plugin

```text
enterprise-toolkit/
├── .cursor-plugin/
│   └── plugin.json
├── assets/
│   └── logo.svg
├── rules/
│   ├── security-standards.mdc
│   └── code-style.mdc
├── skills/
│   └── compliance-check/
│       └── SKILL.md
├── agents/
│   ├── security-reviewer.md
│   ├── performance-tester.md
│   └── compliance-checker.md
├── commands/
│   └── run-compliance-scan.md
├── hooks/
│   └── hooks.json
├── .mcp.json
├── scripts/
│   ├── security-scan.sh
│   └── format-code.py
└── README.md
```

```json title="plugin.json"
{
  "name": "enterprise-toolkit",
  "version": "2.0.0",
  "description": "Complete enterprise development toolkit with security, compliance, and automation",
  "author": {
    "name": "ACME DevTools",
    "email": "devtools@acme.com"
  },
  "keywords": ["enterprise", "security", "compliance"],
  "logo": "assets/logo.svg"
}
```

## Submitting your plugin

Plugins are reviewed by the Cursor team to maintain a high quality bar. To submit a plugin:

### Create your plugin

Follow this guide's structure. Make sure your plugin has a valid `.cursor-plugin/plugin.json` manifest.

### Host in a Git repository

Push your plugin to a public Git repository. Commit your logo to the repo (optional but recommended).

### Submit your plugin

Go to [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) and submit your repository link.

The team will review your submission and publish it to the [marketplace](https://cursor.com/marketplace).

### Submission checklist

- Plugin has a valid `.cursor-plugin/plugin.json` manifest
- `name` is unique, lowercase, kebab-case (e.g., `my-awesome-plugin`)
- `description` clearly explains the plugin's purpose
- All rules, skills, agents, and commands have proper frontmatter metadata
- Logo is committed to the repo and referenced by relative path (if provided)
- `README.md` documents usage and any configuration
- All paths in manifest are relative and valid (no `..`, no absolute paths)
- Plugin has been tested locally
- For multi-plugin repos: `.cursor-plugin/marketplace.json` is at the repo root with unique plugin names

## Guidelines

1. **Keep plugins focused.** Do one thing well rather than bundling unrelated features.
2. **Document thoroughly.** Include a clear README with usage examples.
3. **Use semantic versioning.** Follow semver for version numbers.
4. **Add proper frontmatter.** All rules, skills, agents, and commands need metadata.
5. **Test locally first.** Verify your plugin works before submitting.
6. **Use descriptive keywords.** Help users discover your plugin.
7. **Commit your logo.** Push an SVG to the repo and reference it by path.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/plugins/security.md
# INDEX: 104/114
================================================================================

# Marketplace security

Every plugin in the [Cursor Marketplace](https://cursor.com/marketplace) is manually reviewed by our team before it's listed. We work exclusively with a small group of trusted partners, and we review each plugin for security, data handling, and quality before it goes live.

## What risk does installing a plugin carry?

Plugins are lightweight by design. They're largely markdown files and supporting files for skills, such as templates and scripts. No binaries are shipped.

Plugins respect your MCP allowlist and blocklist, so they can only access the tools and servers you've explicitly permitted. If a plugin contains a blocked MCP server, the plugin installs normally but the blocked server cannot make calls. Existing MCP governance policies carry over to plugins without additional configuration.

That said, plugins are third-party software, and installation is at the discretion and risk of the installing user. Since all plugins are open source, we recommend reviewing a plugin's source code before installing.

## Are plugins open source?

Yes. All marketplace plugins must be open source. You can inspect the code yourself, and so can the broader community.

## Are plugin updates reviewed?

Yes. Plugins in the marketplace are not automatically updated from source code. We manually review every plugin update, so nothing gets into the marketplace without our explicit approval.

## What happens if a security issue is found in a plugin?

We take a proactive approach. If we determine that a plugin poses a risk to users, whether through our own review, community reports, or ongoing monitoring, we remove it from the marketplace immediately while the issue is being resolved.

## Are plugin authors required to maintain their plugins?

Yes. Plugin authors are expected to respond to and resolve reported security or stability issues. Authors who don't meet this standard risk losing their good standing in the marketplace, which may result in their plugins being delisted.

## How do I report a plugin issue?

If you discover a security concern or other issue with a marketplace plugin, report it to [security-reports@cursor.com](mailto:security-reports@cursor.com). We take all reports seriously and follow up promptly.

## How do you decide which plugins to list?

We keep the marketplace curated. We work directly with plugin authors we trust, and every submission goes through our internal review process. As we mature our vetting standards, we plan to open this up more broadly.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/settings/api-keys.md
# INDEX: 105/114
================================================================================

# API Keys

Use your own API keys to send unlimited AI messages at your own cost. When configured, Cursor will use your API keys to call LLM providers directly.

To use your API key, go to `Cursor Settings` > `Models` and enter your API keys. Click **Verify**. Once validated, your API key is enabled.

Custom API keys only work with standard chat models. Features requiring
specialized models (like Tab Completion) will continue using Cursor's built-in
models.

Cursor's [Zero Data Retention policy](https://cursor.com/docs/account/teams/dashboard.md#privacy-settings) does not apply when using your own API keys. Your data handling will be subject to the privacy policies of your chosen AI provider (OpenAI, Anthropic, Google, Azure, or AWS).

## Supported providers

- **OpenAI** - Standard, non-reasoning chat models only. The model picker will show the OpenAI models available.
- **Anthropic** - All Claude models available through the Anthropic API.
- **Google** - Gemini models available through the Google AI API.
- **Azure OpenAI** - Models deployed in your Azure OpenAI Service instance.
- **[AWS Bedrock](https://cursor.com/docs/settings/aws-bedrock.md)** - Use AWS access keys, secret keys, or IAM roles. Works with models available in your Bedrock configuration. See the [AWS Bedrock setup guide](https://cursor.com/docs/settings/aws-bedrock.md) for detailed configuration instructions.

## FAQ

### Will my API key be stored or leave my device?

Your API key won't be stored but is sent to our server with every request.
All requests are routed through our backend for final prompt building.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/settings/aws-bedrock.md
# INDEX: 106/114
================================================================================

# AWS Bedrock

Route AI requests through your AWS Bedrock account instead of Cursor's model providers. This lets your team use existing AWS credits and keep requests within your AWS infrastructure.

![AWS Bedrock settings in Cursor](/docs-static/images/settings/aws-bedrock-settings.png)

## IAM role setup (recommended)

The recommended approach is to create an IAM role that grants Cursor permission to invoke Bedrock models on your behalf.

### Step 1: Create the IAM role

Create a new IAM role with the following trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::289469326074:role/roleAssumer"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "<your-external-id>"
        }
      }
    }
  ]
}
```

Replace `<your-external-id>` with the External ID shown in your Cursor settings. This ID is generated after you first validate your Bedrock configuration and prevents the [confused deputy problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html).

### Step 2: Attach permissions

Attach a policy that grants access to the Bedrock models you want to use:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.*",
        "arn:aws:bedrock:*::foundation-model/us.anthropic.*"
      ]
    }
  ]
}
```

Adjust the resource ARNs to match the specific models and regions you want to allow.

### Step 3: Enable models in Bedrock

Before using a model, you must enable it in the AWS Bedrock console:

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Select the models you want to use
5. Click **Save changes**

### Step 4: Configure in Cursor

1. Go to `Cursor Settings` > `Models`
2. Find the **Bedrock IAM Role** section
3. Enter your credentials:

| Setting              | Description                                                                  |
| -------------------- | ---------------------------------------------------------------------------- |
| **AWS IAM Role ARN** | Your IAM role ARN (e.g., `arn:aws:iam::123456789012:role/CursorBedrockRole`) |
| **AWS Region**       | The AWS region where Bedrock is enabled (e.g., `us-east-1`)                  |
| **Test Model ID**    | A model to test connectivity                                                 |

4. Click **Validate & Save** to test the connection

## External ID

After validating your Bedrock configuration, Cursor generates a unique External ID. Add this to your IAM role's trust policy under the `Condition` section to enable secure cross-account access.

The External ID prevents unauthorized access to your AWS resources. Copy the ID from your Cursor settings and update your trust policy accordingly.

## Using access keys

Alternatively, you can use AWS access keys instead of an IAM role. Enter your AWS Access Key ID and Secret Access Key in the Cursor settings. This approach is simpler but less secure than using IAM roles.

## Troubleshooting

### Validation fails with access denied

- Verify the IAM role ARN is correct
- Check that the trust policy includes Cursor's cross-account ARN (`arn:aws:iam::289469326074:role/roleAssumer`)
- Confirm the External ID matches exactly
- Ensure the test model is enabled in Bedrock

### Model not found

- Enable the model in the AWS Bedrock console
- Verify the model ID format matches your region (some use `us.anthropic.*` prefix)
- Check that your IAM policy includes the model's ARN

### Region errors

- Confirm Bedrock is available in your selected region
- Verify the model is enabled in that specific region
- Some models are only available in certain regions

## Related

- [API Keys](https://cursor.com/docs/settings/api-keys.md) - Configure other model providers
- [Models](https://cursor.com/docs/models.md) - Overview of available models in Cursor


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/shared-transcripts.md
# INDEX: 107/114
================================================================================

# Shared transcripts

Share your AI conversations with teammates or the public. Shared transcripts let you collaborate on solutions, document debugging sessions, or showcase how you solved a problem.

## What are shared transcripts?

Shared transcripts are read-only copies of your Cursor chat conversations that you can share via a link. Recipients can view the entire conversation including:

- All messages between you and the AI
- Code snippets and suggestions
- Tool calls and their results
- Context that was included

This makes it easy to share solutions, get feedback on approaches, or document how a problem was solved.

## How to share a chat

### From Cursor

1. Open the chat you want to share
2. Click the **Share** icon in the chat header (link icon)
3. Choose a visibility option:
   - **Team**: Only your team members can view
   - **Public**: Anyone with the link can view
4. Click **Copy Link** to copy the share URL

The share link is created when you open the share modal.

### Visibility options

| Visibility | Who can view                       | URL format                                          |
| ---------- | ---------------------------------- | --------------------------------------------------- |
| **Team**   | Team members with dashboard access | `cursor.com/dashboard?tab=shared-chats&shareId=...` |
| **Public** | Anyone with the link               | `cursor.com/s/abc123`                               |

Team visibility requires the viewer to be signed in and a member of your team. Public links can be shared anywhere, including social media, documentation, or Stack Overflow.

## Viewing shared transcripts

### From a public link

Click a public share link (e.g., `cursor.com/s/abc123`) to view the conversation directly in your browser. No sign-in required.

### From the dashboard

1. Go to **cursor.com/dashboard**
2. Click the **Shared Transcripts** tab
3. Use the tabs to filter:
   - **Team Chats**: All transcripts shared by your team
   - **My Chats**: Transcripts you've shared

Click any transcript to view the full conversation.

### Fork a shared chat

Want to continue a conversation from a shared transcript? You can **fork** it:

1. Open the shared transcript
2. Click **Fork to Cursor** (or use **Open in Cursor**)
3. The conversation opens in Cursor, ready for you to continue

You can also use the deeplink `cursor://fork-shared-chat/{shareId}` (replace `{shareId}` with the share ID from the URL) to open and fork a shared chat directly in Cursor.

Forking creates a copy. The original shared transcript remains unchanged.

## Managing shared transcripts

### Change visibility

You can change visibility after sharing:

1. Go to **Shared Transcripts** in the dashboard
2. Find the transcript
3. Click the visibility dropdown
4. Select **Team** or **Public**

### Delete a shared transcript

1. Go to **Shared Transcripts** in the dashboard
2. Find the transcript
3. Click the **...** menu
4. Select **Delete**

Deleting a share removes the link permanently. Anyone with the old link will see an error.

### Who can delete?

- **Your transcripts**: You can always delete your own
- **Team transcripts**: Team admins can delete any team member's transcript

## Privacy and security

### What gets shared

When you share a transcript, the full conversation is included:

- Your messages to the AI
- AI responses
- Code snippets
- Tool results (file reads, search results, etc.)
- File context that was attached

### What's not shared

- Your identity (only first name shown if viewing from dashboard)
- Your authentication tokens or API keys
- Files from your local machine (only content included in the chat)

### Automatic secret redaction

Cursor scans shared transcripts and redacts potential secrets:

- API keys
- Passwords
- Tokens
- Connection strings

This helps prevent accidental exposure, but always review before sharing sensitive conversations.

### Storage

Shared transcripts are stored securely:

- Encrypted at rest
- Stored separately from your Cursor account
- Subject to your team's data retention policies

## Requirements

### Plan requirements

Shared transcripts are available for:

- **Pro** users
- **Teams** users
- **Enterprise** users

Free and trial users cannot create shared transcripts.

| Plan              | Available | Visibility options                     |
| ----------------- | --------- | -------------------------------------- |
| Free / Free trial | No        | —                                      |
| **Pro**           | Yes       | Public only                            |
| **Teams**         | Yes       | Team + Public                          |
| **Enterprise**    | Yes       | Team only (public disabled by default) |

Pro users without a team can only share publicly. Teams and Enterprise teams can use team visibility; team admins configure which options are allowed. Enterprise teams have public sharing disabled by default for security.

### Privacy mode

Users with **Privacy Mode** set to "No Storage" cannot create shared transcripts. The feature requires storing conversation data.

### Team admin settings

Team admins can control sharing for their organization:

- **Enable/Disable**: Turn sharing on or off for the team
- **Allowed Visibilities**: Choose which visibility options are available (Team only, Public only, or both)

Configure these in **Dashboard > Settings > Team Settings**.

## Troubleshooting

### Share feature is only available for Pro, Teams, and Enterprise users

Upgrade to a paid plan to access shared transcripts.

### Share feature requires data storage

You have Privacy Mode set to "No Storage". Adjust your privacy settings in **Settings > Privacy** to enable sharing.

### Shared conversations are disabled for your team

Your team admin has disabled sharing. Contact them to enable it.

### No visibility options are available

Your team admin hasn't enabled any visibility options. Contact them to configure sharing settings.

### The share link doesn't work

The transcript may have been deleted by the creator. Share links are permanent until deleted.

### You have reached the daily limit of shares

You can create up to 50 shared transcripts per day. The limit resets daily. Try again tomorrow.

## Frequently asked questions

### Can I edit a shared transcript?

No, shared transcripts are read-only snapshots. To make changes, delete the share and create a new one.

### Do shared transcripts expire?

No, shared transcripts remain available until you delete them.

### Can I see who viewed my transcript?

View analytics are not currently available.

### What happens if I delete my account?

All your shared transcripts (where you're the creator) are deleted.

### Can I share a conversation with images?

Yes, images included in the conversation are preserved in the shared transcript.

### Is there a limit to how many transcripts I can share?

Yes. You can create up to 50 shared transcripts per day. The limit resets daily. Most users won't hit it with normal usage.

### Can I share Cloud Agent sessions?

Cloud Agent (Background Agent) sessions can be shared within your team using the share button in the agent header. Full public sharing for Cloud Agents is coming soon.

## Tips for sharing

**Give it a good title.** The default title comes from your conversation, but you can customize it when sharing.

**Review before sharing publicly.** Make sure no sensitive information is included.

- Use team sharing for internal discussions to keep work-in-progress solutions visible only to your team
- Fork before modifying. If you want to continue a shared conversation, fork it to preserve the original


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/tab/overview.md
# INDEX: 108/114
================================================================================

# Tab

Tab is a specialized Cursor model for autocompletion. The more you use it, the better it becomes as you inject intent by accepting Tab or rejecting Escape suggestions. With Tab, you can:

- Modify multiple lines at once
- Add import statements when missing
- Jump within and across files for coordinated edits
- Get suggestions based on recent changes, linter errors and accepted edits

[Media](/docs-static/images/tab/simple-tab.mp4)

## Suggestions

When adding text, completions appear as semi-opaque ghost text. When modifying existing code, it shows as a diff popup right of your current line.

![Tab inline suggestion](/docs-static/images/tab/tab-inline.png)

![Tab block suggestion](/docs-static/images/tab/tab-block.png)

Accept suggestions with Tab, reject with Escape, or accept word-by-word using Cmd+Arrow Right. Keep typing or press Escape to hide suggestions.

### Jump in file

Tab predicts your next editing location in the file and suggests jumps. After accepting an edit, press Tab again to jump to the next location.

![Jump in file](/docs-static/images/tab/jump-in-file.png)

### Jump across files

Tab predicts context-aware edits across files. A portal window appears at the bottom when a cross-file jump is suggested.

![Jump to file](/docs-static/images/tab/jump-to-file.png)

### Auto-import

In TypeScript and Python, Tab automatically adds import statements when missing. Use a method from another file and Tab suggests the import. Accepting adds it without disrupting your flow.

If auto-import isn't working:

- Ensure your project has the right language server or extensions
- Test with Cmd . to check if the import appears in *Quick Fix* suggestions

![Auto import](/docs-static/images/tab/auto-import.png)

### Tab in Peek

Tab works in *Go to Definition* or *Go to Type Definition* peek views. Useful for modifying function signatures and fixing call sites.

![Tab in Peek](/docs-static/images/tab/tab-in-peek.png)

In Vim, use with `gd` to jump to definitions, modify, and resolve references in one flow.

### Partial Accepts

Accept one word at a time with Cmd Right, or set your keybinding via `editor.action.inlineSuggest.acceptNextWord`. Enable in: `Cursor Settings` → `Tab`.

## Settings

| Setting                       | Description                                                                    |
| :---------------------------- | :----------------------------------------------------------------------------- |
| Cursor Tab                    | Context-aware, multi-line suggestions around your cursor based on recent edits |
| Partial Accepts               | Accept the next word of a suggestion via Cmd Right                             |
| Suggestions While Commenting  | Enable Tab inside comment blocks                                               |
| Whitespace-Only Suggestions   | Allow edits affecting only formatting                                          |
| Imports                       | Enable auto-import for TypeScript                                              |
| Auto Import for Python (beta) | Enable auto-import for Python projects                                         |

### Toggling

Use the status bar (bottom-right) to:

- **Snooze**: Temporarily disable Tab for a chosen duration
- **Disable globally**: Disable Tab for all files
- **Disable for extensions**: Disable Tab for specific file extensions (e.g., markdown or JSON)

## FAQ

### Tab gets in the way when writing comments, what can I do?

Disable Tab for comments by going to `Cursor Settings` → `Tab Completion` and unchecking **Trigger in comments**.

### Can I change the keyboard shortcut for Tab suggestions?

Remap accepting and rejecting suggestions to any key using `Accept Cursor Tab Suggestions` in `Keyboard Shortcuts` settings.

### How does Tab generate suggestions?

Cursor syncs recently edited files to our backend, where they are encrypted in-memory. Whenever we need to update that context or fetch a suggestion, we decrypt the contents in our backend. We use this synced context to produce suggestions.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/troubleshooting/common-issues.md
# INDEX: 109/114
================================================================================

# Common Issues

Below are common issues and their solutions.

### Networking Issues

First, check your network connectivity. Go to `Cursor Settings` > `Network` and click `Run Diagnostics`. This will test your connection to Cursor's servers and help identify any network-related issues that might be affecting AI features, updates, or other online functionality.

Cursor relies on HTTP/2 for AI features because it handles streamed responses efficiently. If your network doesn't support HTTP/2, you may experience indexing failures and AI feature issues.

This occurs on corporate networks, VPNs, or when using proxies like Zscaler.

To resolve this, go to `Cursor Settings` > `Network`, then set `HTTP Compatibility Mode` to `HTTP/1.1`. This forces HTTP/1.1 usage and resolves the issue.

We plan to add automatic detection and fallback.

### Resource Issues (CPU, RAM, etc.)

High CPU or RAM usage can slow your machine or trigger resource warnings.

While large codebases require more resources, high usage typically stems from extensions or settings issues.

If you are seeing a low RAM warning on **MacOS**, please note that there is a
bug for some users that can show wildly incorrect values. If you are seeing
this, please open the Activity Monitor and look at the "Memory" tab to see the
correct memory usage.

If you're experiencing high CPU or RAM usage, try these steps:

### Check Your Extensions

Extensions can impact performance.

The Extension Monitor shows resource consumption for all your installed and built-in extensions.

Enable the extension monitor from `Settings` > `Cursor Settings` > `Beta` and toggle `Extension RPC Tracer`. This will prompt you to restart Cursor.

Open it: `Cmd/Ctrl + Shift + P` → `Developer: Open Extension Logs Folder`.

Cursor runs your extensions in one or more **extension hosts**. Usually, most of your extensions will run in the same extension host, which means an extension consuming a lot of CPU time can suffocate its neighboring extensions!

The Extension Monitor will show:

- Every long-lived process launched by an extension (MacOS and Linux only).
- **% Ext Host**: The percentage of total extension host time consumed by this extension. Helps identify which extensions are using the most time relative to others.
- **Max Blocking**: An extensions's longest continuous block of execution, per monitoring interval.
- **% CPU**:
  - For extensions: The percentage of total CPU usage attributed to the extension's code.
  - For processes: The percentage of total CPU usage attributed to the launched process (MacOS and Linux only).
- **Memory**:
  - For extensions: The amount of JS heap memory used by the extension's code (external allocations not counted).
  - For processes: The amount of system memory used by the launched process (MacOS and Linux only).

You can also test by running `cursor --disable-extensions` from the command line. If performance improves, re-enable extensions one by one to identify problematic ones.

Try Extension Bisect to identify problematic extensions. Read more [here](https://code.visualstudio.com/blogs/2021/02/16/extension-bisect#_welcome-extension-bisect). Note: this works best for immediate issues, not gradual performance degradation.

### Use the Process Explorer

The Process Explorer shows which processes consume resources.

Open it: Command Palette (`Cmd/Ctrl + Shift + P`) → `Developer: Open Process Explorer`.

Review processes under:

- **`extensionHost`**: Extension-related issues
- **`ptyHost`**: Terminal resource consumption

The Process Explorer displays each terminal and its running commands for diagnosis.

For other high-usage processes, report to the [forum](https://forum.cursor.com/).

### Monitor System Resources

Use your operating system's monitoring tools to determine if the issue is
Cursor-specific or system-wide.

### Testing a Minimal Installation

If issues persist, test a minimal Cursor installation.

## AI Model Issues

If you're experiencing unexpected AI behavior, understanding [how AI models work](https://cursor.com/learn/how-ai-models-work.md) and [their limitations](https://cursor.com/learn/hallucination-limitations.md) can help you work more effectively with Cursor's AI features.

## General FAQs

### I see an update on the changelog but Cursor won't update

New updates use staged rollouts - randomly selected users receive updates first. Expect your update within a few days.

### I have issues with my GitHub login in Cursor / How do I log out of GitHub in Cursor?

Use `Sign Out of GitHub` from the command palette `Ctrl/⌘ + Shift + P`.

### I can't use GitHub Codespaces

GitHub Codespaces isn't supported yet.

### SSH Connection Problems on Windows

If you see "SSH is only supported in Microsoft versions of VS Code":

1. Uninstall Remote-SSH:
   - Open Extensions view (`Ctrl + Shift + X`)
   - Search "Remote-SSH"
   - Click gear icon → "Uninstall"

2. Install Anysphere Remote SSH:
   - Open Cursor marketplace
   - Search "SSH"
   - Install the Anysphere Remote SSH extension

3. After installation:
   - Close all VS Code instances with active SSH connections
   - Restart Cursor
   - Reconnect via SSH

Verify your SSH configuration and keys are properly set up.

### Cursor Tab and Inline Edit do not work behind my corporate proxy

Cursor Tab and Inline Edit use HTTP/2 for lower latency and resource usage.
Some corporate proxies (e.g., Zscaler) block HTTP/2. Fix by setting
`HTTP Compatibility Mode` to `HTTP/1.1` in `Cursor Settings` > `Network`.

### I just subscribed to Pro but I'm still on the free plan in the app

Log out and back in from Cursor Settings.

### When will my usage reset again?

Pro subscribers: Click `Manage Subscription` in the [Dashboard](https://cursor.com/dashboard) to view your renewal date.

Free users: Check your first Cursor email date. Usage resets monthly from that date.

### My Chat/Composer history disappeared after an update

Low disk space may cause Cursor to clear historical data during updates. To prevent this:

1. Maintain sufficient free disk space before updating
2. Clean up unnecessary system files regularly
3. Back up important conversations before updating

### How do I uninstall Cursor?

Follow [this guide](https://code.visualstudio.com/docs/setup/uninstall).
Replace "VS Code" or "Code" with "Cursor", and ".vscode" with ".cursor".

### How do I delete my account?

Click `Delete Account` in the [Dashboard](https://cursor.com/dashboard). This
permanently deletes your account and all associated data.

### How do I open Cursor from the command line?

Run `cursor` in your terminal. If the command is missing:

1. Open command palette `⌘⇧P`
2. Type `install command`
3. Select `Install 'cursor' command` (optionally install `code` command to override VS Code's)

### Unable to Sign In to Cursor

If clicking Sign In redirects to cursor.com but doesn't sign you in, disable
your firewall or antivirus software - they may block the sign-in process.

### Suspicious Activity Message

Due to recent increased misuse of our system, your request may have been blocked as a security measure. Here's how to resolve this:

First, check your VPN. If you're using one, try turning it off, as VPNs can sometimes trigger our security systems.

If that doesn't resolve it, you can try:

- Creating a new chat
- Waiting a bit and trying again later
- Creating a new account using Google or GitHub authentication
- Upgrading to Cursor Pro


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/troubleshooting/request-reporting.md
# INDEX: 110/114
================================================================================

# Sharing Request IDs with Support

When you encounter issues with Cursor, our support team may ask for a Request ID. This guide explains what Request IDs are, how to find them, and why your privacy settings affect what we can see.

## What is a Request ID?

A Request ID is a unique identifier generated for each request you make to Cursor. It looks something like this:

```text
8f2a5b91-4d3e-47c6-9f12-5e8d94ca7d23
```

This ID allows us to locate your specific request in our internal systems and investigate what went wrong.

Request IDs are only meaningful within Cursor's private backend. They're lookup keys with no value outside our systems. You don't need to treat them as confidential.

## How to find your Request ID

1. Open the relevant conversation in the Chat sidebar
2. Click the context menu (top right corner)
3. Select `Copy Request ID`
4. Share this ID with us via the forum or email

![Request ID popup](/docs-static/images/requestIDpopup.png)

## Why Privacy Mode matters for debugging

Your privacy settings affect what our team can see when investigating your issue.

### With Privacy Mode enabled

We can only see:

- Which model was used
- Whether tool failures occurred (but not which tools failed)
- Backend failures unrelated to your prompt, code, or agent actions

### With Share Data enabled

We can see:

- The full conversation between you and the agent
- Tool calls, including details about which ones failed
- Context provided to the agent (system prompt, rules, git status)

### What this means for you

For agent behavior issues, understanding what happened without Share Data enabled is difficult. We'd need extremely precise debugging instructions from you to reproduce the problem.

For connectivity issues, we can often debug them with Privacy Mode enabled. These typically don't require seeing your code or conversation content.

**Privacy Mode is per-request.** Changing your privacy setting does not retroactively affect previous requests. Each request is logged according to the privacy mode in effect when it was submitted.

If you encountered an issue while Privacy Mode was enabled, switching to Share Data afterward won't give us visibility into that original request. To get full debugging information, reproduce the issue with Share Data enabled.

## Our recommendation

If you're reporting an issue, especially anything involving unexpected agent behavior:

### Switch to Share Data mode

Temporarily enable Share Data in your privacy settings.

### Reproduce the issue

Perform the same actions that caused the problem.

### Copy the new Request ID

Use the context menu to copy the Request ID from the new conversation.

### Share it with us

Send the Request ID via the forum or email.

### Re-enable Privacy Mode

Switch back to Privacy Mode if preferred.


---

## Sitemap

[Overview of all docs pages](/llms.txt)


================================================================================
# SOURCE: https://cursor.com/docs/troubleshooting/troubleshooting-guide.md
# INDEX: 111/114
================================================================================

# Troubleshooting Guide

Cursor issues can stem from extensions, app data, or system problems. Try these troubleshooting steps.

### Reporting an Issue

Steps to report an issue to the Cursor team

## Troubleshooting

### Check network connectivity

First check if Cursor can connect to its services.

**Run network diagnostics:** Go to `Cursor Settings` > `Network` and click `Run Diagnostics`. This tests your connection to Cursor's servers and identifies network issues affecting AI features, updates, or other online functionality.

If diagnostics reveal connectivity issues, check firewall settings, proxy configuration, or network restrictions blocking Cursor's access.

### Clearing extension data

For extension issues:

**Disable all extensions temporarily:** Run `cursor --disable-extensions` from the command line. If issues resolve, re-enable extensions one by one to identify the problematic one.

**Reset extension data:** Uninstall and reinstall problematic extensions to reset their stored data. Check settings for extension configuration that persists after reinstallation.

### Clearing app data

This deletes your app data, including extensions, themes, snippets, and installation-related data. Export your profile first to preserve this data.

Cursor stores app data outside the app for restoration between updates and reinstallations.

To clear app data:

**Windows:** Run these commands in Command Prompt:

```txt
rd /s /q "%USERPROFILE%\AppData\Local\Programs\Cursor"
rd /s /q "%USERPROFILE%\AppData\Local\Cursor"
rd /s /q "%USERPROFILE%\AppData\Roaming\Cursor"
del /f /q "%USERPROFILE%\.cursor*"
rd /s /q "%USERPROFILE%\.cursor"
```

**MacOS:** Run `sudo rm -rf ~/Library/Application\ Support/Cursor` and `rm -f ~/.cursor.json` in Terminal.

**Linux:** Run `rm -rf ~/.cursor ~/.config/Cursor/` in Terminal.

### Uninstalling Cursor

To uninstall Cursor:

### Windows

Search "Add or Remove Programs" in Start Menu, find "Cursor", click "Uninstall".

### MacOS

Open Applications folder, right-click "Cursor", select "Move to Trash".

### Linux

**For .deb packages:** `sudo apt remove cursor`

**For .rpm packages:** `sudo dnf remove cursor` or `sudo yum remove cursor`

**For AppImage:** Delete the Cursor.appimage file from its location.

### Reinstalling Cursor

Reinstall from the [Downloads page](https://www.cursor.com/downloads). Without cleared app data, Cursor restores to its previous state. Otherwise, you get a fresh install.

## Reporting an Issue

If these steps don't help, report to the [forum](https://forum.cursor.com/).

### Cursor Forum

Report a bug or issue on the Cursor forum

For quick resolution, provide:

### Screenshot of Issue

Capture a screenshot, redact sensitive information.

### Steps to Reproduce

Document exact steps to reproduce the issue.

### System Information

Get system info from: `Cursor` > `About Cursor` (macOS) or `Help` > `About` (Windows/Linux)

### Request IDs

Click to view our guide on gathering request IDs

### Console Errors

Go to `Help` > `Toggle Developer Tools` to check for errors.

### Logs

Open the Command Palette (`Cmd/Ctrl+Shift+P`), then run `Developer: Open Logs Folder` to access log files.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
