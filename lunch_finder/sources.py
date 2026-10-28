from __future__ import annotations

import os

import json
import re
from io import BytesIO
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lunch_finder.models import CrawlFailure, Offer, Restaurant


PRICE_RE = re.compile(
    r"(?:(?:EUR|€)\s*(?P<prefix>\d{1,3}(?:[.,]\d{1,2})?)|"
    r"(?P<suffix>\d{1,3}(?:[.,]\d{1,2})?)\s*(?:EUR|€))",
    re.IGNORECASE,
)
SKIP_LABELS = {
    "adresse",
    "address",
    "kontakt",
    "contact",
    "öffnungszeiten",
    "opening hours",
    "telefon",
    "phone",
    "reservieren",
    "book",
}


class VisibleTextParser(HTMLParser):
    block_tags = {
        "article",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "p",
        "section",
        "td",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self._buffer: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
            return
        if not self._ignored_depth and tag in self.block_tags:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if not self._ignored_depth and tag in self.block_tags:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            clean = " ".join(data.split())
            if clean:
                self._buffer.append(clean)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        line = " ".join(self._buffer).strip()
        if line and (not self.lines or self.lines[-1] != line):
            self.lines.append(line)
        self._buffer.clear()


def fetch_html(url: str, timeout: int = 25) -> str:
    return _fetch_text(url, "text/html,application/xhtml+xml", None, timeout)


def fetch_json(url: str, bearer_token: str | None = None, timeout: int = 25) -> dict:
    text = _fetch_text(url, "application/json", bearer_token, timeout)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid JSON from {url}") from error
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected JSON payload from {url}")
    return data


def fetch_bytes(url: str, timeout: int = 25) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "TTTechLunchFinder/0.1 (+internal lunch menu monitor)",
            "Accept": "application/pdf",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} for {url}") from error
    except URLError as error:
        raise RuntimeError(f"Network error for {url}: {error.reason}") from error


