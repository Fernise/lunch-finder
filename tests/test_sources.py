from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from lunch_finder.models import Restaurant
from lunch_finder.sources import (
    crawl_restaurants,
    contentful_is_closed,
    extract_offers_from_contentful,
    extract_offers_from_html,
    extract_offers_from_shared_price_text,
)


class SourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.restaurant = Restaurant(
            id="test",
            name="Test Restaurant",
            address="Testgasse 1",
            latitude=48.19,
            longitude=16.36,
            source_type="html",
            source_url="https://example.test/menu",
            source_start="Lunch",
            source_end="Drinks",
        )

    def test_extracts_same_line_and_separate_prices(self) -> None:
        html = """
        <h2>Lunch</h2>
        <p>Vegetarian curry <strong>€ 10,90</strong></p>
        <h3>Chicken with rice</h3><p>12.50 EUR</p>
        <h2>Drinks</h2><p>Lemonade € 4,50</p>
        """
        offers = extract_offers_from_html(
            self.restaurant,
            html,
            date(2026, 8, 6),
            datetime(2026, 8, 6, tzinfo=timezone.utc),
            25,
        )
        self.assertEqual([offer.name for offer in offers], ["Vegetarian curry", "Chicken with rice"])
        self.assertEqual([offer.price_eur for offer in offers], [10.9, 12.5])
        self.assertEqual(offers[0].tags, ("vegetarian",))

    def test_filters_expensive_items(self) -> None:
        html = "<h2>Lunch</h2><p>Tasting menu € 75</p><h2>Drinks</h2>"
        offers = extract_offers_from_html(
            self.restaurant,
            html,
            date(2026, 8, 6),
            datetime(2026, 8, 6, tzinfo=timezone.utc),
            25,
        )
        self.assertEqual(offers, [])

    def test_extracts_linked_contentful_menu_entries(self) -> None:
        restaurant = Restaurant(
            id="fein",
            name="Fein Essen",
            address="Example 2",
            latitude=48.2,
            longitude=16.3,
            source_type="contentful",
            source_url="https://cdn.example.test/entries",
            menu_url="https://example.test/menu",
        )
        payload = {
            "items": [{"fields": {"mainCourses": [{"sys": {"id": "dish-1"}}]}}],
            "includes": {
                "Entry": [
                    {
                        "sys": {"id": "dish-1"},
                        "fields": {
                            "german": "Kichererbsen-Curry",
                            "price": "€ 10,90",
                            "details": "GLUTENFREI, VEGAN",
                        },
                    }
                ]
            },
        }

        offers = extract_offers_from_contentful(
            restaurant,
            payload,
            date(2026, 8, 6),
            datetime(2026, 8, 6, 9, tzinfo=timezone.utc),
            25,
        )

        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].name, "Kichererbsen-Curry")
        self.assertEqual(offers[0].price_eur, 10.9)
        self.assertEqual(offers[0].tags, ("vegan", "gluten-free"))
        self.assertEqual(offers[0].category, "main_course")
        self.assertEqual(offers[0].source_url, "https://example.test/menu")

    def test_contentful_notice_closes_only_the_matching_date(self) -> None:
        payload = {
            "items": [
                {"fields": {"notice": "Freitag 07. August geschlossen"}}
            ]
        }

        self.assertTrue(contentful_is_closed(payload, date(2026, 8, 7)))
        self.assertFalse(contentful_is_closed(payload, date(2026, 8, 6)))

    def test_contentful_vacation_range_closes_matching_dates(self) -> None:
        payload = {
            "items": [
                {
                    "fields": {
                        "notice": "Von 07. bis 21. August wegen Urlaub geschlossen."
                    }
                }
            ]
        }

        self.assertTrue(contentful_is_closed(payload, date(2026, 8, 7)))
        self.assertTrue(contentful_is_closed(payload, date(2026, 8, 21)))
        self.assertFalse(contentful_is_closed(payload, date(2026, 8, 22)))

    def test_extracts_configured_items_with_shared_pdf_price(self) -> None:
        restaurant = Restaurant(
            id="lunch_pdf",
            name="Lunch PDF",
            address="Example 3",
            latitude=48.2,
            longitude=16.3,
            source_type="pdf",
            source_url="https://example.test/lunch.pdf",
            source_items=("Veggie Wok", "Crispy Chicken"),
        )
        text = "LUNCH SPECIAL Veggie Wok Crispy Chicken € 12,90"

        offers = extract_offers_from_shared_price_text(
            restaurant,
            text,
            date(2026, 8, 7),
            datetime(2026, 8, 7, tzinfo=timezone.utc),
            25,
        )

        self.assertEqual([offer.name for offer in offers], ["Veggie Wok", "Crispy Chicken"])
        self.assertEqual([offer.price_eur for offer in offers], [12.9, 12.9])

    def test_curated_restaurant_creates_approximate_offer(self) -> None:
        restaurant = Restaurant(
            id="curated",
            name="Curated Lunch",
            address="Example 4",
            latitude=48.2,
            longitude=16.3,
            source_type="curated",
            source_url="https://example.test/menu",
            curated_offer_name="Falafel plate",
            curated_price_eur=10.9,
            open_weekdays=(0, 1, 2, 3, 4),
        )

        offers, failures = crawl_restaurants(
            (restaurant,),
            date(2026, 8, 7),
            datetime(2026, 8, 7, tzinfo=timezone.utc),
            25,
        )

        self.assertEqual(failures, [])
        self.assertEqual(len(offers), 1)
        self.assertTrue(offers[0].price_is_estimate)


if __name__ == "__main__":
    unittest.main()
