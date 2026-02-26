# Team Pricing

There are two teams plans: Teams ($40/user/mo) and Enterprise (Custom).

Team plans provide additional features like:

- Privacy Mode enforcement
- Admin Dashboard with usage stats (also accessible via [Admin API](https://cursor.com/docs/account/teams/admin-api.md))
- Centralized team billing
- SAML/OIDC SSO

We recommend Teams for any customer that is happy self-serving. We recommend [Enterprise](https://cursor.com/docs/enterprise.md) for customers that need priority support, pooled usage, invoicing, SCIM, or advanced security controls. [Contact sales](https://cursor.com/contact-sales) to get started.

## How pricing works

Teams pricing is usage-based. Each seat includes monthly usage, and you can continue using Cursor beyond that with on-demand usage.

### Included usage

Each team seat ($40/mo) comes with **$20/mo of included usage**. This usage:

- Is allocated per user (each user gets their own $20)
- Does not transfer between team members
- Resets at the start of each billing cycle
- Covers all agent requests at public list API prices + Cursor Token Fee

Our [Enterprise plan](https://cursor.com/docs/enterprise.md) offers pooled usage shared between all users in a team. [Get in touch](https://cursor.com/contact-sales) with our team to learn more.

### On-demand usage

On-demand usage allows you to continue using models after your included amount is consumed, billed in arrears.

When exceeding the $20 of included usage, team members automatically continue with **on-demand usage**:

- Billed monthly at the same rates (API prices + Cursor Token Fee)
- No interruption in service or quality
- Tracked per user in your admin dashboard (see [spending data API](https://cursor.com/docs/account/teams/admin-api.md#get-spending-data))
- Can be controlled with spending limits

On-demand usage is enabled by default for the Teams plan.

### Cursor Token Fee

All non-Auto agent requests include a **$0.25 per million tokens** fee. This covers:

- [Semantic search](https://cursor.com/docs/context/semantic-search.md)
- Custom model execution (Tab, Apply, etc.)
- Infrastructure and processing costs

This fee applies to all tokens: input, output, and cached tokens. This applies to [BYOK](https://cursor.com/docs/settings/api-keys.md) as well.

## Active seats

Cursor bills per active user, not pre-allocated seats. Add or remove users anytime and billing will adjust immediately.

Refunds appear as account credit on your next invoice. Your renewal date stays the same.

## Spending controls

Teams can configure monthly team-wide spending limits. You can manage these limits through the dashboard. Per-member spend limits are available on [Enterprise](https://cursor.com/docs/enterprise.md) plans.

Contact `enterprise@cursor.com` for volume discounts on larger teams.

## Model Pricing

All prices are per million tokens. Teams are charged at public list API prices + [Cursor Token Fee](https://cursor.com/docs/account/teams/pricing.md#cursor-token-fee).

| Model                                                                                         | Provider  | Input | Cache write | Cache read | Output | Notes                                                                                                                                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------------- | --------- | ----- | ----------- | ---------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Claude 4 Sonnet](https://www.anthropic.com/claude/sonnet)                                    | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Claude 4 Sonnet 1M](https://www.anthropic.com/claude/sonnet)                                 | Anthropic | $6    | $7.5        | $0.6       | $22.5  | Hidden by default; This model can be very expensive due to the large context window; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                        |
| [Claude 4.5 Haiku](https://www.anthropic.com/claude/haiku)                                    | Anthropic | $1    | $1.25       | $0.1       | $5     | Hidden by default; Bedrock/Vertex: regional endpoints +10% surcharge; Cache: writes 1.25x, reads 0.1x                                                                                                                                                                                                                                         |
| [Claude 4.5 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | Hidden by default; Thinking variant counts as 2 requests in legacy pricing                                                                                                                                                                                                                                                                    |
| [Claude 4.5 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | Hidden by default; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                          |
| [Claude 4.6 Opus](https://www.anthropic.com/claude/opus)                                      | Anthropic | $5    | $6.25       | $0.5       | $25    | The cost is about 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                       |
| [Claude 4.6 Opus (Fast mode)](https://www.anthropic.com/claude/opus)                          | Anthropic | $30   | $37.5       | $3         | $150   | Hidden by default; Limited research preview; The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                |
| [Claude 4.6 Sonnet](https://www.anthropic.com/claude/sonnet)                                  | Anthropic | $3    | $3.75       | $0.3       | $15    | The cost is 2x when the input exceeds 200k tokens                                                                                                                                                                                                                                                                                             |
| [Composer 1](https://cursor.com)                                                              | Cursor    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Composer 1.5](https://cursor.com)                                                            | Cursor    | $3.5  | -           | $0.35      | $17.5  | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 2.5 Flash](https://developers.googleblog.com/en/start-building-with-gemini-25-flash/) | Google    | $0.3  | -           | $0.03      | $2.5   | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Flash](https://ai.google.dev/gemini-api/docs)                                       | Google    | $0.5  | -           | $0.05      | $3     | -                                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro](https://ai.google.dev/gemini-api/docs)                                         | Google    | $2    | -           | $0.2       | $12    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [Gemini 3 Pro Image Preview](https://ai.google.dev/gemini-api/docs)                           | Google    | $2    | -           | $0.2       | $12    | Hidden by default; Native image generation model optimized for speed, flexibility, and contextual understanding; Text input and output priced the same as Gemini 3 Pro; Image output: $120/1M tokens (\~$0.134 per 1K/2K image, \~$0.24 per 4K image); Preview models may change before becoming stable and have more restrictive rate limits |
| [Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs)                                       | Google    | $2    | -           | $0.2       | $12    | -                                                                                                                                                                                                                                                                                                                                             |
| [GPT-5](https://openai.com/index/gpt-5/)                                                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5-high                                                                                                                                                                                                                                       |
| [GPT-5 Fast](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $2.5  | -           | $0.25      | $20    | Hidden by default; Faster speed but 2x price; Available reasoning effort variants are gpt-5-high-fast, gpt-5-low-fast                                                                                                                                                                                                                         |
| [GPT-5 Mini](https://openai.com/index/gpt-5/)                                                 | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5-Codex](https://platform.openai.com/docs/models/gpt-5-codex)                            | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.1 Codex Max](https://platform.openai.com/docs/models/gpt-5-codex)                      | OpenAI    | $1.25 | -           | $0.125     | $10    | Hidden by default                                                                                                                                                                                                                                                                                                                             |
| [GPT-5.1 Codex Mini](https://platform.openai.com/docs/models/gpt-5-codex)                     | OpenAI    | $0.25 | -           | $0.025     | $2     | Hidden by default; Agentic and reasoning capabilities; 4x rate limits compared to GPT-5.1 Codex                                                                                                                                                                                                                                               |
| [GPT-5.2](https://openai.com/index/gpt-5/)                                                    | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.2-high                                                                                                                                                                                                                                                        |
| [GPT-5.2 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Hidden by default; Agentic and reasoning capabilities                                                                                                                                                                                                                                                                                         |
| [GPT-5.3 Codex](https://platform.openai.com/docs/models/gpt-5-codex)                          | OpenAI    | $1.75 | -           | $0.175     | $14    | Agentic and reasoning capabilities; Available reasoning effort variant is gpt-5.3-codex-high                                                                                                                                                                                                                                                  |
| [Grok Code](https://docs.x.ai/docs/models#models-and-pricing)                                 | xAI       | $0.2  | -           | $0.02      | $1.5   | -                                                                                                                                                                                                                                                                                                                                             |
| Kimi K2.5                                                                                     | Moonshot  | $0.6  | -           | $0.1       | $3     | Hidden by default                                                                                                                                                                                                                                                                                                                             |


---

## Sitemap

[Overview of all docs pages](/llms.txt)
