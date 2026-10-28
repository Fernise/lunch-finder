from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Location:
    name: str
    address: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class Restaurant:
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    rating: float | None = None
    review_count: int = 0
    price_level: int | None = None
    source_type: str = "none"
    source_url: str | None = None
    source_bearer_token: str | None = None
    menu_url: str | None = None
    source_start: str | None = None
    source_end: str | None = None
    source_items: tuple[str, ...] = ()
    curated_offer_name: str | None = None
    curated_price_eur: float | None = None
    open_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    enabled: bool = True
    source_bearer_token_env: str | None = None


@dataclass(frozen=True)
class Offer:
    restaurant: Restaurant
    name: str
    price_eur: float
    menu_date: date
    source_url: str
    fetched_at: datetime
    tags: tuple[str, ...] = field(default_factory=tuple)
    category: str = "main_course"
    price_is_estimate: bool = False

    @property
    def key(self) -> str:
        raw = "|".join(
            (
                self.restaurant.id,
                self.menu_date.isoformat(),
                self.name.casefold().strip(),
                f"{self.price_eur:.2f}",
            )
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class RankedOffer:
    offer: Offer
    score: float
    distance_m: int
    walking_minutes: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class CrawlFailure:
    restaurant_id: str
    restaurant_name: str
    error: str
