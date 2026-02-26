# API Keys

Use your own API keys to send unlimited AI messages at your own cost. When configured, Cursor will use your API keys to call LLM providers directly.

To use your API key, go to `Cursor Settings` > `Models` and enter your API keys. Click **Verify**. Once validated, your API key is enabled.

Custom API keys only work with standard chat models. Features requiring
specialized models (like Tab Completion) will continue using Cursor's built-in
models.

Cursor's [Zero Data Retention policy](https://cursor.com/docs/account/teams/dashboard.md#privacy-settings) does not apply when using your own API keys. Your data handling will be subject to the privacy policies of your chosen AI provider (OpenAI, Anthropic, Google, Azure, or AWS).

## Supported providers

- **OpenAI** - Standard, non-reasoning chat models only. The model picker will show the OpenAI models available.
- **Anthropic** - All Claude models available through the Anthropic API.
- **Google** - Gemini models available through the Google AI API.
- **Azure OpenAI** - Models deployed in your Azure OpenAI Service instance.
- **[AWS Bedrock](https://cursor.com/docs/settings/aws-bedrock.md)** - Use AWS access keys, secret keys, or IAM roles. Works with models available in your Bedrock configuration. See the [AWS Bedrock setup guide](https://cursor.com/docs/settings/aws-bedrock.md) for detailed configuration instructions.

## FAQ

### Will my API key be stored or leave my device?

Your API key won't be stored but is sent to our server with every request.
All requests are routed through our backend for final prompt building.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
