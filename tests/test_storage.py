from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from lunch_finder.models import Offer, RankedOffer, Restaurant
from lunch_finder.storage import LunchStore


class StorageTests(unittest.TestCase):
    def test_notification_deduplication(self) -> None:
        restaurant = Restaurant("r", "Restaurant", "Address", 48.19, 16.36)
        offer = Offer(
            restaurant,
            "Lunch",
            10.9,
            date(2026, 8, 6),
            "https://example.test",
            datetime(2026, 8, 6, tzinfo=timezone.utc),
        )
        ranked = RankedOffer(offer, 90, 100, 2, ("nearby",))
        with tempfile.TemporaryDirectory() as directory:
            with LunchStore(Path(directory) / "lunch.sqlite3") as store:
                self.assertFalse(store.has_notified(offer.key))
                store.record(ranked, notified=True)
                self.assertTrue(store.has_notified(offer.key))


if __name__ == "__main__":
    unittest.main()
