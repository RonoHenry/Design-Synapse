"""Snapshot every listed shop's prices to a dated CSV.

Usage:  python -m price_scraper [--out DIR] [--store NAME ...]
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import sys
from datetime import date
from pathlib import Path

from .stores import STORES
from .woocommerce import Product, fetch_products

FIELDS = [f.name for f in dataclasses.fields(Product)]


def main(argv: list[str] | None = None) -> int:
    """Scrape the selected shops into one dated CSV; exit 1 if any shop failed."""
    parser = argparse.ArgumentParser(prog="price_scraper", description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).parent.parent / "data"
    )
    parser.add_argument("--store", action="append", choices=sorted(STORES))
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / f"prices-{date.today().isoformat()}.csv"
    failures = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for name in args.store or sorted(STORES):
            count = 0
            try:
                for product in fetch_products(name, STORES[name]):
                    writer.writerow(dataclasses.asdict(product))
                    count += 1
            except Exception as exc:  # one shop failing must not stop the rest
                failures += 1
                print(f"{name}: FAILED after {count} products: {exc}", file=sys.stderr)
                continue
            print(f"{name}: {count} products")
    print(f"wrote {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
