"""Offline tests: Store API records shaped like the live responses seen 2026-11-12."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from price_scraper.woocommerce import _get, fetch_products, parse_product

WHEN = "2026-11-12T21:00:00+03:00"


def record(**overrides):
    item = {
        "id": 101,
        "name": "Bamburi Fundi Cement 50Kg &#8211; Nairobi",
        "sku": "BFC50",
        "permalink": "https://shop.example/product/cement/",
        "is_in_stock": True,
        "categories": [{"name": "Cement &amp; Concrete"}],
        "prices": {
            "price": "79000",
            "regular_price": "79000",
            "sale_price": "79000",
            "currency_code": "KES",
            "currency_minor_unit": 2,
        },
    }
    item.update(overrides)
    return item


def test_price_in_minor_units_becomes_shillings():
    p = parse_product("shop", record(), WHEN)
    assert p.price == Decimal("790")
    assert p.currency == "KES"
    assert p.sale_price is None  # sale equal to regular is not a sale


def test_html_entities_are_decoded():
    p = parse_product("shop", record(), WHEN)
    assert p.name == "Bamburi Fundi Cement 50Kg – Nairobi"
    assert p.categories == "Cement & Concrete"


def test_sale_price_kept_when_lower():
    prices = {
        "price": "70000",
        "regular_price": "79000",
        "sale_price": "70000",
        "currency_code": "KES",
        "currency_minor_unit": 2,
    }
    p = parse_product("shop", record(prices=prices), WHEN)
    assert (p.price, p.regular_price, p.sale_price) == (
        Decimal("700"),
        Decimal("790"),
        Decimal("700"),
    )


def test_products_without_a_price_are_skipped():
    no_price = {"price": "", "currency_code": "KES", "currency_minor_unit": 2}
    assert parse_product("shop", record(prices=no_price), WHEN) is None
    zero = {"price": "0", "currency_code": "KES", "currency_minor_unit": 2}
    assert parse_product("shop", record(prices=zero), WHEN) is None


def test_fetch_follows_every_page():
    pages = {1: [record(id=1), record(id=2)], 2: [record(id=3)]}
    requested = []

    def fake_get(url, timeout):
        page = int(url.rsplit("page=", 1)[1])
        requested.append(page)
        return pages[page], 2

    products = list(
        fetch_products(
            "shop",
            "https://shop.example/",
            delay=0,
            get=fake_get,
            now=lambda: datetime(2026, 11, 12, 18, tzinfo=timezone.utc),
        )
    )
    assert requested == [1, 2]
    assert [p.product_id for p in products] == [1, 2, 3]
    assert requested and products[0].url.startswith("https://shop.example/")


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "http://shop.example/", "ftp://shop.example/"]
)
def test_only_https_urls_are_fetched(url):
    with pytest.raises(ValueError, match="non-HTTPS"):
        _get(url, timeout=1)
