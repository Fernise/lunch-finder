from __future__ import annotations

import math

from lunch_finder.models import Location, Offer, RankedOffer


def rank_offers(offers: list[Offer], office: Location) -> list[RankedOffer]:
    ranked: list[RankedOffer] = []
    for offer in offers:
        restaurant = offer.restaurant
        distance = round(
            haversine_m(
                office.latitude,
                office.longitude,
                restaurant.latitude,
                restaurant.longitude,
            )
        )
        walking_minutes = max(1, math.ceil(distance / 75))
        rating = restaurant.rating or 4.0
        rating_points = max(0.0, (rating - 3.0) * 18.0)
        review_points = min(12.0, math.log10(max(1, restaurant.review_count)) * 4.0)
        distance_points = max(0.0, 22.0 - walking_minutes * 2.0)
        value_points = max(0.0, 22.0 - offer.price_eur)
        dietary_points = 2.0 if offer.tags else 0.0
        live_menu_points = 4.0 if not offer.price_is_estimate else 0.0
        meal_points = {
            "main_course": 8.0,
            "salad": 2.0,
            "soup": 0.0,
            "dessert": -2.0,
        }.get(offer.category, 0.0)
        score = round(
            rating_points
            + review_points
            + distance_points
            + value_points
            + dietary_points
            + live_menu_points
            + meal_points,
            1,
        )
        reasons = (
            f"{walking_minutes} min walk",
            f"{rating:.1f}★ from {restaurant.review_count} reviews",
            f"€{offer.price_eur:.2f}",
        )
        ranked.append(
            RankedOffer(
                offer=offer,
                score=score,
                distance_m=distance,
                walking_minutes=walking_minutes,
                reasons=reasons,
            )
        )
    return sorted(ranked, key=lambda item: (-item.score, item.offer.price_eur))


def select_best_restaurants(
    ranked: list[RankedOffer],
    limit: int,
) -> list[RankedOffer]:
    selected: list[RankedOffer] = []
    seen_restaurants: set[str] = set()
    for item in ranked:
        restaurant_id = item.offer.restaurant.id
        if restaurant_id in seen_restaurants:
            continue
        selected.append(item)
        seen_restaurants.add(restaurant_id)
        if len(selected) >= limit:
            break
    return selected


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
