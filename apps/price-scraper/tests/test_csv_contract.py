"""The CSV columns are read by apps/platform vendor pricing; changing them breaks it.

If a change here is intended, update the platform's reader in the same commit.
"""

from price_scraper.__main__ import FIELDS

PUBLISHED_COLUMNS = [
    "store",
    "product_id",
    "name",
    "sku",
    "price",
    "regular_price",
    "sale_price",
    "currency",
    "in_stock",
    "categories",
    "url",
    "scraped_at",
]


def test_csv_columns_are_stable():
    assert FIELDS == PUBLISHED_COLUMNS
