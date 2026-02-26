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
