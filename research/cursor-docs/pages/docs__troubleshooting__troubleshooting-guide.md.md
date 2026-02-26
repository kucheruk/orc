# Troubleshooting Guide

Cursor issues can stem from extensions, app data, or system problems. Try these troubleshooting steps.

### Reporting an Issue

Steps to report an issue to the Cursor team

## Troubleshooting

### Check network connectivity

First check if Cursor can connect to its services.

**Run network diagnostics:** Go to `Cursor Settings` > `Network` and click `Run Diagnostics`. This tests your connection to Cursor's servers and identifies network issues affecting AI features, updates, or other online functionality.

If diagnostics reveal connectivity issues, check firewall settings, proxy configuration, or network restrictions blocking Cursor's access.

### Clearing extension data

For extension issues:

**Disable all extensions temporarily:** Run `cursor --disable-extensions` from the command line. If issues resolve, re-enable extensions one by one to identify the problematic one.

**Reset extension data:** Uninstall and reinstall problematic extensions to reset their stored data. Check settings for extension configuration that persists after reinstallation.

### Clearing app data

This deletes your app data, including extensions, themes, snippets, and installation-related data. Export your profile first to preserve this data.

Cursor stores app data outside the app for restoration between updates and reinstallations.

To clear app data:

**Windows:** Run these commands in Command Prompt:

```txt
rd /s /q "%USERPROFILE%\AppData\Local\Programs\Cursor"
rd /s /q "%USERPROFILE%\AppData\Local\Cursor"
rd /s /q "%USERPROFILE%\AppData\Roaming\Cursor"
del /f /q "%USERPROFILE%\.cursor*"
rd /s /q "%USERPROFILE%\.cursor"
```

**MacOS:** Run `sudo rm -rf ~/Library/Application\ Support/Cursor` and `rm -f ~/.cursor.json` in Terminal.

**Linux:** Run `rm -rf ~/.cursor ~/.config/Cursor/` in Terminal.

### Uninstalling Cursor

To uninstall Cursor:

### Windows

Search "Add or Remove Programs" in Start Menu, find "Cursor", click "Uninstall".

### MacOS

Open Applications folder, right-click "Cursor", select "Move to Trash".

### Linux

**For .deb packages:** `sudo apt remove cursor`

**For .rpm packages:** `sudo dnf remove cursor` or `sudo yum remove cursor`

**For AppImage:** Delete the Cursor.appimage file from its location.

### Reinstalling Cursor

Reinstall from the [Downloads page](https://www.cursor.com/downloads). Without cleared app data, Cursor restores to its previous state. Otherwise, you get a fresh install.

## Reporting an Issue

If these steps don't help, report to the [forum](https://forum.cursor.com/).

### Cursor Forum

Report a bug or issue on the Cursor forum

For quick resolution, provide:

### Screenshot of Issue

Capture a screenshot, redact sensitive information.

### Steps to Reproduce

Document exact steps to reproduce the issue.

### System Information

Get system info from: `Cursor` > `About Cursor` (macOS) or `Help` > `About` (Windows/Linux)

### Request IDs

Click to view our guide on gathering request IDs

### Console Errors

Go to `Help` > `Toggle Developer Tools` to check for errors.

### Logs

Open the Command Palette (`Cmd/Ctrl+Shift+P`), then run `Developer: Open Logs Folder` to access log files.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
