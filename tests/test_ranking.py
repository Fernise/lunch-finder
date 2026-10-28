from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from lunch_finder.models import Location, Offer, Restaurant
from lunch_finder.models import RankedOffer
from lunch_finder.ranking import rank_offers, select_best_restaurants


class RankingTests(unittest.TestCase):
    def test_closer_offer_wins_when_other_inputs_match(self) -> None:
        office = Location("Office", "Address", 48.19504, 16.36139)
        close = Restaurant("close", "Close", "A", 48.1951, 16.3614, 4.7, 500)
        far = Restaurant("far", "Far", "B", 48.21, 16.38, 4.7, 500)
        now = datetime(2026, 8, 6, tzinfo=timezone.utc)
        offers = [
            Offer(far, "Dish", 12, date(2026, 8, 6), "https://far", now),
            Offer(close, "Dish", 12, date(2026, 8, 6), "https://close", now),
        ]
        ranked = rank_offers(offers, office)
        self.assertEqual(ranked[0].offer.restaurant.id, "close")

    def test_main_course_ranks_above_equally_priced_soup(self) -> None:
        office = Location("Office", "Address", 48.19504, 16.36139)
        restaurant = Restaurant("place", "Place", "A", 48.1951, 16.3614, 4.7, 500)
        now = datetime(2026, 8, 6, tzinfo=timezone.utc)
        offers = [
            Offer(restaurant, "Soup", 10, date(2026, 8, 6), "https://menu", now, category="soup"),
            Offer(restaurant, "Curry", 10, date(2026, 8, 6), "https://menu", now),
        ]

        ranked = rank_offers(offers, office)

        self.assertEqual(ranked[0].offer.name, "Curry")

    def test_selection_returns_only_best_offer_per_restaurant(self) -> None:
        office = Location("Office", "Address", 48.19504, 16.36139)
        first = Restaurant("first", "First", "A", 48.1951, 16.3614)
        second = Restaurant("second", "Second", "B", 48.1952, 16.3615)
        now = datetime(2026, 8, 6, tzinfo=timezone.utc)
        ranked = [
            RankedOffer(
                Offer(first, f"First {index}", 10, date(2026, 8, 6), "https://menu", now),
                100 - index,
                10,
                1,
                (),
            )
            for index in range(4)
        ]
        ranked.append(
            RankedOffer(
                Offer(second, "Second 1", 10, date(2026, 8, 6), "https://menu", now),
                90,
                20,
                1,
                (),
            )
        )

        selected = select_best_restaurants(ranked, limit=4)

        self.assertEqual([item.offer.name for item in selected], ["First 0", "Second 1"])


if __name__ == "__main__":
    unittest.main()
