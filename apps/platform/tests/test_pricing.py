import csv
import math
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from designsynapse.pricing import (
    PriceList,
    Product,
    ProductMap,
    default_product_map,
    load_price_list,
    price_schedule,
)
from designsynapse.quantities import MaterialLine, TakeoffResult, takeoff
from designsynapse.quantities.rates import Meta

SCRAPED = datetime(2026, 11, 12, 21, 50, tzinfo=timezone.utc)


def result_with(*materials: tuple[str, str, float], currency="KES") -> TakeoffResult:
    """Build a takeoff result holding only the given (key, unit, quantity) materials."""
    return TakeoffResult(
        building="Test building",
        rate_table="Test rates",
        currency=currency,
        rates_verified=False,
        sections=[],
        materials=[
            MaterialLine(
                key=key,
                name=key.title(),
                unit=unit,
                net_quantity=qty,
                wastage=0,
                quantity=qty,
                sources=["A1"],
            )
            for key, unit, qty in materials
        ],
    )


def product(product_id, price, *, store="shop", in_stock=True, currency="KES"):
    return Product(
        store=store,
        product_id=product_id,
        name=f"Product {product_id}",
        price=Decimal(price),
        currency=currency,
        in_stock=in_stock,
        url=f"https://example.test/{product_id}",
        scraped_at=SCRAPED,
    )


def prices(*products: Product) -> PriceList:
    return PriceList(source="prices-test.csv", products=list(products))


def product_map(**materials: list[tuple[int, float]]) -> ProductMap:
    """Map each material to (product_id, pack) pairs at store 'shop'."""
    return ProductMap(
        meta=Meta(name="Test map", region="KE", currency="KES"),
        materials={
            key: [
                {"store": "shop", "product_id": pid, "pack": pack} for pid, pack in refs
            ]
            for key, refs in materials.items()
        },
    )


# ------------------------------------------------------------------ pricing


def test_buys_whole_packs_at_the_pack_price():
    s = price_schedule(
        result_with(("cement", "bag", 63.2)),
        prices(product(1, "850")),
        product_map(cement=[(1, 1)]),
    )
    offer = s.line("cement").offer
    assert offer.packs == 64
    assert offer.pack_price == Decimal("850")
    assert offer.amount == Decimal("54400")
    assert s.priced_total == Decimal("54400")


def test_pack_converts_material_units_to_products():
    # 30 m2 of mesh in 11.52 m2 sheets: 2.6 sheets, so 3 are bought.
    s = price_schedule(
        result_with(("brc_a142", "m2", 30.0)),
        prices(product(1, "33000")),
        product_map(brc_a142=[(1, 11.52)]),
    )
    assert s.line("brc_a142").offer.packs == 3
    assert s.priced_total == Decimal("99000")


def test_float_noise_does_not_buy_an_extra_pack():
    qty = 0.1 + 0.2  # 0.30000000000000004
    s = price_schedule(
        result_with(("dpc", "m", qty)),
        prices(product(1, "100")),
        product_map(dpc=[(1, 0.3)]),
    )
    assert s.line("dpc").offer.packs == 1


def test_lowest_price_per_material_unit_wins_not_lowest_pack_price():
    # 40 kg bag at 700 is 875 per 50 kg bag; the 50 kg bag at 850 is cheaper.
    s = price_schedule(
        result_with(("cement", "bag", 10)),
        prices(product(1, "700"), product(2, "850")),
        product_map(cement=[(1, 0.8), (2, 1)]),
    )
    assert s.line("cement").offer.product_id == 2


def test_in_stock_product_preferred_over_cheaper_out_of_stock():
    s = price_schedule(
        result_with(("cement", "bag", 10)),
        prices(product(1, "700", in_stock=False), product(2, "850")),
        product_map(cement=[(1, 1), (2, 1)]),
    )
    assert s.line("cement").offer.product_id == 2


def test_out_of_stock_product_used_and_flagged_when_none_in_stock():
    s = price_schedule(
        result_with(("cement", "bag", 10)),
        prices(product(1, "900", in_stock=False), product(2, "850", in_stock=False)),
        product_map(cement=[(1, 1), (2, 1)]),
    )
    offer = s.line("cement").offer
    assert offer.product_id == 2
    assert offer.in_stock is False


def test_tie_goes_to_product_listed_first_in_map():
    s = price_schedule(
        result_with(("board", "pc", 5)),
        prices(product(1, "600"), product(2, "600")),
        product_map(board=[(2, 1), (1, 1)]),
    )
    assert s.line("board").offer.product_id == 2


