"""Shops we collect prices from.

Only shops whose robots.txt allows it and that serve their catalogue through
the public WooCommerce Store API are listed. Checked 2026-11-12.

Not listed: randtech.co.ke (behind a captcha that blocks automated access;
we respect that rather than work around it).
"""

STORES: dict[str, str] = {
    # General building materials: cement, BRC mesh, gypsum, tiles, paint.
    "ebuild": "https://www.ebuild.ke",
    # Gypsum, ceilings, DPC, polythene, roofing (uPVC), paint, tiles.
    "gypsumceilingkenya": "https://www.gypsumceilingkenya.co.ke",
    # Sanitary ware, taps, pipes and fittings, door locks (for plumbing and
    # ironmongery bills later; none of the current BOQ materials).
    "cedarclink": "https://cedarclink.com",
}
