"""Plane geometry helpers. All coordinates are metres; points are (x, y) tuples."""

from __future__ import annotations

import math
from collections.abc import Sequence

XY = tuple[float, float]

# Coordinates closer than this are the same point (0.1 mm).
TOL = 1e-4


def distance(a: XY, b: XY) -> float:
    """Straight-line distance between two points."""
    return math.hypot(b[0] - a[0], b[1] - a[1])


def same_point(a: XY, b: XY, tol: float = TOL) -> bool:
    """Whether two points coincide within tolerance."""
    return distance(a, b) <= tol


def on_segment_interior(p: XY, a: XY, b: XY, tol: float = TOL) -> bool:
    """Check whether p lies on segment ab, excluding its endpoints."""
    length = distance(a, b)
    if length <= tol:
        return False
    cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    if abs(cross) / length > tol:
        return False
    t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / length**2
    margin = tol / length
    return margin < t < 1 - margin


def parallel(a1: XY, a2: XY, b1: XY, b2: XY, tol: float = 1e-6) -> bool:
    """Whether segments a1-a2 and b1-b2 run in the same or opposite direction."""
    ux, uy = a2[0] - a1[0], a2[1] - a1[1]
    vx, vy = b2[0] - b1[0], b2[1] - b1[1]
    norm = math.hypot(ux, uy) * math.hypot(vx, vy)
    return norm > 0 and abs(ux * vy - uy * vx) / norm <= tol


def is_axis_aligned(a: XY, b: XY, tol: float = TOL) -> bool:
    """Whether segment ab is horizontal or vertical."""
    return abs(a[0] - b[0]) <= tol or abs(a[1] - b[1]) <= tol


def polygon_area(points: Sequence[XY]) -> float:
    """Unsigned shoelace area."""
    n = len(points)
    s = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def polygon_perimeter(points: Sequence[XY]) -> float:
    """Return the closed perimeter of a polygon."""
    n = len(points)
    return sum(distance(points[i], points[(i + 1) % n]) for i in range(n))


def point_in_polygon(p: XY, points: Sequence[XY]) -> bool:
    """Ray casting; points exactly on the boundary may go either way."""
    x, y = p
    inside = False
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_cross = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_cross:
                inside = not inside
    return inside


def drop_collinear(points: Sequence[XY]) -> list[XY]:
    """Remove vertices where the outline runs straight on (e.g. a wall split in two)."""
    out = list(points)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            prev, cur, nxt = out[i - 1], out[i], out[(i + 1) % len(out)]
            if parallel(prev, cur, cur, nxt):
                del out[i]
                changed = True
                break
    return out
