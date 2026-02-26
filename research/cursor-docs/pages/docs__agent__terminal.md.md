# Terminal

Agent runs shell commands directly in your terminal, with safe sandbox execution on macOS and Linux. Command history persists across sessions. Click skip to interrupt running commands with `Ctrl+C`.

## Sandbox

Sandbox is available on macOS (>v2.0) and Linux (>= v6.2). Windows users can use WSL2 for sandboxed command execution.

Auto mode is not currently compatible with Sandbox.

By default, Agent runs terminal commands in a restricted environment that blocks unauthorized file access and network activity. Commands execute automatically while staying confined to your workspace.

- **macOS**: Implemented using `sandbox-exec` (seatbelt)
- **Linux**: Implemented using Landlock v3 (kernel 6.2+), seccomp, and user namespaces

[Media](/docs-static/images/agent/sandbox.mp4)

### Linux Requirements

Linux sandbox requires:

- **Kernel 6.2 or later** with Landlock v3 support (`CONFIG_SECURITY_LANDLOCK=y`)
- **Unprivileged user namespaces** enabled (most modern distributions have this by default)

If your Linux kernel doesn't meet these requirements, Agent will fall back to asking for approval before running commands.

### How the sandbox works

The sandbox prevents unauthorized access while allowing workspace operations:

