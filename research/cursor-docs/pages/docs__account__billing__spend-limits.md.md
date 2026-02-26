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
