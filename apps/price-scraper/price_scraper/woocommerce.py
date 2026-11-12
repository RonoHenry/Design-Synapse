"""Read a WooCommerce shop's public product catalogue through its Store API.

The Store API (``/wp-json/wc/store/v1/products``) is the same public feed the
shop's own pages use. It returns structured prices, so no HTML parsing is
needed. We fetch politely: one request at a time with a pause between pages.
"""

from __future__ import annotations

import html
import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

USER_AGENT = "Mozilla/5.0 (compatible; price-research-bot/0.1)"
PAGE_SIZE = 100


@dataclass(frozen=True)
class Product:
    """One product as listed by a shop at the time of scraping."""

    store: str
    product_id: int
    name: str
    sku: str
    price: Decimal
    regular_price: Decimal
    sale_price: Decimal | None
    currency: str
    in_stock: bool
    categories: str
    url: str
    scraped_at: str


def _money(raw: str | None, minor_unit: int) -> Decimal | None:
    """Convert a Store API price string in minor units (e.g. cents) to a Decimal."""
    if raw in (None, ""):
        return None
    return Decimal(raw) / (Decimal(10) ** minor_unit)


def parse_product(store: str, item: dict, scraped_at: str) -> Product | None:
    """Turn one Store API product record into a Product; None if it has no price."""
    prices = item.get("prices") or {}
    minor = int(prices.get("currency_minor_unit", 0))
    price = _money(prices.get("price"), minor)
    if price is None or price <= 0:
        return None
    regular = _money(prices.get("regular_price"), minor) or price
    sale = _money(prices.get("sale_price"), minor)
    return Product(
        store=store,
        product_id=int(item["id"]),
        name=html.unescape(item.get("name", "")).strip(),
        sku=item.get("sku") or "",
        price=price,
        regular_price=regular,
        sale_price=sale if sale is not None and sale < regular else None,
        currency=prices.get("currency_code", ""),
        in_stock=bool(item.get("is_in_stock", True)),
        categories="; ".join(
            html.unescape(c.get("name", "")) for c in item.get("categories", [])
        ),
        url=item.get("permalink", ""),
        scraped_at=scraped_at,
    )


def _get(url: str, timeout: float) -> tuple[list[dict], int]:
    # urlopen also accepts file:// and custom schemes; only ever fetch shops over HTTPS.
    if urllib.parse.urlsplit(url).scheme != "https":
        raise ValueError(f"refusing to fetch non-HTTPS URL: {url}")
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    # nosec B310: the scheme is checked above, so only https is ever opened.
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type:
            raise RuntimeError(
                f"{url} returned {content_type or 'no content type'}, not JSON "
                "(the site may block automated access)"
            )
        pages = int(resp.headers.get("X-WP-TotalPages", "1"))
        return json.loads(resp.read().decode("utf-8")), pages


def fetch_products(
    store: str,
    base_url: str,
    *,
    delay: float = 1.5,
    timeout: float = 30,
    get: Callable[[str, float], tuple[list[dict], int]] = _get,
    now: Callable[[], datetime] = datetime.now,
) -> Iterator[Product]:
    """Yield every priced product in a shop's catalogue, page by page."""
    scraped_at = now().astimezone().isoformat(timespec="seconds")
    page, pages = 1, 1
    while page <= pages:
        url = (
            f"{base_url.rstrip('/')}/wp-json/wc/store/v1/products"
            f"?per_page={PAGE_SIZE}&page={page}"
        )
        items, pages = get(url, timeout)
        for item in items:
            product = parse_product(store, item, scraped_at)
            if product is not None:
                yield product
        page += 1
        if page <= pages:
            time.sleep(delay)
