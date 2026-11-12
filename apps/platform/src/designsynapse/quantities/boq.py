"""Bill of quantities and material schedule produced by the takeoff."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BOQItem(BaseModel):
    """One measured item in the bill."""

    key: str = Field(description="Stable identifier, e.g. substructure.excavation.")
    code: str = Field(description="Item code within the bill, e.g. A3.")
    description: str
    unit: str
    quantity: float
    spec: str | None = None
    trace: list[str] = Field(default=[], description="How the quantity was measured.")


class BOQSection(BaseModel):
    """An element of the bill, e.g. Substructure."""

    code: str
    title: str
    items: list[BOQItem] = []


class MaterialLine(BaseModel):
    """Total quantity of one material to buy, gathered from BOQ items."""

    key: str
    name: str
    unit: str
    net_quantity: float
    wastage: float
    quantity: float = Field(description="Net quantity plus wastage.")
    sources: list[str] = Field(description="BOQ item codes this material comes from.")


class TakeoffResult(BaseModel):
    """Bill of quantities plus material schedule for one building."""

    building: str
    rate_table: str
    currency: str
    rates_verified: bool
    sections: list[BOQSection]
    materials: list[MaterialLine]
    notes: list[str] = []

    def items(self) -> list[BOQItem]:
        """All items across sections, in bill order."""
        return [i for s in self.sections for i in s.items]

    def item(self, key: str) -> BOQItem:
        """Look up an item by its stable key."""
        for i in self.items():
            if i.key == key:
                return i
        raise KeyError(key)

    def material(self, key: str) -> MaterialLine:
        """Look up a material line by key."""
        for m in self.materials:
            if m.key == key:
                return m
        raise KeyError(key)
