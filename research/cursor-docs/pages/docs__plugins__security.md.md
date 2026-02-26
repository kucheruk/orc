# Marketplace security

Every plugin in the [Cursor Marketplace](https://cursor.com/marketplace) is manually reviewed by our team before it's listed. We work exclusively with a small group of trusted partners, and we review each plugin for security, data handling, and quality before it goes live.

## What risk does installing a plugin carry?

Plugins are lightweight by design. They're largely markdown files and supporting files for skills, such as templates and scripts. No binaries are shipped.

Plugins respect your MCP allowlist and blocklist, so they can only access the tools and servers you've explicitly permitted. If a plugin contains a blocked MCP server, the plugin installs normally but the blocked server cannot make calls. Existing MCP governance policies carry over to plugins without additional configuration.

That said, plugins are third-party software, and installation is at the discretion and risk of the installing user. Since all plugins are open source, we recommend reviewing a plugin's source code before installing.

## Are plugins open source?

Yes. All marketplace plugins must be open source. You can inspect the code yourself, and so can the broader community.

## Are plugin updates reviewed?

Yes. Plugins in the marketplace are not automatically updated from source code. We manually review every plugin update, so nothing gets into the marketplace without our explicit approval.

## What happens if a security issue is found in a plugin?

We take a proactive approach. If we determine that a plugin poses a risk to users, whether through our own review, community reports, or ongoing monitoring, we remove it from the marketplace immediately while the issue is being resolved.

## Are plugin authors required to maintain their plugins?

Yes. Plugin authors are expected to respond to and resolve reported security or stability issues. Authors who don't meet this standard risk losing their good standing in the marketplace, which may result in their plugins being delisted.

## How do I report a plugin issue?

If you discover a security concern or other issue with a marketplace plugin, report it to [security-reports@cursor.com](mailto:security-reports@cursor.com). We take all reports seriously and follow up promptly.

## How do you decide which plugins to list?

We keep the marketplace curated. We work directly with plugin authors we trust, and every submission goes through our internal review process. As we mature our vetting standards, we plan to open this up more broadly.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
