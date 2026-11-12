"""Rate tables: specifications and material constants, kept as editable data."""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Material(_Model):
    """A purchasable material and the wastage allowed on it."""

    name: str
    unit: str
    wastage: float = Field(default=0, ge=0, lt=1)


class Spec(_Model):
    """A BOQ item specification and its materials per unit of measure."""

    description: str
    unit: str
    materials: dict[str, float] = {}
    skirting: str | None = None


class Meta(_Model):
    """Rate table identity and whether a quantity surveyor has checked it."""

    name: str
    region: str
    currency: str
    verified: bool = False


class Defaults(_Model):
    """Which spec the takeoff uses for each kind of item."""

    model_config = ConfigDict(extra="allow")

    walling: dict[str, str]
    dpc: dict[str, str]

    def __getitem__(self, key: str) -> str:
        """Return the default spec key for an item kind."""
        value = getattr(self, key, None)
        if not isinstance(value, str):
            raise KeyError(f"rate table has no default for {key!r}")
        return value


class RateTable(_Model):
    """Specs, materials and defaults for one region."""

    meta: Meta
    defaults: Defaults
    materials: dict[str, Material]
    specs: dict[str, Spec]

    @model_validator(mode="after")
    def _references_resolve(self) -> RateTable:
        missing: list[str] = []
        for key, spec in self.specs.items():
            missing += [
                f"{key} -> material {m}"
                for m in spec.materials
                if m not in self.materials
            ]
            if spec.skirting and spec.skirting not in self.specs:
                missing.append(f"{key} -> skirting {spec.skirting}")
        refs = [
            v for v in (self.defaults.model_extra or {}).values() if isinstance(v, str)
        ]
        refs += list(self.defaults.walling.values()) + list(self.defaults.dpc.values())
        missing += [f"defaults -> spec {r}" for r in refs if r not in self.specs]
        if missing:
            raise ValueError("unresolved rate table references: " + "; ".join(missing))
        return self

    def spec(self, key: str) -> Spec:
        """Look up a spec, naming the rate table if it is missing."""
        try:
            return self.specs[key]
        except KeyError:
            raise KeyError(
                f"rate table {self.meta.name!r} has no spec {key!r}"
            ) from None

    def by_thickness(self, table: str, thickness: float) -> str:
        """Return the default walling or DPC spec for a wall thickness in metres."""
        mm = str(round(thickness * 1000))
        choices: dict[str, str] = getattr(self.defaults, table)
        try:
            return choices[mm]
        except KeyError:
            raise KeyError(
                f"rate table has no {table} spec for {mm} mm walls "
                f"(has {', '.join(sorted(choices))})"
            ) from None


def load_rate_table(path: str | Path) -> RateTable:
    """Load and validate a rate table from a TOML file."""
    with open(path, "rb") as f:
        return RateTable.model_validate(tomllib.load(f))


def default_rate_table() -> RateTable:
    """Load the bundled Kenya default rate table."""
    source = (
        resources.files("designsynapse.quantities")
        / "rate_tables"
        / "kenya_default.toml"
    )
    return RateTable.model_validate(tomllib.loads(source.read_text(encoding="utf-8")))
