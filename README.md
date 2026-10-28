![Lunch Finder — A useful lunch shortlist, without the daily search.](docs/assets/banner.svg)

# Lunch Finder

A useful lunch shortlist, without the daily search.

[![CI](https://github.com/Fernise/lunch-finder/actions/workflows/ci.yml/badge.svg)](https://github.com/Fernise/lunch-finder/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-52646b)](LICENSE)

A configurable weekday lunch crawler that ranks nearby restaurant offers and sends a deduplicated Telegram digest.

**Technology:** Python · SQLite · HTML/PDF parsing · Telegram

## What it does

- Restaurant sources from published HTML, PDFs and structured menus.
- Ranking by menu confidence, price, rating and walking distance.
- One choice per restaurant and a configurable shortlist.
- SQLite notification deduplication and optional cron/systemd deployment.

## Project status

A configurable personal automation tool. The Vienna restaurant list is an illustrative configuration, not a claim of current menu availability, prices or opening hours. Network source formats can change; regular-menu fallbacks are marked as estimates.

## Quick start

Requires Python 3.11+.

```sh
git clone https://github.com/Fernise/lunch-finder.git
cd lunch-finder
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
cp config.example.json config.json
cp .env.example .env
```

Review the sample location and restaurant set before use. For a live menu fetch that prints a digest without sending Telegram:

```sh
python -m lunch_finder.cli --config config.json --dry-run
```

A dry run still fetches external menu sources and writes local crawl state; it only suppresses Telegram delivery and notification marks. Use the unit tests for a fully offline check.

The authenticated menu example references `LUNCH_MENU_BEARER_TOKEN` by environment-variable name. No provider token is bundled. Missing credentials skip that source with a configuration error before any authenticated request. See [configuration](docs/CONFIGURATION.md).

## Verification

```sh
python -m unittest discover -s tests -v
```

Offline tests cover parsing, closure notices, ranking, storage/deduplication and credential lookup. A real Telegram send is deliberately outside the test suite.

## Repository map

| Path | Responsibility |
| --- | --- |
| `lunch_finder/` | Sources, ranking, storage, notification and CLI modules |
| `tests/` | Offline parsing, ranking, credential and storage tests |
| `config.example.json` | Illustrative Vienna restaurant configuration |
| `deploy/` | Portable service/timer examples |
| `assets/` | Bot artwork |
| `docs/` | Configuration and architecture |

## Documentation

- [Verification record and limits](docs/VERIFICATION.md)
- [Architecture and data boundaries](docs/ARCHITECTURE.md)
- [Configuration](docs/CONFIGURATION.md)
- [Security policy](SECURITY.md)
- [Contribution guidance](CONTRIBUTING.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## License

Original project code is licensed under the [MIT License](LICENSE).

Third-party libraries and assets retain their own licenses.