def _fetch_text(
    url: str,
    accept: str,
    bearer_token: str | None,
    timeout: int,
) -> str:
    headers = {
        "User-Agent": "TTTechLunchFinder/0.1 (+internal lunch menu monitor)",
        "Accept": accept,
    }
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    request = Request(
        url,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as error:
        raise RuntimeError(f"HTTP {error.code} for {url}") from error
    except URLError as error:
        raise RuntimeError(f"Network error for {url}: {error.reason}") from error


def extract_offers_from_contentful(
    restaurant: Restaurant,
    payload: dict,
    menu_date: date,
    fetched_at: datetime,
    max_price_eur: float,
) -> list[Offer]:
    items = payload.get("items") or []
    included = (payload.get("includes") or {}).get("Entry") or []
    if not items or not isinstance(items[0], dict):
        return []

    entries = {
        entry.get("sys", {}).get("id"): entry.get("fields", {})
        for entry in included
        if isinstance(entry, dict) and entry.get("sys", {}).get("id")
    }
    menu_fields = items[0].get("fields", {})
    offers: list[Offer] = []
    seen: set[tuple[str, float]] = set()
    categories = {
        "mainCourses": "main_course",
        "soups": "soup",
        "salads": "salad",
        "desserts": "dessert",
    }
    for contentful_category, offer_category in categories.items():
        for reference in menu_fields.get(contentful_category, []) or []:
            entry_id = reference.get("sys", {}).get("id")
            fields = entries.get(entry_id, {})
            label = str(fields.get("german") or fields.get("english") or "").strip()
            price_text = str(fields.get("price") or "")
            match = PRICE_RE.search(price_text)
            if not _usable_label(label) or not match:
                continue
            price = float((match.group("prefix") or match.group("suffix")).replace(",", "."))
            if price < 3.0 or price > max_price_eur:
                continue
            normalized = (label.casefold(), price)
            if normalized in seen:
                continue
            seen.add(normalized)
            tag_text = f"{label} {fields.get('details') or ''}"
            offers.append(
                Offer(
                    restaurant=restaurant,
                    name=label,
                    price_eur=price,
                    menu_date=menu_date,
                    source_url=restaurant.menu_url or restaurant.source_url or "",
                    fetched_at=fetched_at,
                    tags=_infer_tags(tag_text),
                    category=offer_category,
                )
            )
    return offers


def contentful_is_closed(payload: dict, menu_date: date) -> bool:
    items = payload.get("items") or []
    if not items or not isinstance(items[0], dict):
        return False
    notice = str(items[0].get("fields", {}).get("notice") or "").casefold()
    if "geschlossen" not in notice:
        return False
    months = {
        "januar": 1,
        "februar": 2,
        "märz": 3,
        "maerz": 3,
        "april": 4,
        "mai": 5,
        "juni": 6,
        "juli": 7,
        "august": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "dezember": 12,
    }
    range_match = re.search(
        r"(?:von\s+)?(\d{1,2})\.\s+bis\s+(\d{1,2})\.\s+([a-zä]+)",
        notice,
    )
    if range_match:
        start_day, end_day, month_name = range_match.groups()
        if months.get(month_name) == menu_date.month:
            return int(start_day) <= menu_date.day <= int(end_day)
    weekdays = (
        "montag",
        "dienstag",
        "mittwoch",
        "donnerstag",
        "freitag",
        "samstag",
        "sonntag",
    )
    weekday = weekdays[menu_date.weekday()]
    day_pattern = rf"\b0?{menu_date.day}\."
    return weekday in notice and re.search(day_pattern, notice) is not None


def extract_offers_from_shared_price_text(
    restaurant: Restaurant,
    text: str,
    menu_date: date,
    fetched_at: datetime,
    max_price_eur: float,
) -> list[Offer]:
    prices = [
        float((match.group("prefix") or match.group("suffix")).replace(",", "."))
        for match in PRICE_RE.finditer(text)
    ]
    valid_prices = [price for price in prices if 3.0 <= price <= max_price_eur]
    if not valid_prices:
        return []
    price = min(valid_prices)
    folded_text = " ".join(text.casefold().split())
    offers: list[Offer] = []
    for item in restaurant.source_items:
        if " ".join(item.casefold().split()) not in folded_text:
            continue
        offers.append(
            Offer(
                restaurant=restaurant,
                name=item,
                price_eur=price,
                menu_date=menu_date,
                source_url=restaurant.menu_url or restaurant.source_url or "",
                fetched_at=fetched_at,
                tags=_infer_tags(item),
            )
        )
    return offers


def extract_offers_from_pdf(
    restaurant: Restaurant,
    pdf_data: bytes,
    menu_date: date,
    fetched_at: datetime,
    max_price_eur: float,
) -> list[Offer]:
    try:
        from pypdf import PdfReader

        text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_data)).pages)
    except Exception as error:
        raise RuntimeError("Could not extract text from PDF menu") from error
    return extract_offers_from_shared_price_text(
        restaurant,
        text,
        menu_date,
        fetched_at,
        max_price_eur,
    )


def extract_offers_from_html(
    restaurant: Restaurant,
    html: str,
    menu_date: date,
    fetched_at: datetime,
    max_price_eur: float,
) -> list[Offer]:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    lines = _scope_lines(parser.lines, restaurant.source_start, restaurant.source_end)

    offers: list[Offer] = []
    seen: set[tuple[str, float]] = set()
    for index, line in enumerate(lines):
        match = PRICE_RE.search(line)
        if not match:
            continue
        price = float((match.group("prefix") or match.group("suffix")).replace(",", "."))
        if price < 3.0 or price > max_price_eur:
            continue

        label = PRICE_RE.sub("", line).strip(" ·|:-–—\t")
        if not _usable_label(label):
            label = _previous_label(lines, index)
        if not _usable_label(label):
            continue

        normalized = (label.casefold(), price)
        if normalized in seen:
            continue
        seen.add(normalized)
        offers.append(
            Offer(
                restaurant=restaurant,
                name=label,
                price_eur=price,
                menu_date=menu_date,
                source_url=restaurant.menu_url or restaurant.source_url or "",
                fetched_at=fetched_at,
                tags=_infer_tags(label),
            )
        )
    return offers


