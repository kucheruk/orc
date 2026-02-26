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
