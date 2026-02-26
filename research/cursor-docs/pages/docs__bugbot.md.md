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
