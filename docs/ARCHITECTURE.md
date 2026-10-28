# Lunch Finder — architecture

A configurable weekday lunch crawler that ranks nearby restaurant offers and sends a deduplicated Telegram digest.

## Code boundaries

- **lunch_finder/:** Sources, ranking, storage, notification and CLI modules.
- **tests/:** Offline parsing, ranking, credential and storage tests.
- **config.example.json:** Illustrative Vienna restaurant configuration.
- **deploy/:** Portable service/timer examples.
- **assets/:** Bot artwork.
- **docs/:** Configuration and architecture.

## Data boundary

This public repository contains application source and fictional test inputs. Personal/operational state belongs in ignored local storage or separately configured services. Test results establish the behavior exercised by the suite; they do not certify live integrations, product efficacy or deployment readiness.

See the README for implementation status and `CONFIGURATION.md` for provider-specific requirements.