def crawl_restaurants(
    restaurants: tuple[Restaurant, ...],
    menu_date: date,
    fetched_at: datetime,
    max_price_eur: float,
) -> tuple[list[Offer], list[CrawlFailure]]:
    offers: list[Offer] = []
    failures: list[CrawlFailure] = []
    for restaurant in restaurants:
        if not restaurant.enabled or restaurant.source_type == "none":
            continue
        if menu_date.weekday() not in restaurant.open_weekdays:
            continue
        if restaurant.source_type == "curated":
            if (
                not restaurant.curated_offer_name
                or restaurant.curated_price_eur is None
                or not restaurant.source_url
            ):
                failures.append(
                    CrawlFailure(restaurant.id, restaurant.name, "incomplete curated offer")
                )
                continue
            if restaurant.curated_price_eur > max_price_eur:
                continue
            offers.append(
                Offer(
                    restaurant=restaurant,
                    name=restaurant.curated_offer_name,
                    price_eur=restaurant.curated_price_eur,
                    menu_date=menu_date,
                    source_url=restaurant.menu_url or restaurant.source_url,
                    fetched_at=fetched_at,
                    tags=_infer_tags(restaurant.curated_offer_name),
                    price_is_estimate=True,
                )
            )
            continue
        if restaurant.source_type not in {"html", "contentful", "pdf"} or not restaurant.source_url:
            failures.append(
                CrawlFailure(restaurant.id, restaurant.name, "unsupported or missing source")
            )
            continue
        try:
            if restaurant.source_type == "html":
                html = fetch_html(restaurant.source_url)
                parsed = extract_offers_from_html(
                    restaurant,
                    html,
                    menu_date,
                    fetched_at,
                    max_price_eur,
                )
            elif restaurant.source_type == "contentful":
                token = restaurant.source_bearer_token
                if restaurant.source_bearer_token_env:
                    token = os.environ.get(restaurant.source_bearer_token_env)
                    if not token:
                        raise RuntimeError(
                            f"Configure {restaurant.source_bearer_token_env} for this menu source"
                        )
                payload = fetch_json(
                    restaurant.source_url,
                    bearer_token=token,
                )
                if contentful_is_closed(payload, menu_date):
                    continue
                parsed = extract_offers_from_contentful(
                    restaurant,
                    payload,
                    menu_date,
                    fetched_at,
                    max_price_eur,
                )
            else:
                parsed = extract_offers_from_pdf(
                    restaurant,
                    fetch_bytes(restaurant.source_url),
                    menu_date,
                    fetched_at,
                    max_price_eur,
                )
            if not parsed:
                failures.append(
                    CrawlFailure(restaurant.id, restaurant.name, "no priced menu items found")
                )
            offers.extend(parsed)
        except RuntimeError as error:
            failures.append(CrawlFailure(restaurant.id, restaurant.name, str(error)))
    return offers, failures


def _scope_lines(lines: list[str], start: str | None, end: str | None) -> list[str]:
    start_index = 0
    end_index = len(lines)
    if start:
        needle = start.casefold()
        start_index = next(
            (index + 1 for index, line in enumerate(lines) if needle in line.casefold()),
            0,
        )
    if end:
        needle = end.casefold()
        end_index = next(
            (
                index
                for index, line in enumerate(lines[start_index:], start=start_index)
                if needle in line.casefold()
            ),
            len(lines),
        )
    return lines[start_index:end_index]


def _previous_label(lines: list[str], index: int) -> str:
    for candidate in reversed(lines[max(0, index - 3) : index]):
        candidate = candidate.strip(" ·|:-–—\t")
        if _usable_label(candidate) and not PRICE_RE.search(candidate):
            return candidate
    return ""


def _usable_label(label: str) -> bool:
    if not 3 <= len(label) <= 180:
        return False
    if label.casefold() in SKIP_LABELS:
        return False
    if not any(character.isalpha() for character in label):
        return False
    return True


def _infer_tags(label: str) -> tuple[str, ...]:
    folded = label.casefold()
    tags: list[str] = []
    if "vegan" in folded:
        tags.append("vegan")
    elif "vegetar" in folded or "veggie" in folded:
        tags.append("vegetarian")
    if "glutenfrei" in folded or "gluten-free" in folded:
        tags.append("gluten-free")
    if "laktosefrei" in folded or "lactose-free" in folded:
        tags.append("lactose-free")
    return tuple(tags)
