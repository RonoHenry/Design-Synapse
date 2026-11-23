"""Pricing a takeoff's material schedule against supplier products."""

from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from ..quantities import MaterialLine, TakeoffResult
from .prices import PriceList, Product
from .product_map import ProductMap, ProductRef

NOTES = [
    "Prices are suppliers' published online prices, including any sale "
    "discount, on the date shown for each line. They exclude delivery, "
    "labour, plant, overheads and profit.",
    "Quantities are rounded up to whole supplier packs.",
]


class Offer(BaseModel):
    """The supplier product chosen to price one material."""

    store: str
    product_id: int
    product: str
    url: str
    in_stock: bool
    priced_at: datetime
    pack: float = Field(description="Material units supplied by one product.")
    packs: int = Field(description="Number of products to buy.")
    pack_price: Decimal
    amount: Decimal


class ScheduleLine(BaseModel):
    """One material, with its offer or the reason it is unpriced."""

    key: str
    name: str
    unit: str
    quantity: float = Field(description="Quantity to buy, including wastage.")
    sources: list[str]
    offer: Offer | None = None
    unpriced_reason: str | None = None


class PricedSchedule(BaseModel):
    """Material schedule for one building, priced against supplier products."""

    building: str
    rate_table: str
    product_map: str
    price_list: str
    currency: str
    rates_verified: bool
    product_map_verified: bool
    lines: list[ScheduleLine]
    priced_total: Decimal = Field(
        description="Sum of the priced lines. Unpriced materials are excluded."
    )
    notes: list[str] = []

    def line(self, key: str) -> ScheduleLine:
        """Look up a line by material key."""
        for line in self.lines:
            if line.key == key:
                return line
        raise KeyError(key)

    def unpriced(self) -> list[ScheduleLine]:
        """Lines with no supplier price."""
        return [line for line in self.lines if line.offer is None]


def price_schedule(
    result: TakeoffResult, prices: PriceList, products: ProductMap
) -> PricedSchedule:
    """Price each material in a takeoff with the best mapped supplier product.

    The best product is the one with the lowest price per material unit,
    preferring products in stock; ties go to the product listed first in the
    map. Materials with no usable product are kept, with the reason.
    """
    if products.meta.currency != result.currency:
        raise ValueError(
            f"product map {products.meta.name!r} prices in "
            f"{products.meta.currency}, but the takeoff is in {result.currency}"
        )
    lines = [
        _price_line(m, products.products_for(m.key), prices, result.currency)
        for m in result.materials
    ]
    notes = list(result.notes) + NOTES
    if not (result.rates_verified and products.meta.verified):
        notes.append(
            "The rate table or product map has not been verified by a "
            "quantity surveyor."
        )
    return PricedSchedule(
        building=result.building,
        rate_table=result.rate_table,
        product_map=products.meta.name,
        price_list=prices.source,
        currency=result.currency,
        rates_verified=result.rates_verified,
        product_map_verified=products.meta.verified,
        lines=lines,
        priced_total=sum(
            (line.offer.amount for line in lines if line.offer), Decimal(0)
        ),
        notes=notes,
    )


def _price_line(
    material: MaterialLine, refs: list[ProductRef], prices: PriceList, currency: str
) -> ScheduleLine:
    line = ScheduleLine(
        key=material.key,
        name=material.name,
        unit=material.unit,
        quantity=material.quantity,
        sources=material.sources,
    )
    if not refs:
        line.unpriced_reason = "no supplier product mapped"
        return line

    found: list[tuple[ProductRef, Product]] = []
    for ref in refs:
        product = prices.get(ref.store, ref.product_id)
        if product is not None and product.currency == currency:
            found.append((ref, product))
    if not found:
        mapped = ", ".join(f"{r.store} #{r.product_id}" for r in refs)
        line.unpriced_reason = (
            f"mapped products not listed in {currency} in {prices.source}: {mapped}"
        )
        return line

    candidates = [c for c in found if c[1].in_stock] or found
    ref, product = min(candidates, key=lambda c: c[1].price / Decimal(str(c[0].pack)))
    # Round before ceil so float noise (2.0000000001 packs) doesn't add a pack.
    packs = math.ceil(round(material.quantity / ref.pack, 6))
    line.offer = Offer(
        store=product.store,
        product_id=product.product_id,
        product=product.name,
        url=product.url,
        in_stock=product.in_stock,
        priced_at=product.scraped_at,
        pack=ref.pack,
        packs=packs,
        pack_price=product.price,
        amount=product.price * packs,
    )
    return line
