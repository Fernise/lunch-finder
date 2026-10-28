import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from lunch_finder.models import Restaurant
from lunch_finder.sources import crawl_restaurants


class SourceCredentialTests(unittest.TestCase):
    def setUp(self):
        self.restaurant = Restaurant(
            id="demo", name="Demo", address="Vienna", latitude=48.2,
            longitude=16.3, source_type="contentful",
            source_url="https://example.com/menu",
            source_bearer_token_env="DEMO_MENU_TOKEN",
        )
        self.day = date(2026, 10, 26)
        self.now = datetime(2026, 10, 26, tzinfo=timezone.utc)

    @patch("lunch_finder.sources.fetch_json")
    def test_missing_credential_fails_before_network_request(self, fetch):
        with patch.dict(os.environ, {}, clear=True):
            offers, failures = crawl_restaurants(
                [self.restaurant], self.day, self.now, 25
            )
        self.assertEqual(offers, [])
        self.assertEqual(len(failures), 1)
        self.assertIn("DEMO_MENU_TOKEN", failures[0].error)
        fetch.assert_not_called()

    @patch("lunch_finder.sources.fetch_json", return_value={})
    def test_credential_is_read_from_environment(self, fetch):
        with patch.dict(os.environ, {"DEMO_MENU_TOKEN": "synthetic-menu-value"}):
            crawl_restaurants([self.restaurant], self.day, self.now, 25)
        fetch.assert_called_once_with(
            "https://example.com/menu", bearer_token="synthetic-menu-value"
        )
