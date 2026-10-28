from __future__ import annotations

import json
import os
from html import escape
from urllib import parse, request
from urllib.error import HTTPError, URLError

from lunch_finder.config import TelegramConfig
from lunch_finder.models import Location, RankedOffer


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self.token_env = config.bot_token_env
        self.chat_id_env = config.chat_id_env
        self.token = os.environ.get(config.bot_token_env)
        self.chat_id = os.environ.get(config.chat_id_env)
        if not self.token:
            raise RuntimeError(f"Missing Telegram variable: {self.token_env}")

    def send(self, offers: list[RankedOffer], office: Location) -> None:
        if not offers:
            return
        if not self.chat_id:
            raise RuntimeError(f"Missing Telegram variable: {self.chat_id_env}")
        assert self.token is not None
        payload = parse.urlencode(
            {
                "chat_id": self.chat_id,
                "text": format_digest(offers, office),
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode("utf-8")
        telegram_request = request.Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=payload,
            method="POST",
        )
        try:
            with request.urlopen(telegram_request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Telegram network error: {error.reason}") from error
        if not result.get("ok"):
            raise RuntimeError(f"Telegram send failed: {result}")

    def chat_candidates(self) -> list[tuple[str, str, str]]:
        assert self.token is not None
        updates_request = request.Request(
            f"https://api.telegram.org/bot{self.token}/getUpdates",
            headers={"Accept": "application/json"},
        )
        try:
            with request.urlopen(updates_request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram HTTP {error.code}: {detail}") from error
        except URLError as error:
            raise RuntimeError(f"Telegram network error: {error.reason}") from error
        if not result.get("ok"):
            raise RuntimeError(f"Telegram getUpdates failed: {result}")

        candidates: dict[str, tuple[str, str, str]] = {}
        for update in result.get("result", []):
            message = update.get("message") or update.get("channel_post") or {}
            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            if chat_id is None:
                continue
            title = chat.get("title") or chat.get("username") or chat.get("first_name") or "unknown"
            candidates[str(chat_id)] = (str(chat_id), str(chat.get("type", "unknown")), str(title))
        return list(candidates.values())


def format_digest(offers: list[RankedOffer], office: Location) -> str:
    lines = ["🍽️ <b>Lunch picks</b>", escape(offers[0].offer.menu_date.strftime("%A, %d %B"))]
    for index, ranked in enumerate(offers, start=1):
        offer = ranked.offer
        restaurant = offer.restaurant
        directions = (
            "https://www.google.com/maps/dir/?api=1&"
            + parse.urlencode(
                {
                    "origin": f"{office.latitude},{office.longitude}",
                    "destination": f"{restaurant.latitude},{restaurant.longitude}",
                    "travelmode": "walking",
                }
            )
        )
        price = f"≈€{offer.price_eur:.2f}" if offer.price_is_estimate else f"€{offer.price_eur:.2f}"
        rating = f"{restaurant.rating:.1f}" if restaurant.rating is not None else "n/a"
        source_label = "Menu / info" if offer.price_is_estimate else "Today's menu"
        lines.extend(
            (
                "",
                f"<b>{index}. {escape(offer.name)}</b>",
                f"{escape(restaurant.name)} · <b>{price}</b>",
                f"🚶 {ranked.walking_minutes} min · ⭐ {rating} · score {ranked.score:g}",
                f'<a href="{escape(directions, quote=True)}">Directions</a> · '
                f'<a href="{escape(offer.source_url, quote=True)}">{source_label}</a>',
            )
        )
    return "\n".join(lines)
