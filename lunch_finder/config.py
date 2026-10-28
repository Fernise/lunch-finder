from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from lunch_finder.models import Location, Restaurant


@dataclass(frozen=True)
class TelegramConfig:
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    chat_id_env: str = "TELEGRAM_CHAT_ID"


@dataclass(frozen=True)
class AppConfig:
    office: Location
    restaurants: tuple[Restaurant, ...]
    database_path: Path
    timezone: str = "Europe/Vienna"
    notification_limit: int = 5
    max_offer_price_eur: float = 25.0
    telegram: TelegramConfig = TelegramConfig()

    @classmethod
    def from_file(cls, path: Path) -> "AppConfig":
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        office = Location(**data["office"])
        restaurants = tuple(Restaurant(**item) for item in data["restaurants"])
        telegram = TelegramConfig(**data.get("telegram", {}))
        return cls(
            office=office,
            restaurants=restaurants,
            database_path=Path(data.get("database_path", "data/lunch_finder.sqlite3")),
            timezone=data.get("timezone", "Europe/Vienna"),
            notification_limit=int(data.get("notification_limit", 5)),
            max_offer_price_eur=float(data.get("max_offer_price_eur", 25.0)),
            telegram=telegram,
        )
