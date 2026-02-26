# iOS & macOS (Swift)

Welcome to Swift development in Cursor! Whether you're building iOS apps, macOS applications, or server-side Swift projects, we've got you covered. This guide will help you set up your Swift environment in Cursor, starting with the basics and moving on to more advanced features.

## Basic Workflow

The simplest way to use Cursor with Swift is to treat it as your primary code editor while still relying on Xcode for building and running your apps. You'll get great features like:

- Smart code completion
- AI-powered coding assistance (try [CMD+K](https://cursor.com/docs/inline-edit/overview.md) on any line)
- Quick access to documentation with [@Docs](https://cursor.com/docs/context/mentions.md)
- Syntax highlighting
- Basic code navigation

When you need to build or run your app, simply switch to Xcode. This workflow is perfect for developers who want to leverage Cursor's AI capabilities while sticking to familiar Xcode tools for debugging and deployment.

### Hot Reloading

When using Xcode workspaces or projects (instead of opening a folder directly in Xcode), Xcode can often ignore changes to your files that were made in Cursor, or outside of Xcode in general.

While you can open the folder in Xcode to resolve this, you may need to use a project for your Swift development workflow.

A great solution to this is to use [Inject](https://github.com/krzysztofzablocki/Inject), a hot reloading library for Swift that allows your app to "hot reload" and update as soon as changes are made in real time. This does not suffer from the side effects of the Xcode workspace/project issue, and allows you to make changes in Cursor and have them reflected in your app immediately.

## Advanced Swift Development

This section of the guide was heavily inspired by [Thomas
Ricouard](https://x.com/Dimillian) and his
[article](https://dimillian.medium.com/how-to-use-cursor-for-ios-development-54b912c23941)
about using Cursor for iOS development. Please check his article for more
details and drop him a follow for more Swift content.

If you are looking to only need one editor open at a time, and want to avoid the need to switch between Xcode and Cursor, you can use an extension like [Sweetpad](https://sweetpad.hyzyla.dev/) to integrate Cursor directly with Xcode's underlying build system.

Sweetpad is a powerful extension that allows you to build, run and debug your Swift projects directly in Cursor, without compromising on Xcode's features.

To get started with Sweetpad, you'll still need to have Xcode installed on your Mac - it's the foundation of Swift development. You can download Xcode from the [Mac App Store](https://apps.apple.com/us/app/xcode/id497799835). Once you have Xcode set up, let's enhance your development experience in Cursor with a few essential tools.

Open your terminal and run:

```bash
# Builds your projects without needing Xcode open
brew install xcode-build-server

# Pretty print's the `xcodebuild` command output into Cursor's terminal
brew install xcbeautify

# Allows for advanced formating and language features
brew install swiftformat
```

Next, install the [Swift Language Support](cursor:extension/chrisatwindsurf.swift-vscode) extension in Cursor. This will give you syntax highlighting and basic language features right out of the box.

Then, we can install the [Sweetpad](https://sweetpad.hyzyla.dev/) extension to integrate Cursor with Xcode. Sweetpad wraps a bunch of shortcuts around the `xcodebuild` CLI (and much more), and allows you to scan your targets, select the destination, build, and run your app just like Xcode. On top of that, it’ll set up your project for Xcode Build Server so you get all the features mentioned above.

### Sweetpad Usage

Once Sweetpad is installed, and you have a Swift project open in Cursor, you should first run the `Sweetpad: Generate Build Server Config` command. This will generate a `buildServer.json` file in the root of your project that allows the Xcode Build Server to work with your project.

Then, from either the Command Palette or the Sweetpad sidebar, you can select the target you want to build and run.

You need to build your project once to enable auto-completion, jump to definition, and other language features.

You can also now hit F5 to build and run your project with a debugger - you might need to create a launch configuration first, but just select Sweetpad from the list when prompted!

As with many extensions in Cursor, you can bind many of the Sweetpad commands to keyboard shortcuts, to make your workflow even more efficient.

To learn more about Sweetpad, check out these resources:

### Sweetpad Website

Official Sweetpad website with features and installation instructions

### Sweetpad Guide

Comprehensive guide covering configuration, usage and advanced features


---

## Sitemap

[Overview of all docs pages](/llms.txt)
