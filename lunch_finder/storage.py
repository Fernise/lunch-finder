from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from lunch_finder.models import RankedOffer


class LunchStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS offers (
                offer_key TEXT PRIMARY KEY,
                menu_date TEXT NOT NULL,
                restaurant_id TEXT NOT NULL,
                restaurant_name TEXT NOT NULL,
                offer_name TEXT NOT NULL,
                price_eur REAL NOT NULL,
                score REAL NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                notification_count INTEGER NOT NULL DEFAULT 0,
                payload TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def has_notified(self, offer_key: str) -> bool:
        row = self.connection.execute(
            "SELECT notification_count FROM offers WHERE offer_key = ?", (offer_key,)
        ).fetchone()
        return bool(row and row[0] > 0)

    def record(self, ranked: RankedOffer, notified: bool) -> None:
        offer = ranked.offer
        seen_at = offer.fetched_at.isoformat()
        payload = json.dumps(
            {
                "distance_m": ranked.distance_m,
                "walking_minutes": ranked.walking_minutes,
                "reasons": ranked.reasons,
                "tags": offer.tags,
                "source_url": offer.source_url,
                "price_is_estimate": offer.price_is_estimate,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.connection.execute(
            """
            INSERT INTO offers (
                offer_key, menu_date, restaurant_id, restaurant_name, offer_name,
                price_eur, score, first_seen_at, last_seen_at, notification_count, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(offer_key) DO UPDATE SET
                score = excluded.score,
                last_seen_at = excluded.last_seen_at,
                notification_count = offers.notification_count + excluded.notification_count,
                payload = excluded.payload
            """,
            (
                offer.key,
                offer.menu_date.isoformat(),
                offer.restaurant.id,
                offer.restaurant.name,
                offer.name,
                offer.price_eur,
                ranked.score,
                seen_at,
                seen_at,
                1 if notified else 0,
                payload,
            ),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "LunchStore":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
