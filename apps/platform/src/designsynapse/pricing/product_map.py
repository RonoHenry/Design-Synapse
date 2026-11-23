"""Product maps: the supplier products accepted for each material, kept as data."""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..quantities.rates import Meta


class ProductRef(BaseModel):
    """A supplier product accepted for a material."""

    model_config = ConfigDict(extra="forbid")

    store: str
    product_id: int
    pack: float = Field(
        gt=0,
        description="Quantity of the material, in its rate-table unit, "
        "that one product supplies.",
    )


class ProductMap(BaseModel):
    """Supplier products accepted for each material key of a rate table."""

    model_config = ConfigDict(extra="forbid")

    meta: Meta
    materials: dict[str, list[ProductRef]] = {}

    def products_for(self, material: str) -> list[ProductRef]:
        """Return the products accepted for a material, in map order."""
        return self.materials.get(material, [])


def load_product_map(path: str | Path) -> ProductMap:
    """Load and validate a product map from a TOML file."""
    with open(path, "rb") as f:
        return ProductMap.model_validate(tomllib.load(f))


def default_product_map() -> ProductMap:
    """Load the bundled Kenya default product map."""
    source = (
        resources.files("designsynapse.pricing") / "product_maps" / "kenya_default.toml"
    )
    return ProductMap.model_validate(tomllib.loads(source.read_text(encoding="utf-8")))
