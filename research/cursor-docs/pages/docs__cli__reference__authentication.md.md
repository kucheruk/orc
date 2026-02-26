# Authentication

Cursor CLI supports two authentication methods: browser-based login (recommended) and API keys.

## Browser authentication (recommended)

Use the browser flow for the easiest authentication experience:

```bash
# Log in using browser flow
agent login

# Check authentication status
agent status

# Log out and clear stored authentication
agent logout
```

The login command will open your default browser and prompt you to authenticate with your Cursor account. Once completed, your credentials are securely stored locally.

## API key authentication

For automation, scripts, or CI/CD environments, use API key authentication:

### Step 1: Generate an API key

Generate an API key in your Cursor dashboard under Integrations > User API Keys.

### Step 2: Set the API key

You can provide the API key in two ways:

**Option 1: Environment variable (recommended)**

```bash
export CURSOR_API_KEY=your_api_key_here
agent "implement user authentication"
```

**Option 2: Command line flag**

```bash
agent --api-key your_api_key_here "implement user authentication"
```

## Authentication status

Check your current authentication status:

```bash
agent status
```

This command will display:

- Whether you're authenticated
- Your account information
- Current endpoint configuration

## Troubleshooting

- **"Not authenticated" errors:** Run `agent login` or ensure your API key is correctly set
- **SSL certificate errors:** Use the `--insecure` flag for development environments
- **Endpoint issues:** Use the `--endpoint` flag to specify a custom API endpoint


---

## Sitemap

[Overview of all docs pages](/llms.txt)
