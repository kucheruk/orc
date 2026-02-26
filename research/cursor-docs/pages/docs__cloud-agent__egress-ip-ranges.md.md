# Cloud Agent Egress IP Ranges

Cloud Agents make network connections from specific IP address ranges when accessing external services, APIs, or repositories. This page documents the IP addresses that Cloud Agents use for outbound connections.

## API Endpoint

The IP ranges are available via a [JSON API endpoint](https://cursor.com/docs/ips.json):

```bash
curl https://cursor.com/docs/ips.json
```

### Response Format

```json
{
  "version": 1,
  "modified": "2025-09-24T16:00:00.000Z",
  "cloudAgents": {
    "us3p": ["100.26.13.169/32", "34.195.201.10/32", ...],
    "us4p": ["54.184.235.255/32", "35.167.37.158/32", ...],
    "us5p": ["3.12.82.200/32", "52.14.104.140/32", ...]
  }
}
```

- **version**: Schema version number for the API response
- **modified**: ISO 8601 timestamp of when the IP ranges were last updated
- **cloudAgents**: Object containing IP ranges, keyed by cluster

IP ranges published in [CIDR notation](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing). You can use an online conversion tool to convert from CIDR notation to IP address ranges if needed.

## Using the IP Ranges

These published IP ranges may be used by Cloud Agents to:

- Clone and push to remote repositories (unless using the [GitHub IP allow list](https://cursor.com/docs/integrations/github.md#ip-allow-list-configuration))
- Download packages and dependencies
- Make API calls to external services
- Access web resources during agent execution

If your organization uses firewall rules or IP allowlists to control network access, you may need to allowlist these IP ranges to ensure Cloud Agents can properly access your services.

**Important considerations:**

- We make changes to our IP addresses from time to time for scaling and operational needs.
- We do not recommend allowlisting by IP address as your primary security mechanism.
- If you must use these IP ranges, we strongly encourage regular monitoring of the JSON API endpoint.

## GitHub Proxy and IP Allow List

Cursor supports a similar but distinct feature to [use a GitHub egress proxy for IP allow lists](https://cursor.com/docs/integrations/github.md#ip-allow-list-configuration). This proxy works for all GitHub-dependent Cursor features, including Cloud Agents.

We recommended that you use the GitHub-specific IP allow list for GitHub, as it is more deeply integrated with the Cursor GitHub app, and the above egress IP ranges for everything else.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
