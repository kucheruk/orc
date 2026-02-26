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
