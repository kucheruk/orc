# Pricing

You can try Cursor for free or purchase an individual or team plan.

## Individual

All individual plans include:

- Unlimited tab completions
- Extended agent usage limits on all models
- Access to Bugbot
- Access to Cloud Agents

Each plan includes usage charged at model inference [API prices](https://cursor.com/docs/models.md#model-pricing):

- Pro includes $20 of API agent usage + generous Auto and Composer usage
- Pro Plus includes $70 of API agent usage + generous Auto and Composer usage
- Ultra includes $400 of API agent usage + generous Auto and Composer usage

We work hard to grant additional bonus capacity beyond the guaranteed included usage. Since different models have different API costs, your model selection affects token output and how quickly your included usage is consumed. You can view usage and token breakdowns on [your dashboard](https://cursor.com/dashboard?tab=usage). Limit notifications are routinely shown in the editor.

To understand how usage is calculated, see our guide on [tokens and pricing](https://cursor.com/learn/tokens-pricing.md).

### How much usage do I need?

For individual plans, here are typical usage levels based on our data:

- **Daily Tab users**: Always stay within $20
- **Limited Agent users**: Often stay within the included $20
- **Daily Agent users**: Typically $60–$100/mo total usage
- **Power users (multiple agents/automation)**: Often $200+/mo total usage

### What happens when I reach my limit?

When you exceed your included monthly usage, you'll be notified in the editor and can choose to:

- **Add on-demand usage**: Continue using Cursor at the same API rates with pay-as-you-go billing
- **Upgrade your plan**: Move to a higher tier for more included usage

On-demand usage is billed monthly at the same rates as your included usage. Requests are never downgraded in quality or speed.

## Teams

There are two teams plans: Teams ($40/user/mo) and Enterprise (Custom).

Team plans provide additional features like:

- Privacy Mode enforcement
- Admin Dashboard with usage stats
- Centralized team billing
- SAML/OIDC SSO

We recommend Teams for any customer that is happy self-serving. We recommend [Enterprise](https://cursor.com/contact-sales) for customers that need priority support, pooled usage, invoicing, SCIM, or advanced security controls.

Learn more about [Teams pricing](https://cursor.com/docs/account/teams/pricing.md).

## Auto

Enabling Auto allows Cursor to select the model best fit for the immediate task and with the highest reliability based on current demand. This feature can detect degraded output performance and automatically switch models to resolve it.

![Model picker](/docs-static/images/models/model-picker.png)

Auto consumes usage at the following API rates:

- **Input + Cache Write**: $1.25 per 1M tokens
- **Output**: $6.00 per 1M tokens
- **Cache Read**: $0.25 per 1M tokens

Both the editor and dashboard will show your usage, which includes Auto. If you prefer to select a model directly, usage is incurred at that model's list API price.

## Max Mode

[Max Mode](https://cursor.com/docs/context/max-mode.md) extends the context window to the maximum a model supports. It uses token-based pricing at the model's API rate plus a 20% upcharge, so it consumes usage faster than the default context window. Max Mode is designed for users who want the best possible experience, regardless of cost.

## Bugbot

Bugbot is a separate product from Cursor subscriptions and has its own pricing plan.

- **Pro** ($40/mo): Unlimited reviews on up to 200 PRs/month, unlimited access to Cursor Ask, integration with Cursor to fix bugs, and access to Bugbot Rules
- **Teams** ($40/user/mo): Unlimited code reviews across all PRs, unlimited access to Cursor Ask, pooled usage across your team, and advanced rules and settings
- **Enterprise** (Custom): Everything in Teams plus advanced analytics and reporting, priority support, and account management

Learn more about [Bugbot pricing](https://cursor.com/bugbot#pricing).

## Cloud Agent

Cloud Agents are charged at API pricing for the selected [model](https://cursor.com/docs/models.md). You'll be asked to set a spend limit for Cloud Agents when you first start using them.

Virtual Machine (VM) compute for cloud agents will be priced in the
future.


---

## Sitemap

[Overview of all docs pages](/llms.txt)
