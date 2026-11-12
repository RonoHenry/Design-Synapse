"""Derived geometry: outline, wall junctions and which room each opening faces."""

from __future__ import annotations

from dataclasses import dataclass

from . import geometry as geo
from .building import Building, Opening, Room, Wall


class GeometryError(ValueError):
    """The walls do not describe a building the model can handle."""


def external_outline(b: Building) -> list[geo.XY]:
    """Chain the external walls into one closed centreline polygon."""
    walls = list(b.external_walls)
    if len(walls) < 3:
        raise GeometryError("need at least three external walls forming a loop")
    for w in walls:
        if not geo.is_axis_aligned(w.start.xy, w.end.xy):
            raise GeometryError(
                f"external wall {w.id} is not axis-aligned; "
                "only orthogonal plans are supported for now"
            )

    first = walls.pop(0)
    points = [first.start.xy]
    current = first.end.xy
    while walls:
        for i, w in enumerate(walls):
            if geo.same_point(w.start.xy, current):
                nxt = w.end.xy
            elif geo.same_point(w.end.xy, current):
                nxt = w.start.xy
            else:
                continue
            points.append(current)
            current = nxt
            walls.pop(i)
            break
        else:
            raise GeometryError(
                f"external walls do not form a continuous loop near {current}"
            )
    if not geo.same_point(current, points[0]):
        raise GeometryError("external walls do not close")
    return geo.drop_collinear(points)


@dataclass(frozen=True)
class Outline:
    """Areas and girths of the external wall loop (orthogonal plans).

    For an orthogonal polygon offset by d, convex minus reflex corners is
    always 4, which gives the exact closed forms used here.
    """

    centreline: list[geo.XY]
    half_thickness: float

    @property
    def area(self) -> float:
        """Area enclosed by the wall centrelines."""
        return geo.polygon_area(self.centreline)

    @property
    def girth(self) -> float:
        """Centreline girth of the external walls."""
        return geo.polygon_perimeter(self.centreline)

    @property
    def inner_area(self) -> float:
        """Area inside the internal faces of the external walls."""
        d = self.half_thickness
        return self.area - self.girth * d + 4 * d * d

    @property
    def outer_area(self) -> float:
        """Area of the footprint to the outer faces of the external walls."""
        d = self.half_thickness
        return self.area + self.girth * d + 4 * d * d

    @property
    def outer_girth(self) -> float:
        """Girth measured on the outer faces of the external walls."""
        return self.girth + 8 * self.half_thickness

    @property
    def is_rectangle(self) -> bool:
        """Whether the plan is a plain rectangle."""
        return len(self.centreline) == 4

    def outer_extents(self) -> tuple[float, float]:
        """Overall x and y dimensions to the outer wall faces."""
        xs = [p[0] for p in self.centreline]
        ys = [p[1] for p in self.centreline]
        two_d = 2 * self.half_thickness
        return (max(xs) - min(xs) + two_d, max(ys) - min(ys) + two_d)


def outline(b: Building) -> Outline:
    """Build the external wall outline used for areas and girths."""
    return Outline(external_outline(b), b.external_walls[0].thickness / 2)


def end_hosts(b: Building) -> dict[str, list[Wall]]:
    """For each wall, the walls its ends butt into at T-junctions.

    A wall end is butted into a host when it lands on the host's interior,
    or on the shared end of two collinear walls it is not collinear with.
    Plain corners (L-junctions) need no adjustment on the centreline method.
    """
    hosts: dict[str, list[Wall]] = {w.id: [] for w in b.walls}
    for w in b.walls:
        for p in (w.start.xy, w.end.xy):
            host = _host_at(b, w, p)
            if host is not None:
                hosts[w.id].append(host)
    return hosts


def _host_at(b: Building, w: Wall, p: geo.XY) -> Wall | None:
    others = [o for o in b.walls if o is not w]
    for o in others:
        if geo.on_segment_interior(p, o.start.xy, o.end.xy):
            return o
    ending_here = [
        o
        for o in others
        if geo.same_point(o.start.xy, p) or geo.same_point(o.end.xy, p)
    ]
    for i, o1 in enumerate(ending_here):
        for o2 in ending_here[i + 1 :]:
            if geo.parallel(o1.start.xy, o1.end.xy, o2.start.xy, o2.end.xy) and not (
                geo.parallel(w.start.xy, w.end.xy, o1.start.xy, o1.end.xy)
            ):
                return o1
    return None


def rooms_beside(b: Building, opening: Opening) -> list[Room]:
    """Rooms on either face of an opening (none for a face open to outside)."""
    w = b.wall(opening.wall_id)
    dx, dy = w.direction
    along = opening.offset + opening.width / 2
    cx, cy = w.start.x + dx * along, w.start.y + dy * along
    probe = w.thickness / 2 + 0.05
    found: list[Room] = []
    for sign in (1, -1):
        p = (cx - dy * probe * sign, cy + dx * probe * sign)
        for r in b.rooms:
            if geo.point_in_polygon(p, r.xy) and r not in found:
                found.append(r)
                break
    return found
