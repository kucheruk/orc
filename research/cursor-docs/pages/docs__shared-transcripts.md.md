# Shared transcripts

Share your AI conversations with teammates or the public. Shared transcripts let you collaborate on solutions, document debugging sessions, or showcase how you solved a problem.

## What are shared transcripts?

Shared transcripts are read-only copies of your Cursor chat conversations that you can share via a link. Recipients can view the entire conversation including:

- All messages between you and the AI
- Code snippets and suggestions
- Tool calls and their results
- Context that was included

This makes it easy to share solutions, get feedback on approaches, or document how a problem was solved.

## How to share a chat

### From Cursor

1. Open the chat you want to share
2. Click the **Share** icon in the chat header (link icon)
3. Choose a visibility option:
   - **Team**: Only your team members can view
   - **Public**: Anyone with the link can view
4. Click **Copy Link** to copy the share URL

The share link is created when you open the share modal.

### Visibility options

| Visibility | Who can view                       | URL format                                          |
| ---------- | ---------------------------------- | --------------------------------------------------- |
| **Team**   | Team members with dashboard access | `cursor.com/dashboard?tab=shared-chats&shareId=...` |
| **Public** | Anyone with the link               | `cursor.com/s/abc123`                               |

Team visibility requires the viewer to be signed in and a member of your team. Public links can be shared anywhere, including social media, documentation, or Stack Overflow.

## Viewing shared transcripts

### From a public link

Click a public share link (e.g., `cursor.com/s/abc123`) to view the conversation directly in your browser. No sign-in required.

### From the dashboard

1. Go to **cursor.com/dashboard**
2. Click the **Shared Transcripts** tab
3. Use the tabs to filter:
   - **Team Chats**: All transcripts shared by your team
   - **My Chats**: Transcripts you've shared

Click any transcript to view the full conversation.

### Fork a shared chat

Want to continue a conversation from a shared transcript? You can **fork** it:

1. Open the shared transcript
2. Click **Fork to Cursor** (or use **Open in Cursor**)
3. The conversation opens in Cursor, ready for you to continue

You can also use the deeplink `cursor://fork-shared-chat/{shareId}` (replace `{shareId}` with the share ID from the URL) to open and fork a shared chat directly in Cursor.

Forking creates a copy. The original shared transcript remains unchanged.

## Managing shared transcripts

### Change visibility

You can change visibility after sharing:

1. Go to **Shared Transcripts** in the dashboard
2. Find the transcript
3. Click the visibility dropdown
4. Select **Team** or **Public**

### Delete a shared transcript

1. Go to **Shared Transcripts** in the dashboard
2. Find the transcript
3. Click the **...** menu
4. Select **Delete**

Deleting a share removes the link permanently. Anyone with the old link will see an error.

### Who can delete?

- **Your transcripts**: You can always delete your own
- **Team transcripts**: Team admins can delete any team member's transcript

## Privacy and security

### What gets shared

When you share a transcript, the full conversation is included:

- Your messages to the AI
- AI responses
- Code snippets
- Tool results (file reads, search results, etc.)
- File context that was attached

### What's not shared

- Your identity (only first name shown if viewing from dashboard)
- Your authentication tokens or API keys
- Files from your local machine (only content included in the chat)

### Automatic secret redaction

Cursor scans shared transcripts and redacts potential secrets:

- API keys
- Passwords
- Tokens
- Connection strings

This helps prevent accidental exposure, but always review before sharing sensitive conversations.

### Storage

Shared transcripts are stored securely:

- Encrypted at rest
- Stored separately from your Cursor account
- Subject to your team's data retention policies

## Requirements

### Plan requirements

Shared transcripts are available for:

- **Pro** users
- **Teams** users
- **Enterprise** users

Free and trial users cannot create shared transcripts.

| Plan              | Available | Visibility options                     |
| ----------------- | --------- | -------------------------------------- |
| Free / Free trial | No        | —                                      |
| **Pro**           | Yes       | Public only                            |
| **Teams**         | Yes       | Team + Public                          |
| **Enterprise**    | Yes       | Team only (public disabled by default) |

Pro users without a team can only share publicly. Teams and Enterprise teams can use team visibility; team admins configure which options are allowed. Enterprise teams have public sharing disabled by default for security.

### Privacy mode

Users with **Privacy Mode** set to "No Storage" cannot create shared transcripts. The feature requires storing conversation data.

### Team admin settings

Team admins can control sharing for their organization:

- **Enable/Disable**: Turn sharing on or off for the team
- **Allowed Visibilities**: Choose which visibility options are available (Team only, Public only, or both)

Configure these in **Dashboard > Settings > Team Settings**.

## Troubleshooting

### Share feature is only available for Pro, Teams, and Enterprise users

Upgrade to a paid plan to access shared transcripts.

### Share feature requires data storage

You have Privacy Mode set to "No Storage". Adjust your privacy settings in **Settings > Privacy** to enable sharing.

### Shared conversations are disabled for your team

Your team admin has disabled sharing. Contact them to enable it.

### No visibility options are available

Your team admin hasn't enabled any visibility options. Contact them to configure sharing settings.

### The share link doesn't work

The transcript may have been deleted by the creator. Share links are permanent until deleted.

### You have reached the daily limit of shares

You can create up to 50 shared transcripts per day. The limit resets daily. Try again tomorrow.

## Frequently asked questions

### Can I edit a shared transcript?

No, shared transcripts are read-only snapshots. To make changes, delete the share and create a new one.

### Do shared transcripts expire?

No, shared transcripts remain available until you delete them.

### Can I see who viewed my transcript?

View analytics are not currently available.

### What happens if I delete my account?

All your shared transcripts (where you're the creator) are deleted.

### Can I share a conversation with images?

Yes, images included in the conversation are preserved in the shared transcript.

### Is there a limit to how many transcripts I can share?

Yes. You can create up to 50 shared transcripts per day. The limit resets daily. Most users won't hit it with normal usage.

### Can I share Cloud Agent sessions?

Cloud Agent (Background Agent) sessions can be shared within your team using the share button in the agent header. Full public sharing for Cloud Agents is coming soon.

## Tips for sharing

**Give it a good title.** The default title comes from your conversation, but you can customize it when sharing.

**Review before sharing publicly.** Make sure no sensitive information is included.

- Use team sharing for internal discussions to keep work-in-progress solutions visible only to your team
- Fork before modifying. If you want to continue a shared conversation, fork it to preserve the original


---

## Sitemap

[Overview of all docs pages](/llms.txt)
