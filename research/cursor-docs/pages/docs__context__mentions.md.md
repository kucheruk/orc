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
