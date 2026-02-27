#!/usr/bin/env python3
"""Debug the search providers issue."""

import os
import sys

sys.path.append("src")

from src.models.service_provider import ServiceProvider

# Create test providers manually
providers = [
    {
        "business_name": "ABC Plumbing Services",
        "individual_name": "Provider One",
        "description": "General services",
    },
    {
        "business_name": "General Services",
        "individual_name": "John Plumber",
        "description": "General contractor",
    },
    {
        "business_name": "Heating Services",
        "individual_name": "Provider Three",
        "description": "Expert in plumbing and heating systems",
    },
]

search_term = "plumbing"
search_pattern = f"%{search_term}%"

print(f"Searching for: '{search_term}' (pattern: '{search_pattern}')")
print()

matches = 0
for i, p in enumerate(providers, 1):
    business_match = (
        search_pattern.lower().replace("%", "") in p["business_name"].lower()
    )
    individual_match = (
        search_pattern.lower().replace("%", "") in p["individual_name"].lower()
    )
    description_match = (
        search_pattern.lower().replace("%", "") in p["description"].lower()
    )

    any_match = business_match or individual_match or description_match

    print(f"Provider {i}:")
    print(f"  Business: '{p['business_name']}' -> {business_match}")
    print(f"  Individual: '{p['individual_name']}' -> {individual_match}")
    print(f"  Description: '{p['description']}' -> {description_match}")
    print(f"  Overall Match: {any_match}")
    print()

    if any_match:
        matches += 1

print(f"Total matches: {matches}")
