# Price Scraper

**Supplier price data collection for DesignSynapse: building-material prices from public supplier catalogues in Kenya.**

The price scraper is the data source for the procurement and pricing stage of the [DesignSynapse platform](../../README.md). It captures dated snapshots of product prices from Kenyan building-material suppliers' public catalogues. The platform's pricing module then matches those products to the material schedule to produce a priced bill of quantities in KES.

## Approach

- **Structured source.** Prices are read from each supplier's WooCommerce Store API (`/wp-json/wc/store/v1/products`), the same public feed the supplier's own storefront uses. No HTML is parsed.
- **Responsible collection.** Requests are made over HTTPS only, one at a time, with a 1.5 s interval between pages. Suppliers are registered only after their robots.txt has been reviewed, and sites that restrict automated access are excluded.
- **Faithful records.** Prices are converted from minor units to KES as exact decimals. Sale prices are recorded only when they are below the regular price, and product names are HTML-decoded. No personal data is collected.
- **Standard library only.** The package has no runtime dependencies.

## Supplier coverage

| Supplier | Catalogue focus | Priced products (Nov 2026) |
|---|---|---:|
| [ebuild.ke](https://www.ebuild.ke) | General building materials: cement, BRC mesh, gypsum board, paint, tiles | 288 |
| [gypsumceilingkenya.co.ke](https://www.gypsumceilingkenya.co.ke) | Ceilings, damp-proofing (DPC and DPM), roofing, paint, tiles | 432 |
| [cedarclink.com](https://cedarclink.com) | Sanitary ware, taps, pipes and fittings, ironmongery | 897 |

randtech.co.ke is excluded because it restricts automated access.

Bulk materials (aggregates, masonry units, reinforcement, iron roofing sheets and timber) are not sold through these catalogues. They require a separate source and are reported as unpriced until one is added.

## Output

Each run writes one CSV file, `data/prices-YYYY-MM-DD.csv`, with one row per priced product. The `data/` directory is excluded from version control.

The column set is a contract with the platform's pricing module and is pinned by [`tests/test_csv_contract.py`](tests/test_csv_contract.py). Any change must be made together with the platform's reader.

| Column | Type | Description |
|---|---|---|
| `store` | text | Supplier key, as registered in [`stores.py`](price_scraper/stores.py) |
| `product_id` | integer | Supplier's product identifier |
| `name` | text | Product name, HTML-decoded |
| `sku` | text | Supplier SKU; may be empty |
| `price` | decimal, KES | Current selling price |
| `regular_price` | decimal, KES | List price |
| `sale_price` | decimal, KES | Sale price, set only when below the list price |
| `currency` | text | ISO 4217 currency code reported by the supplier |
| `in_stock` | boolean | Stock status reported by the supplier |
| `categories` | text | Supplier categories, separated by semicolons |
| `url` | text | Product page |
| `scraped_at` | ISO 8601 timestamp | Collection time, with UTC offset |

## Usage

Requires Python 3.11 or later. Run from this directory:

```bash
python -m price_scraper                      # all registered suppliers
python -m price_scraper --store ebuild       # a single supplier (repeatable)
python -m price_scraper --out path/to/dir    # custom output directory
```

A failure at one supplier is reported and does not stop collection from the others. The command exits with status 1 if any supplier failed.

## Registering a supplier

1. Confirm that the site serves `/wp-json/wc/store/v1/products` as JSON.
2. Review its robots.txt and terms of use. Do not register sites that restrict automated access.
3. Add the supplier to `STORES` in [`stores.py`](price_scraper/stores.py), with a comment describing its catalogue focus.

## Testing

```bash
pip install pytest
python -m pytest
```

The tests run offline against records modelled on live API responses. They cover price conversion, HTML decoding, sale-price handling, pagination, HTTPS enforcement and the CSV contract.

## Roadmap

- Scheduled weekly collection to build a price history
- Bulk-material prices from builders' merchants and quarries
- Additional suppliers, subject to the same access review
