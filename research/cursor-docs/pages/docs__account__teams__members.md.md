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
