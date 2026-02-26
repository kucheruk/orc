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
