"""Supplier price lists, read from the price scraper's CSV snapshots."""

from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, PrivateAttr

# Columns of the apps/price-scraper CSV that this reader uses. The scraper pins
# its full column set in tests/test_csv_contract.py; change the two together.
COLUMNS = (
    "store",
    "product_id",
    "name",
    "price",
    "currency",
    "in_stock",
    "url",
    "scraped_at",
)


class Product(BaseModel):
    """One supplier product and its published price."""

    store: str
    product_id: int
    name: str
    price: Decimal
    currency: str
    in_stock: bool
    url: str
    scraped_at: datetime


class PriceList(BaseModel):
    """Supplier products from one price snapshot, keyed by store and product ID."""

    source: str
    products: list[Product]
    _index: dict[tuple[str, int], Product] = PrivateAttr(default_factory=dict)

    def model_post_init(self, context: Any, /) -> None:
        """Index the products by store and product ID."""
        self._index = {(p.store, p.product_id): p for p in self.products}

    def get(self, store: str, product_id: int) -> Product | None:
        """Return the product, or None if this snapshot does not list it."""
        return self._index.get((store, product_id))


def load_price_list(path: str | Path) -> PriceList:
    """Load a price snapshot written by apps/price-scraper."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(
                f"{path.name} is missing price columns: {', '.join(missing)}"
            )
        products = [
            Product.model_validate({c: row[c] for c in COLUMNS}) for row in reader
        ]
    return PriceList(source=path.name, products=products)
