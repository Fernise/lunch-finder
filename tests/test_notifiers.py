from __future__ import annotations

import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from lunch_finder.config import TelegramConfig
from lunch_finder.models import Location, Offer, RankedOffer, Restaurant
from lunch_finder.notifiers import TelegramNotifier, format_digest


class NotifierTests(unittest.TestCase):
    def test_chat_id_is_not_required_for_notifier_initialization(self) -> None:
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}, clear=True):
            notifier = TelegramNotifier(TelegramConfig())

        self.assertIsNone(notifier.chat_id)

    def test_digest_contains_escaped_offer_and_directions(self) -> None:
        office = Location("Office", "Address", 48.19504, 16.36139)
        restaurant = Restaurant("r", "R & B", "Address", 48.196, 16.362, 4.8, 100)
        offer = Offer(
            restaurant,
            "Fish & chips",
            11.9,
            date(2026, 8, 6),
            "https://example.test/menu?a=1&b=2",
            datetime(2026, 8, 6, tzinfo=timezone.utc),
        )
        text = format_digest([RankedOffer(offer, 80, 150, 2, ())], office)
        self.assertIn("Fish &amp; chips", text)
        self.assertIn("google.com/maps/dir", text)
        self.assertIn("R &amp; B", text)

    def test_digest_marks_curated_price_as_approximate(self) -> None:
        office = Location("Office", "Address", 48.19504, 16.36139)
        restaurant = Restaurant("r", "Lunch place", "Address", 48.196, 16.362, 4.7, 50)
        offer = Offer(
            restaurant,
            "Regular menu option",
            12.9,
            date(2026, 8, 6),
            "https://example.test/menu",
            datetime(2026, 8, 6, tzinfo=timezone.utc),
            price_is_estimate=True,
        )

        text = format_digest([RankedOffer(offer, 75, 150, 2, ())], office)

        self.assertIn("≈€12.90", text)
        self.assertIn("Menu / info", text)


if __name__ == "__main__":
    unittest.main()