def test_unmapped_material_is_unpriced_and_excluded_from_total():
    s = price_schedule(
        result_with(("cement", "bag", 2), ("sand", "t", 4)),
        prices(product(1, "850")),
        product_map(cement=[(1, 1)]),
    )
    sand = s.line("sand")
    assert sand.offer is None
    assert sand.unpriced_reason == "no supplier product mapped"
    assert [line.key for line in s.unpriced()] == ["sand"]
    assert s.priced_total == Decimal("1700")


def test_mapped_product_missing_from_price_list_is_unpriced_with_reason():
    s = price_schedule(
        result_with(("cement", "bag", 2)),
        prices(product(9, "850")),
        product_map(cement=[(1, 1), (2, 1)]),
    )
    reason = s.line("cement").unpriced_reason
    assert "shop #1, shop #2" in reason
    assert "prices-test.csv" in reason


def test_product_in_another_currency_is_not_used():
    s = price_schedule(
        result_with(("cement", "bag", 2)),
        prices(product(1, "7", currency="USD")),
        product_map(cement=[(1, 1)]),
    )
    assert s.line("cement").offer is None


def test_product_map_currency_must_match_takeoff():
    with pytest.raises(ValueError, match="USD"):
        price_schedule(
            result_with(("cement", "bag", 2), currency="USD"),
            prices(),
            product_map(),
        )


def test_total_is_exact_decimal():
    s = price_schedule(
        result_with(("a", "pc", 3), ("b", "pc", 7)),
        prices(product(1, "0.10"), product(2, "1999.99")),
        product_map(a=[(1, 1)], b=[(2, 1)]),
    )
    assert s.priced_total == Decimal("14000.23")


def test_takeoff_notes_carried_and_unverified_flagged():
    result = result_with(("cement", "bag", 1))
    result.notes = ["Takeoff note."]
    s = price_schedule(result, prices(), product_map())
    assert s.notes[0] == "Takeoff note."
    assert any("whole supplier packs" in n for n in s.notes)
    assert any("not been verified" in n for n in s.notes)


# -------------------------------------------------------------- price list

CONTRACT_COLUMNS = [
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


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_reads_price_scraper_csv(tmp_path):
    path = tmp_path / "prices-2026-11-12.csv"
    write_csv(
        path,
        CONTRACT_COLUMNS,
        [
            {
                "store": "ebuild",
                "product_id": "24938",
                "name": "Bamburi Cement Tembo 50Kg – Westlands, Nairobi",
                "sku": "",
                "price": "850.50",
                "regular_price": "900",
                "sale_price": "850.50",
                "currency": "KES",
                "in_stock": "False",
                "categories": "Cement",
                "url": "https://www.ebuild.ke/product/x/",
                "scraped_at": "2026-11-12T21:49:49+03:00",
            }
        ],
    )
    price_list = load_price_list(path)
    p = price_list.get("ebuild", 24938)
    assert price_list.source == "prices-2026-11-12.csv"
    assert p.price == Decimal("850.50")
    assert p.in_stock is False
    assert p.name.endswith("Westlands, Nairobi")
    assert p.scraped_at.utcoffset().total_seconds() == 3 * 3600
    assert price_list.get("ebuild", 1) is None


def test_price_csv_missing_a_contract_column_is_rejected(tmp_path):
    path = tmp_path / "prices.csv"
    write_csv(path, [c for c in CONTRACT_COLUMNS if c != "in_stock"], [])
    with pytest.raises(ValueError, match="in_stock"):
        load_price_list(path)


# ----------------------------------------------------- bundled product map


def test_default_product_map_covers_only_rate_table_materials(rates):
    m = default_product_map()
    assert m.meta.currency == rates.meta.currency
    assert set(m.materials) <= set(rates.materials)
    assert all(refs for refs in m.materials.values())


def test_reference_house_priced_with_default_product_map(house, rates):
    bill = takeoff(house, rates)
    m = default_product_map()
    listed = [
        product(ref.product_id, "1000", store=ref.store)
        for refs in m.materials.values()
        for ref in refs
    ]
    # Tembo (24938) is the cheaper of the two accepted cements.
    listed = [p for p in listed if p.product_id not in (24938, 24936)] + [
        product(24938, "850", store="ebuild"),
        product(24936, "885", store="ebuild"),
    ]
    s = price_schedule(bill, prices(*listed), m)

    cement = s.line("cement")
    assert cement.offer.product_id == 24938
    assert cement.offer.packs == math.ceil(bill.material("cement").quantity)

    in_bill = {line.key for line in bill.materials}
    assert {line.key for line in s.lines if line.offer} == set(m.materials) & in_bill
    assert s.line("ballast").unpriced_reason == "no supplier product mapped"
    assert s.priced_total == sum(line.offer.amount for line in s.lines if line.offer)
