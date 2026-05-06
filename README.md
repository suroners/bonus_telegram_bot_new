# Casino Bonus Platform

Shared-DB Django implementation for scraping casino promotion pages, parsing bonuses with an LLM, and serving Telegram users with GEO-filtered affiliate links.

## Architecture

- `bonus_core` owns the shared database schema, admin, seed commands, serializers, and common link/GEO services.
- `bonus_scraping` seeds casino promotion pages and scrapes raw HTML with Playwright.
- `ai_parsing` processes scraped HTML through a DB-configured LLM provider and writes `Bonus` rows.
- `bonus_telegram_bot` runs the async Telegram bot and notification tasks.

The first deployment target keeps Postgres, Redis, the REST/admin web service, and the Telegram bot online. Scraper and AI parser workers can be run locally/on demand against the same database to reduce server cost.

## Setup

```bash
cp .env.example .env
docker compose up --build postgres redis web telegram
```

Set `TELEGRAM_BOT_TOKEN` in `.env` before running the `telegram` service. Create a Django admin user with `docker compose run --rm web python manage.py createsuperuser`, then add at least one enabled `AIProviderConfig` row in admin before running AI parser jobs.
Telegram no-GEO fallback is configurable with `TELEGRAM_NO_GEO_MODE`, `TELEGRAM_NO_GEO_CASINO_LIMIT`, `TELEGRAM_NO_GEO_BONUS_PER_CASINO_LIMIT`, and `TELEGRAM_NO_GEO_CASINO_COMMAND_LIMIT`.

For no-cost local parsing, set `DEFAULT_PARSER_PROVIDER=script` or run one job with `python manage.py parse_pending_queue --provider script`. The admin label is `Script Parser`; it extracts likely bonus blocks locally and still saves rows as unapproved for review.
For GPT-calibrated reference data, run `python manage.py build_reference_dataset --provider openai --label baseline`. Those bonus rows are stored in the database with parser reference flags in `raw_payload`, and each scrape gets a `ParserReferenceRun` record even when OpenAI finds zero bonuses.

Proxy options for scraping:

- Add `ScraperProxy` rows in Django admin. Set `geo` for a GEO-specific proxy, or leave `geo` empty for the default fallback proxy.
- Or set env fallbacks: `PROXY_URLS` for a comma-separated rotating pool, `GEO_PROXY_DEFAULT` for a default proxy, and `GEO_PROXY_MAP` for a JSON GEO map like `{"uk":"http://user:pass@host:port"}`.
- Supported proxy formats include `http://user:pass@host:port`, `socks5://user:pass@host:port`, `host:port`, and `host:port:user:pass`.

Webshare free proxy test flow:

1. Sign up at `https://www.webshare.io/features/free-proxy` and get your Webshare API token from the dashboard.
2. Set `WEBSHARE_API_TOKEN` in `.env`. Optionally set `WEBSHARE_COUNTRY_CODES=US,GB,FR` to import only those countries.
3. Restart web and sync the proxies:

```bash
WEB_PORT=8001 docker compose up -d web
docker compose exec -T web python manage.py sync_webshare_proxies
```

The sync command imports Webshare's proxy list into `ScraperProxy`, where the scraper can use it automatically.

No-verification public proxy test flow:

```bash
docker compose exec -T web python manage.py sync_public_proxy_list --limit 10
```

By default this uses ProxyScrape's public no-auth proxy API. These proxies are weak and unreliable; use them only to test that proxy wiring works.

If port `8000` is busy, run with another host port:

```bash
WEB_PORT=8001 docker compose up --build -d postgres redis web
```

Run local job workers when you want scraping/parsing automation:

```bash
docker compose --profile local-jobs up --build scraper-worker ai-worker beat
```

Manual commands:

```bash
python manage.py seed_startup_data
python manage.py scrape_all_casinos --force
python manage.py parse_pending_queue --provider script
python manage.py build_reference_dataset --provider openai --label baseline --limit 10
python manage.py evaluate_script_parser --limit 10
python manage.py run_telegram_bot
```

## Data Flow

1. `seed_startup_data` imports `bonus_scraping/geo-big.json` and `bonus_scraping/grouped_casinos_with_verticals_10.json`.
2. Scraping jobs store raw HTML in `ScrapedHistory` and create `AIParsingQueue` rows.
3. Parser jobs write approved/editable `Bonus` rows.
4. Telegram commands and notifications query the shared DB by GEO and user settings.

Telegram outbound links use a manually entered affiliate URL on the casino bonus page first, then fall back to the parsed direct bonus URL.