| Access Type         | Description                                                                                                                          |
| :------------------ | :----------------------------------------------------------------------------------------------------------------------------------- |
| **File access**     | Read access to the filesystemRead and write access to workspace directories                                                          |
| **Network access**  | Blocked by default. Configure with [`sandbox.json`](https://cursor.com/docs/agent/terminal.md#sandbox-configuration) or in settings. |
| **Temporary files** | Full access to `/tmp/` or equivalent system temp directories                                                                         |

The `.cursor` configuration directory stays protected regardless of allowlist settings.

### Allowlist

Commands on the allowlist skip sandbox restrictions and run immediately. You can add commands to the allowlist by choosing "Add to allowlist" when prompted after a sandboxed command fails.

When a sandboxed command fails due to restrictions, you can:

| Option               | Description                                                          |
| :------------------- | :------------------------------------------------------------------- |
| **Skip**             | Cancel the command and let Agent try something else                  |
| **Run**              | Execute the command without sandbox restrictions                     |
| **Add to allowlist** | Run without restrictions and automatically approve it for future use |

#### Default network allowlist

When network access is enabled, outbound connections are restricted to a curated set of domains. These cover common package registries, cloud providers, and language toolchains so most development workflows work without extra configuration.

### View default allowed domains

```
*.cloudflarestorage.com
*.docker.com
*.docker.io
*.googleapis.com
*.githubusercontent.com
*.gvt1.com
*.public.blob.vercel-storage.com
*.yarnpkg.com
alpinelinux.org
anaconda.com
apache.org
apt.llvm.org
archive.ubuntu.com
archlinux.org
awscli.amazonaws.com
azure.com
binaries.prisma.sh
bitbucket.org
centos.org
cloudflarestorage.com
cocoapods.org
codeload.github.com
cpan.org
crates.io
debian.org
dl.google.com
docker.com
docker.io
dot.net
dotnet.microsoft.com
eclipse.org
fedoraproject.org
files.pythonhosted.org
gcr.io
ghcr.io
github.com
gitlab.com
golang.org
google.com
goproxy.io
gradle.org
haskell.org
hashicorp.com
hex.pm
index.crates.io
java.com
java.net
json-schema.org
json.schemastore.org
k8s.io
launchpad.net
maven.org
mcr.microsoft.com
metacpan.org
microsoft.com
mise.run
nodejs.org
npm.duckdb.org
npmjs.com
npmjs.org
nuget.org
oracle.com
packagecloud.io
packages.microsoft.com
packagist.org
pkg.go.dev
playwright.azureedge.net
ppa.launchpad.net
proxy.golang.org
pub.dev
public.blob.vercel-storage.com
public.ecr.aws
pypa.io
pypi.org
pypi.python.org
pythonhosted.org
quay.io
registry.npmjs.org
ruby-lang.org
rubygems.org
rubyonrails.org
rustup.rs
rvm.io
security.ubuntu.com
sh.rustup.rs
sourceforge.net
spring.io
static.crates.io
static.rust-lang.org
sum.golang.org
swift.org
ubuntu.com
visualstudio.com
yarnpkg.com
ziglang.org
```

## Sandbox Configuration

You can customize sandbox behavior with a `sandbox.json` file to control network access, filesystem paths, and more.

Customizing the sandbox requires Cursor version v2.5 or later.

### File locations

Place `sandbox.json` in either or both of these locations:

| Location                           | Scope                       | Priority |
| :--------------------------------- | :-------------------------- | :------- |
| `~/.cursor/sandbox.json`           | All workspaces (per-user)   | Lower    |
| `<workspace>/.cursor/sandbox.json` | Single workspace (per-repo) | Higher   |

Both files are optional. When both exist, they are merged with per-repo settings taking priority. Enterprise team-admin policies and Cursor's hardcoded security rules layer on top and cannot be weakened by either file.

### Quick start

#### Allow specific domains

```json
{
  "networkPolicy": {
    "default": "deny",
    "allow": [
      "registry.npmjs.org",
      "pypi.org",
      "*.githubusercontent.com"
    ]
  }
}
```

Network traffic is denied by default. Only the listed domains are reachable.

#### Allow all network

```json
{
  "networkPolicy": {
    "default": "allow"
  }
}
```

All outbound network traffic is permitted inside the sandbox.

#### Full example

A full-stack web project where the agent needs to install packages, pull container images, access a database on the local network, and read a shared design-tokens repo:

```json
{
  "networkPolicy": {
    "default": "deny",
    "allow": [
      "registry.npmjs.org",
      "registry.yarnpkg.com",
      "pypi.org",
      "files.pythonhosted.org",
      "*.docker.io",
      "ghcr.io",
      "*.googleapis.com"
    ],
    "deny": [
      "*.internal.corp.example.com"
    ]
  },
  "additionalReadwritePaths": [
    "/home/me/.docker"
  ],
  "additionalReadonlyPaths": [
    "/opt/shared/design-tokens"
  ],
  "enableSharedBuildCache": true
}
```

This lets the agent:

- Install npm/pip packages and pull Docker images.
- Hit Google Cloud APIs.
- Block access to internal corporate services.
- Write to `~/.docker` for container operations.
- Read (but not modify) a shared design-tokens directory.
- Share npm/pip/cargo caches between sandboxed and unsandboxed runs.

### Schema reference

All fields are optional. Missing fields use the defaults shown below.

#### Top-level fields

| Field                      | Type       | Default                 | Description                                                                                                                                                                     |
| :------------------------- | :--------- | :---------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `type`                     | string     | `"workspace_readwrite"` | Sandbox mode. `"workspace_readwrite"` gives read/write access in the workspace. `"workspace_readonly"` restricts to read-only. `"insecure_none"` disables the sandbox entirely. |
| `additionalReadwritePaths` | `string[]` | `[]`                    | Extra paths the agent can read and write. Only applies when `type` is `"workspace_readwrite"`.                                                                                  |
| `additionalReadonlyPaths`  | `string[]` | `[]`                    | Extra paths the agent can read.                                                                                                                                                 |
| `disableTmpWrite`          | `boolean`  | `false`                 | When `true`, removes default write access to `/tmp` and system temp directories.                                                                                                |
| `enableSharedBuildCache`   | `boolean`  | `false`                 | Redirects build-tool caches (npm, cargo, pip, etc.) to a shared tmpdir so sandboxed and unsandboxed commands share the same caches.                                             |

#### `networkPolicy` object

| Field     | Type                  | Default  | Description                                                                                   |
| :-------- | :-------------------- | :------- | :-------------------------------------------------------------------------------------------- |
| `default` | `"allow"` \| `"deny"` | `"deny"` | Action when no allow/deny rule matches.                                                       |
| `allow`   | `string[]`            | `[]`     | Patterns to allow. Supports exact domains, wildcards, and CIDR notation.                      |
| `deny`    | `string[]`            | `[]`     | Patterns to deny. Highest priority; always blocks, even if a pattern also appears in `allow`. |

### Network pattern syntax

The `allow` and `deny` arrays accept three pattern formats:

| Format       | Example                | Matches                                                        |
| :----------- | :--------------------- | :------------------------------------------------------------- |
| Exact domain | `"registry.npmjs.org"` | That exact host                                                |
| Wildcard     | `"*.example.com"`      | Any subdomain of `example.com`, including `example.com` itself |
| CIDR         | `"10.0.0.0/8"`         | Any IP in that range                                           |

**Key rules:**

- Deny always beats allow. If a host matches both lists, it is blocked.
- Private/RFC 1918 addresses (`10.x`, `172.16.x`, `192.168.x`, `127.x`) and cloud metadata endpoints (`169.254.169.254`) are blocked by default to prevent SSRF.
- IPv6 private addresses (`::1`, `fe80::/10`, `fc00::/7`) are also blocked.
- URL paths are ignored; matching is domain/IP only.

### How policies merge

When multiple policy sources exist, they merge in priority order:

```
per-user  <  per-repo  <  team-admin  <  hardcoded
(lowest)                                (highest)
```

Merge rules:

- **Paths** (`additionalReadwritePaths`, `additionalReadonlyPaths`): unioned across all sources.
- **Network allow lists**: unioned, unless a team-admin allowlist is present (which replaces the union).
- **Network deny lists**: always unioned.
- **`networkPolicy.default`**: `"deny"` wins over `"allow"`.
- **Restrictive booleans** (`disableTmpWrite`, `networkPolicyStrict`): `true` wins.

### Protected paths

Certain paths are always write-protected, regardless of your `sandbox.json` configuration:

- `.cursor/*.json`, `.cursor/**/*.json`, `.cursor/.workspace-trusted`
- `.claude/*.json`, `.claude/**/*.json`
- `.vscode/**`
- `.code-workspace`
- `.git/hooks/**`, `.git/config`, `.git/info/attributes`
- `.cursorignore`

The following `.cursor` subdirectories **are** writable: `rules/`, `commands/`, `worktrees/`, `skills/`, `agents/`.

SSL certificate paths and `~/.ssh` are always readable.

## Editor Configuration

Configure how Agent runs terminal commands in the editor by navigating to Settings -> Cursor Settings -> Agents -> Auto-Run.

| Editor Setting               | Description                                                                                                                                                                                                                                                                                                                                                                                                                |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Run Mode**            | Choose how Agent runs tools like command execution, MCP, and file writes. Users can select from three options: • **Run in Sandbox**: Tools and commands will auto-run in sandbox where possible. Available on macOS and Linux. • **Ask Every Time**: All tools and commands require user approval before running. • **Run Everything**: The agent runs all tools and commands automatically without asking for user input. |
| **Auto-Run Network Access**  | Choose how sandboxed commands access the network: - **sandbox.json Only**: Network is limited to domains in your `sandbox.json` allowlist. No Cursor defaults are added. - **sandbox.json + Defaults**: Your allowlist plus Cursor's built-in defaults (common package managers, etc.). This is the default. - **Allow All**: All network access is allowed in the sandbox, regardless of `sandbox.json`.                  |
| **Command Allowlist**        | Commands that can run automatically outside of the sandbox.                                                                                                                                                                                                                                                                                                                                                                |
| **MCP Allowlist**            | MCP tools that can run automatically outside of the sandbox.                                                                                                                                                                                                                                                                                                                                                               |
| **Browser Protection**       | Prevent Agent from automatically running [Browser](https://cursor.com/docs/agent/browser.md) tools.                                                                                                                                                                                                                                                                                                                        |
| **File-Deletion Protection** | Prevent Agent from deleting files automatically.                                                                                                                                                                                                                                                                                                                                                                           |
| **Dotfile Protection**       | Prevent Agent from modifying dot files like .gitignore automatically.                                                                                                                                                                                                                                                                                                                                                      |
| **External-File Protection** | Prevent Agent from creating or modifying files outside of the workspace automatically.                                                                                                                                                                                                                                                                                                                                     |

## Enterprise Controls

Only available for Enterprise subscriptions.

Enterprise admins can override editor configurations or change which settings are visible for end users. Navigate to Settings -> Auto-Run in the [web dashboard](https://cursor.com/dashboard?tab=settings) to view and change these settings.

| Admin Setting                  | Description                                                                                                                                                                                                     |
| :----------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Auto-Run Controls**          | Enable controls for auto-run and sandbox mode. If disabled, the default behavior for all end users is that commands will auto-run in the sandbox when available, otherwise they will ask for permission to run. |
| **Sandboxing Mode**            | Control whether sandbox is available for end users. When enabled, commands will run automatically in the sandbox even if they are not on the allowlist.                                                         |
| **Sandbox Networking**         | Choose whether commands that run in the sandbox have network access.                                                                                                                                            |
| **Delete File Protection**     | Prevent Agent from deleting files automatically.                                                                                                                                                                |
| **MCP Tool Protection**        | When enabled, prevents the agent from automatically running MCP tools.                                                                                                                                          |
| **Terminal Command Allowlist** | Specify which terminal commands can run automatically without sandboxing. If empty, all commands require manual approval. When sandbox is enabled, commands not on this list will auto-run in sandbox mode.     |
| **Enable Run Everything**      | Give end users the ability to enable the `Run Everything` Auto-Run-Mode.                                                                                                                                        |

## Linux AppArmor configuration

On Linux, the sandbox uses user namespaces, which some distributions restrict through AppArmor. The Cursor desktop package ships with the required AppArmor profile, so no extra setup is needed for local installations.

Remote environments and the standalone [agent-cli](https://cursor.com/docs/agent/agent-cli.md) don't include this profile. If sandbox creation fails with a permissions error related to user namespaces, install the AppArmor configuration package for your distribution:

**Debian / Ubuntu (.deb)**:

```bash
curl -fsSL https://downloads.cursor.com/lab/enterprise/cursor-sandbox-apparmor_0.2.0_all.deb -o cursor-sandbox-apparmor.deb
sudo dpkg -i cursor-sandbox-apparmor.deb
```

**RHEL / Fedora (.rpm)**:

```bash
curl -fsSL https://downloads.cursor.com/lab/enterprise/cursor-sandbox-apparmor-0.2.0-1.noarch.rpm -o cursor-sandbox-apparmor.rpm
sudo rpm -i cursor-sandbox-apparmor.rpm
```

After installing, restart Cursor or your agent-cli session for the sandbox to work.

## Troubleshooting

Some shell themes (for example, Powerlevel9k/Powerlevel10k) can interfere with
the inline terminal output. If your command output looks truncated or
misformatted, disable the theme or switch to a simpler prompt when Agent runs.

### Disable heavy prompts for Agent sessions

Use the `CURSOR_AGENT` environment variable in your shell config to detect when
the Agent is running and skip initializing fancy prompts/themes.

```zsh
# ~/.zshrc — disable Powerlevel10k when Cursor Agent runs
if [[ -n "$CURSOR_AGENT" ]]; then
  # Skip theme initialization for better compatibility
else
  [[ -r ~/.p10k.zsh ]] && source ~/.p10k.zsh
fi
```

```bash
# ~/.bashrc — fall back to a simple prompt in Agent sessions
if [[ -n "$CURSOR_AGENT" ]]; then
  PS1='\u@\h \W \$ '
fi
```


---

## Sitemap

[Overview of all docs pages](/llms.txt)
