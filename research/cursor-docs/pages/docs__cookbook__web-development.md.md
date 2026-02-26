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
