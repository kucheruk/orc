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
