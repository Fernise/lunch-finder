# Configuration

`config.example.json` contains an illustrative Vienna location and restaurant set. Copy it to ignored `config.json`, then choose your own office/location, restaurants, budget, timezone and notification limit. Published prices/ratings are examples rather than verified current values.

## Credentials

- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` configure Telegram delivery.
- `LUNCH_MENU_BEARER_TOKEN` is optional for the configured authenticated menu source. The JSON contains the environment-variable name, never the value.
- `source_bearer_token_env` resolves the credential at request time. Missing values fail before a request and allow other sources to continue.

Keep these in ignored `.env` or the scheduler's secret configuration. Real bot/chat credentials, crawled state and personal config stay outside Git.

## Run modes

`--dry-run` performs menu fetches and records crawl state, but does not send Telegram or mark offers notified. Normal execution sends only new selected offers. Unit tests are the offline mode and mock external requests.

Approximate regular-menu items are labeled as estimates and ranked below high-confidence daily offers. A missing or closed menu should not silently become a claimed fresh daily menu.

## Scheduling

`deploy/` contains illustrative systemd service/timer units. Adapt the service account, installation directory and private environment file. Keep the timer timezone aligned with your configuration. No existing VPS deployment, credentials or cron state is included in this public snapshot.
