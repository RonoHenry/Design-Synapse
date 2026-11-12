"""The building model: the single geometric record every downstream stage reads.

Conventions (single storey, masonry, strip foundations):
- Units are metres, square metres and cubic metres. Angles are degrees.
- Walls are drawn on their centrelines. External walls form one closed loop.
- An internal wall that meets another wall in a T is drawn to the host
  wall's centreline; the takeoff deducts the overlap.
- ``wall_height`` runs from top of floor slab to underside of ring beam.
- Room polygons trace the finished internal faces of the walls around them.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import geometry as geo


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Point(_Model):
    """A plan position in metres."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float
    y: float

    @property
    def xy(self) -> geo.XY:
        """The point as an (x, y) tuple."""
        return (self.x, self.y)


class WallKind(StrEnum):
    """Whether a wall is part of the external envelope."""

    EXTERNAL = "external"
    INTERNAL = "internal"


class Wall(_Model):
    """A straight wall drawn on its centreline."""

    id: str
    kind: WallKind
    start: Point
    end: Point
    thickness: float = Field(gt=0, le=0.6)
    walling_spec: str | None = Field(
        default=None,
        description="Rate-table walling spec; defaults by thickness when omitted.",
    )

    @property
    def length(self) -> float:
        """Centreline length."""
        return geo.distance(self.start.xy, self.end.xy)

    @property
    def direction(self) -> geo.XY:
        """Unit vector from start to end."""
        length = self.length
        return (
            (self.end.x - self.start.x) / length,
            (self.end.y - self.start.y) / length,
        )


class OpeningKind(StrEnum):
    """Door or window."""

    DOOR = "door"
    WINDOW = "window"


class Opening(_Model):
    """A door or window set in a wall."""

    id: str
    wall_id: str
    kind: OpeningKind
    mark: str = Field(description="Schedule mark, e.g. D1 or W2.")
    width: float = Field(gt=0, le=6)
    height: float = Field(gt=0, le=4)
    sill: float = Field(default=0, ge=0, description="Floor to bottom of opening.")
    offset: float = Field(
        ge=0, description="Distance along the wall from its start to the near jamb."
    )
    description: str | None = None

    @property
    def area(self) -> float:
        """Opening area deducted from walls and finishes."""
        return self.width * self.height


class Room(_Model):
    """A room traced on the finished internal faces of its walls."""

    name: str
    polygon: list[Point] = Field(min_length=3)
    floor_finish: str | None = Field(
        default=None, description="Rate-table floor finish spec, or none."
    )
    ceiling: bool = True

    @property
    def xy(self) -> list[geo.XY]:
        """Polygon vertices as (x, y) tuples."""
        return [p.xy for p in self.polygon]

    @property
    def area(self) -> float:
        """Floor area."""
        return geo.polygon_area(self.xy)

    @property
    def perimeter(self) -> float:
        """Perimeter on the internal wall faces."""
        return geo.polygon_perimeter(self.xy)


class Foundation(_Model):
    """Strip foundation dimensions, common to all walls."""

    trench_width: float = Field(default=0.6, gt=0)
    trench_depth: float = Field(
        default=1.0, gt=0, description="Ground level to bottom of trench."
    )
    footing_thickness: float = Field(default=0.2, gt=0)
    plinth_height: float = Field(
        default=0.3, ge=0, description="Ground level to top of floor slab (DPC)."
    )

    @model_validator(mode="after")
    def _footing_fits(self) -> Foundation:
        if self.footing_thickness >= self.trench_depth:
            raise ValueError("footing_thickness must be less than trench_depth")
        return self


class Slab(_Model):
    """Ground floor slab."""

    thickness: float = Field(default=0.15, gt=0, le=0.4)


class RingBeam(_Model):
    """Reinforced concrete ring beam on top of all walls."""

    depth: float = Field(default=0.2, gt=0)
    main_bars: int = Field(default=4, ge=2)
    main_bar_diameter: int = Field(default=12, description="mm, high yield (Y).")
    link_diameter: int = Field(default=8, description="mm, mild steel (R).")
    link_spacing: float = Field(default=0.2, gt=0)
    cover: float = Field(default=0.025, gt=0)


class RoofKind(StrEnum):
    """Roof form."""

    GABLE = "gable"
    HIP = "hip"


class Roof(_Model):
    """Pitched roof over the whole plan."""

    kind: RoofKind = RoofKind.GABLE
    pitch: float = Field(default=25, gt=5, lt=60, description="Degrees.")
    overhang: float = Field(default=0.6, ge=0, le=1.5)
    truss_spacing: float = Field(default=0.9, gt=0)
    purlin_spacing: float = Field(default=0.9, gt=0)

    @property
    def pitch_radians(self) -> float:
        """Pitch in radians."""
        return math.radians(self.pitch)


class Building(_Model):
    """A single storey building: the record every stage reads and enriches."""

    name: str
    wall_height: float = Field(default=2.8, gt=1.8, le=6)
    walls: list[Wall]
    openings: list[Opening] = []
    rooms: list[Room] = []
    foundation: Foundation = Foundation()
    slab: Slab = Slab()
    ring_beam: RingBeam = RingBeam()
    roof: Roof | None = Roof()

    def wall(self, wall_id: str) -> Wall:
        """Look up a wall by id."""
        for w in self.walls:
            if w.id == wall_id:
                return w
        raise KeyError(wall_id)

    @property
    def external_walls(self) -> list[Wall]:
        """Walls forming the external envelope."""
        return [w for w in self.walls if w.kind is WallKind.EXTERNAL]

    @property
    def internal_walls(self) -> list[Wall]:
        """Partition walls."""
        return [w for w in self.walls if w.kind is WallKind.INTERNAL]

    @model_validator(mode="after")
    def _check_consistency(self) -> Building:
        from .analysis import external_outline  # avoid import cycle

        ids = [w.id for w in self.walls]
        if len(ids) != len(set(ids)):
            raise ValueError("wall ids must be unique")
        for w in self.walls:
            if w.length <= geo.TOL:
                raise ValueError(f"wall {w.id} has zero length")

        ext = self.external_walls
        if len({round(w.thickness, 4) for w in ext}) > 1:
            raise ValueError("external walls must share one thickness (for now)")
        external_outline(self)  # raises if the external walls don't close

        opening_ids = [o.id for o in self.openings]
        if len(opening_ids) != len(set(opening_ids)):
            raise ValueError("opening ids must be unique")
        sizes: dict[str, tuple[str, float, float]] = {}
        for o in self.openings:
            try:
                w = self.wall(o.wall_id)
            except KeyError:
                raise ValueError(
                    f"opening {o.id} refers to unknown wall {o.wall_id}"
                ) from None
            if o.offset + o.width > w.length + geo.TOL:
                raise ValueError(f"opening {o.id} runs past the end of wall {w.id}")
            if o.sill + o.height > self.wall_height + geo.TOL:
                raise ValueError(f"opening {o.id} is taller than the wall")
            size = (o.kind, round(o.width, 4), round(o.height, 4))
            if sizes.setdefault(o.mark, size) != size:
                raise ValueError(f"openings marked {o.mark} differ in kind or size")
        return self
