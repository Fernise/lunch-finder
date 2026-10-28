from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from lunch_finder.config import AppConfig
from lunch_finder.models import CrawlFailure, RankedOffer
from lunch_finder.notifiers import TelegramNotifier, format_digest
from lunch_finder.ranking import rank_offers, select_best_restaurants
from lunch_finder.sources import crawl_restaurants
from lunch_finder.storage import LunchStore


def run_once(
    config: AppConfig,
    *,
    dry_run: bool = False,
) -> tuple[list[RankedOffer], list[CrawlFailure]]:
    now = datetime.now(ZoneInfo(config.timezone))
    offers, failures = crawl_restaurants(
        config.restaurants,
        now.date(),
        now,
        config.max_offer_price_eur,
    )
    ranked = rank_offers(offers, config.office)

    with LunchStore(config.database_path) as store:
        restaurant_picks = select_best_restaurants(ranked, len(config.restaurants))
        new_offers = [
            item for item in restaurant_picks if not store.has_notified(item.offer.key)
        ]
        selected = new_offers[: config.notification_limit]
        if dry_run:
            if selected:
                print(format_digest(selected, config.office))
            else:
                print("No new priced offers found.")
        elif selected:
            TelegramNotifier(config.telegram).send(selected, config.office)

        notified_keys = {item.offer.key for item in selected} if not dry_run else set()
        for item in ranked:
            store.record(item, notified=item.offer.key in notified_keys)

    return selected, failures
