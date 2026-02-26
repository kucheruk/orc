# Downloads

## Platform support

Cursor is available for all major operating systems with native installation packages.

### Windows

- Windows 10 and later
- Native installer (.exe)

### macOS

- macOS 10.15 (Catalina) and later
- Native installer (.dmg)
- Apple Silicon and Intel support

### Linux

#### Debian/Ubuntu (recommended)

Install Cursor from the official apt repository. This is the recommended method for Debian, Ubuntu, and other Debian-based distributions.

```bash
# Add Cursor's GPG key
curl -fsSL https://downloads.cursor.com/keys/anysphere.asc | gpg --dearmor | sudo tee /etc/apt/keyrings/cursor.gpg > /dev/null

# Add the Cursor repository
echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/cursor.gpg] https://downloads.cursor.com/aptrepo stable main" | sudo tee /etc/apt/sources.list.d/cursor.list > /dev/null

# Update and install
sudo apt update
sudo apt install cursor
```

This installs Cursor to `/opt/Cursor`, adds a desktop entry, and configures the `cursor` command for terminal use. Updates are handled through your system's package manager.

You can also download the `.deb` file directly from [cursor.com/downloads](https://cursor.com/downloads) and install it with `sudo apt install ./cursor-*.deb`.

#### RHEL/Fedora

Install Cursor from the official yum/dnf repository:

```bash
# Add Cursor's repository
sudo tee /etc/yum.repos.d/cursor.repo << 'EOF'
[cursor]
name=Cursor
baseurl=https://downloads.cursor.com/yumrepo
enabled=1
gpgcheck=1
gpgkey=https://downloads.cursor.com/keys/anysphere.asc
EOF

# Install Cursor
sudo dnf install cursor
```

For older systems using yum instead of dnf, replace `dnf` with `yum`.

You can also download the `.rpm` file directly from [cursor.com/downloads](https://cursor.com/downloads) and install it with `sudo dnf install ./cursor-*.rpm`.

#### AppImage (portable)

AppImage works on any Linux distribution without installation:

1. Download the `.AppImage` file from [cursor.com/downloads](https://cursor.com/downloads)
2. Make it executable and run:

```bash
chmod +x Cursor-*.AppImage
./Cursor-*.AppImage
```

The apt and yum packages are preferred over AppImage. They provide desktop icons, automatic updates through your system's package manager, and CLI tools that AppImage doesn't include.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
