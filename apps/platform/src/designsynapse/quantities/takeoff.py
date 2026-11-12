"""Deterministic quantity takeoff from the building model.

Measurement follows the centreline (girth) method used by Kenyan quantity
surveyors: walls, trenches and beams are measured on their centrelines, which
is exact at L-corners; at T-junctions the abutting wall is shortened by half
the width of whatever it butts into.

Known simplifications are listed in ``NOTES`` and returned with every result.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable

from ..model import Building, OpeningKind, RoofKind, Wall, WallKind
from ..model.analysis import Outline, end_hosts, outline, rooms_beside
from .boq import BOQItem, BOQSection, MaterialLine, TakeoffResult
from .rates import RateTable

NOTES = [
    "Plaster, render and paint areas ignore window and door reveals.",
    "Ring beam is assumed to act as the lintel over all openings.",
    "Formwork is measured to both sides of the ring beam for its full length.",
    "Excavation and backfill quantities are bulk volumes with no bulking allowance.",
]

SECTIONS = [
    ("A", "substructure", "Substructure"),
    ("B", "concrete", "Concrete work"),
    ("C", "walling", "Walling"),
    ("D", "roofing", "Roofing"),
    ("E", "doors", "Doors"),
    ("F", "windows", "Windows"),
    ("G", "wall_finishes", "Wall finishes"),
    ("H", "floor_finishes", "Floor finishes"),
    ("I", "ceilings", "Ceiling finishes"),
    ("J", "painting", "Painting"),
]


class TakeoffError(ValueError):
    """The building is valid but outside what the takeoff can measure yet."""


def bar_kg_per_m(diameter_mm: float) -> float:
    """Return the unit weight of a steel bar in kg/m (d^2 / 162)."""
    return diameter_mm**2 / 162


def _f(x: float) -> str:
    return f"{x:.2f}"


def takeoff(building: Building, rates: RateTable) -> TakeoffResult:
    """Measure the building into a bill of quantities and material schedule."""
    return _Takeoff(building, rates).run()


class _Takeoff:
    def __init__(self, b: Building, rates: RateTable) -> None:
        self.b = b
        self.rates = rates
        self.outline: Outline = outline(b)
        self.hosts = end_hosts(b)
        self.items: dict[str, list[BOQItem]] = defaultdict(list)
        self.notes = list(NOTES)

    # ----------------------------------------------------------- helpers

    def eff_length(self, w: Wall, width_of: Callable[[Wall], float]) -> float:
        """Centreline length less half the host width at each T-junction."""
        return w.length - sum(width_of(h) / 2 for h in self.hosts[w.id])

    def walling_spec(self, w: Wall) -> str:
        return w.walling_spec or self.rates.by_thickness("walling", w.thickness)

    def add(
        self,
        section: str,
        key: str,
        quantity: float,
        trace: list[str],
        spec: str | None = None,
        *,
        description: str | None = None,
        unit: str | None = None,
    ) -> None:
        if quantity <= 0:
            return
        if spec is not None:
            s = self.rates.spec(spec)
            description = description or s.description
            unit = unit or s.unit
        assert description and unit
        self.items[section].append(
            BOQItem(
                key=f"{section}.{key}",
                code="",
                description=description,
                unit=unit,
                quantity=quantity,
                spec=spec,
                trace=trace,
            )
        )

    def group_walls(self, key: Callable[[Wall], str]) -> dict[str, list[Wall]]:
        groups: dict[str, list[Wall]] = defaultdict(list)
        for w in self.b.walls:
            groups[key(w)].append(w)
        return groups

    def _sum_lines(
        self,
        walls: list[Wall],
        width_of: Callable[[Wall], float],
        factor: float,
        label: str,
    ) -> tuple[float, list[str]]:
        total, trace = 0.0, []
        for kind in (WallKind.EXTERNAL, WallKind.INTERNAL):
            ws = [w for w in walls if w.kind is kind]
            if not ws:
                continue
            length = sum(self.eff_length(w, width_of) for w in ws)
            total += length * factor
            trace.append(
                f"{kind.value} walls {_f(length)} m x {label} = {_f(length * factor)}"
            )
        return total, trace

    # ----------------------------------------------------------- measure

    def run(self) -> TakeoffResult:
        self.substructure()
        self.concrete()
        self.walling()
        self.roofing()
        self.openings()
        self.finishes()
        return self.result()

    def substructure(self) -> None:
        b, f, d = self.b, self.b.foundation, self.rates.defaults
        o = self.outline
        trench = lambda w: f.trench_width  # noqa: E731
        thick = lambda w: w.thickness  # noqa: E731

        self.add(
            "substructure",
            "oversite",
            o.outer_area,
            [f"outer footprint {_f(o.outer_area)} m2"],
            d["oversite"],
        )

        exc, exc_trace = self._sum_lines(
            b.walls,
            trench,
            f.trench_width * f.trench_depth,
            f"{f.trench_width} x {f.trench_depth}",
        )
        self.add("substructure", "excavation", exc, exc_trace, d["excavation"])

        footing, footing_trace = self._sum_lines(
            b.walls,
            trench,
            f.trench_width * f.footing_thickness,
            f"{f.trench_width} x {f.footing_thickness}",
        )
        self.add(
            "substructure",
            "footing_concrete",
            footing,
            footing_trace,
            d["footing_concrete"],
        )

        wall_h = f.trench_depth - f.footing_thickness + f.plinth_height
        below_gl = 0.0
        for spec, walls in self.group_walls(self.walling_spec).items():
            area, trace = self._sum_lines(walls, thick, wall_h, f"{_f(wall_h)} high")
            self.add(
                "substructure",
                f"foundation_walling.{spec}",
                area,
                trace,
                spec,
                description=f"{self.rates.spec(spec).description}, in foundations",
            )
            below_gl += sum(
                self.eff_length(w, thick)
                * w.thickness
                * (f.trench_depth - f.footing_thickness)
                for w in walls
            )

        backfill = exc - footing - below_gl
        self.add(
            "substructure",
            "backfill",
            backfill,
            [
                f"excavation {_f(exc)} - footing {_f(footing)} "
                f"- walling below ground {_f(below_gl)} = {_f(backfill)} m3"
            ],
            d["backfill"],
        )

        internal_footprint = sum(
            self.eff_length(w, thick) * w.thickness for w in b.internal_walls
        )
        slab_area = o.inner_area - internal_footprint
        slab_trace = [
            f"inside external walls {_f(o.inner_area)} m2 "
            f"- internal wall footprint {_f(internal_footprint)} m2 "
            f"= {_f(slab_area)} m2"
        ]
        for key in ("hardcore", "blinding", "anti_termite", "dpm", "mesh"):
            self.add("substructure", key, slab_area, slab_trace, d[key])
        self.add(
            "substructure",
            "slab_concrete",
            slab_area * b.slab.thickness,
            [
                *slab_trace,
                f"x {b.slab.thickness} thick = {_f(slab_area * b.slab.thickness)} m3",
            ],
            d["slab_concrete"],
            description=f"{self.rates.spec(d['slab_concrete']).description} "
            f"in {round(b.slab.thickness * 1000)} mm ground floor slab",
        )

        for spec, walls in self.group_walls(
            lambda w: self.rates.by_thickness("dpc", w.thickness)
        ).items():
            length, trace = self._sum_lines(walls, thick, 1.0, "1")
            self.add("substructure", f"dpc.{spec}", length, trace, spec)

    def concrete(self) -> None:
        b, rb, d = self.b, self.b.ring_beam, self.rates.defaults
        thick = lambda w: w.thickness  # noqa: E731

        volume, vol_trace = 0.0, []
        main_kg, link_kg, link_trace = 0.0, 0.0, []
        for w in b.walls:
            length = self.eff_length(w, thick)
            volume += length * w.thickness * rb.depth
            main_kg += length * rb.main_bars * bar_kg_per_m(rb.main_bar_diameter)
            link_len = (
                2 * ((w.thickness - 2 * rb.cover) + (rb.depth - 2 * rb.cover)) + 0.1
            )
            link_kg += (
                length / rb.link_spacing * link_len * bar_kg_per_m(rb.link_diameter)
            )
            vol_trace.append(f"{w.id}: {_f(length)} x {w.thickness} x {rb.depth}")
            link_trace.append(
                f"{w.id}: {_f(length)} m / {rb.link_spacing} x {link_len:.2f} m link"
            )
        total_len = sum(self.eff_length(w, thick) for w in b.walls)

        concrete_spec = self.rates.spec(d["ring_beam_concrete"])
        self.add(
            "concrete",
            "ring_beam",
            volume,
            vol_trace,
            d["ring_beam_concrete"],
            description=f"{concrete_spec.description} in ring beam",
        )
        self.add(
            "concrete",
            "ring_beam_main_bars",
            main_kg,
            [
                f"{_f(total_len)} m x {rb.main_bars} bars x "
                f"{bar_kg_per_m(rb.main_bar_diameter):.3f} kg/m"
            ],
            d["main_bar"],
            description=f"Y{rb.main_bar_diameter} main bars in ring beam",
        )
        self.add(
            "concrete",
            "ring_beam_links",
            link_kg,
            [*link_trace, f"x {bar_kg_per_m(rb.link_diameter):.3f} kg/m"],
            d["link_bar"],
            description=f"R{rb.link_diameter} links at "
            f"{round(rb.link_spacing * 1000)} mm centres in ring beam",
        )
        self.add(
            "concrete",
            "ring_beam_formwork",
            total_len * 2 * rb.depth,
            [f"{_f(total_len)} m x 2 sides x {rb.depth}"],
            d["formwork"],
        )

    def walling(self) -> None:
        h = self.b.wall_height
        thick = lambda w: w.thickness  # noqa: E731
        for spec, walls in self.group_walls(self.walling_spec).items():
            gross, trace = self._sum_lines(walls, thick, h, f"{h} high")
            ids = {w.id for w in walls}
            deduct = sum(o.area for o in self.b.openings if o.wall_id in ids)
            trace.append(f"less openings {_f(deduct)} m2")
            self.add("walling", spec, gross - deduct, trace, spec)

    def roofing(self) -> None:
        roof, d, o = self.b.roof, self.rates.defaults, self.outline
        if roof is None:
            return
        if not o.is_rectangle:
            raise TakeoffError("roof takeoff currently supports rectangular plans only")

        bx, by = o.outer_extents()
        building_len = max(bx, by)
        length = building_len + 2 * roof.overhang
        width = min(bx, by) + 2 * roof.overhang
        cos_p, tan_p = math.cos(roof.pitch_radians), math.tan(roof.pitch_radians)
        plan = length * width
        slope = plan / cos_p
        half = width / 2
        plan_trace = (
            f"plan {_f(length)} x {_f(width)} = {_f(plan)} m2 "
            f"incl. {roof.overhang} m overhang"
        )

        self.add(
            "roofing",
            "covering",
            slope,
            [plan_trace, f"/ cos {roof.pitch} deg = {_f(slope)} m2"],
            d["roof_covering"],
        )
        if roof.kind is RoofKind.GABLE:
            ridge, ridge_trace = length, [f"ridge {_f(length)} m"]
            fascia, fascia_trace = 2 * length, [f"2 eaves x {_f(length)} m"]
            barge = 4 * half / cos_p
            self.add(
                "roofing",
                "barge",
                barge,
                [f"4 x {_f(half)} m / cos {roof.pitch} deg"],
                d["barge"],
            )
        else:
            hip = math.sqrt(2 * half**2 + (half * tan_p) ** 2)
            ridge = (length - width) + 4 * hip
            ridge_trace = [f"ridge {_f(length - width)} m + 4 hips x {_f(hip)} m"]
            fascia = 2 * (length + width)
            fascia_trace = [f"perimeter 2 x ({_f(length)} + {_f(width)})"]
        self.add("roofing", "ridge", ridge, ridge_trace, d["ridge"])
        self.add("roofing", "fascia", fascia, fascia_trace, d["fascia"])

        trusses = math.floor(building_len / roof.truss_spacing + 1e-9) + 1
        self.add(
            "roofing",
            "trusses",
            trusses,
            [f"{_f(building_len)} m / {roof.truss_spacing} m spacing + 1"],
            d["truss"],
        )
        self.add(
            "roofing",
            "purlins",
            slope / roof.purlin_spacing,
            [f"{_f(slope)} m2 / {roof.purlin_spacing} m spacing"],
            d["purlin"],
        )

    def openings(self) -> None:
        by_mark: dict[str, list] = defaultdict(list)
        for op in self.b.openings:
            by_mark[op.mark].append(op)
        for mark in sorted(by_mark):
            ops = by_mark[mark]
            first = ops[0]
            section = "doors" if first.kind is OpeningKind.DOOR else "windows"
            size = f"{round(first.width * 1000)} x {round(first.height * 1000)} mm"
            label = first.description or f"{first.kind.value.capitalize()} {size}"
            self.add(
                section,
                mark,
                len(ops),
                [f"{mark}: {', '.join(o.id for o in ops)}"],
                description=f"{mark}: {label}, complete with frame and ironmongery",
                unit="Nr",
            )

    def finishes(self) -> None:
        b, d, o = self.b, self.rates.defaults, self.outline
        finish_height = b.wall_height + b.ring_beam.depth

        faces: dict[str, list] = defaultdict(list)  # room name -> openings on its walls
        for op in b.openings:
            for room in rooms_beside(b, op):
                faces[room.name].append(op)

        plaster, plaster_trace = 0.0, []
        floor_area = 0.0
        finish_areas: dict[str, float] = defaultdict(float)
        skirting: dict[str, tuple[float, list[str]]] = {}
        ceiling, ceiling_trace = 0.0, []
        for room in b.rooms:
            ops = faces[room.name]
            deduct = sum(op.area for op in ops)
            area = room.perimeter * finish_height - deduct
            plaster += area
            plaster_trace.append(
                f"{room.name}: {_f(room.perimeter)} m x {_f(finish_height)} "
                f"- openings {_f(deduct)} = {_f(area)} m2"
            )
            floor_area += room.area
            if room.floor_finish:
                finish_areas[room.floor_finish] += room.area
                sk = self.rates.spec(room.floor_finish).skirting
                if sk:
                    doors = sum(op.width for op in ops if op.kind is OpeningKind.DOOR)
                    total, trace = skirting.get(sk, (0.0, []))
                    run = room.perimeter - doors
                    skirting[sk] = (
                        total + run,
                        [
                            *trace,
                            f"{room.name}: {_f(room.perimeter)} - doors {_f(doors)}",
                        ],
                    )
            if room.ceiling:
                ceiling += room.area
                ceiling_trace.append(f"{room.name}: {_f(room.area)} m2")

        self.add("wall_finishes", "plaster", plaster, plaster_trace, d["plaster"])
        ext_h = b.foundation.plinth_height + finish_height
        ext_ids = {w.id for w in b.external_walls}
        ext_open = sum(op.area for op in b.openings if op.wall_id in ext_ids)
        render = o.outer_girth * ext_h - ext_open
        render_trace = [
            f"outer girth {_f(o.outer_girth)} m x {_f(ext_h)} "
            f"- openings {_f(ext_open)} = {_f(render)} m2"
        ]
        self.add("wall_finishes", "render", render, render_trace, d["render"])

        self.add(
            "floor_finishes",
            "screed",
            floor_area,
            [f"rooms {_f(floor_area)} m2"],
            d["screed"],
        )
        for spec, area in finish_areas.items():
            self.add("floor_finishes", spec, area, [f"rooms {_f(area)} m2"], spec)
        for spec, (length, trace) in skirting.items():
            self.add("floor_finishes", spec, length, trace, spec)

        self.add("ceilings", "ceiling", ceiling, ceiling_trace, d["ceiling"])

        self.add(
            "painting", "internal_walls", plaster, ["as plaster"], d["paint_internal"]
        )
        self.add(
            "painting", "external_walls", render, ["as render"], d["paint_external"]
        )
        self.add("painting", "ceilings", ceiling, ["as ceiling"], d["paint_ceiling"])

        if not b.rooms:
            self.notes.append("No rooms defined: internal finishes were not measured.")

    # ----------------------------------------------------------- output

    def result(self) -> TakeoffResult:
        sections = []
        for letter, key, title in SECTIONS:
            items = self.items.get(key, [])
            for n, item in enumerate(items, 1):
                item.code = f"{letter}{n}"
            if items:
                sections.append(BOQSection(code=letter, title=title, items=items))
        return TakeoffResult(
            building=self.b.name,
            rate_table=self.rates.meta.name,
            currency=self.rates.meta.currency,
            rates_verified=self.rates.meta.verified,
            sections=sections,
            materials=self.material_schedule(sections),
            notes=self.notes,
        )

    def material_schedule(self, sections: list[BOQSection]) -> list[MaterialLine]:
        net: dict[str, float] = defaultdict(float)
        sources: dict[str, list[str]] = defaultdict(list)
        extra: dict[str, tuple[str, str]] = {}
        for section in sections:
            for item in section.items:
                if item.spec is None:  # doors and windows are bought as units
                    key = f"opening.{item.key.rsplit('.', 1)[1]}"
                    extra[key] = (item.description, "Nr")
                    net[key] += item.quantity
                    sources[key].append(item.code)
                    continue
                for mat, per_unit in self.rates.spec(item.spec).materials.items():
                    net[mat] += item.quantity * per_unit
                    sources[mat].append(item.code)

        lines = []
        for key, qty in net.items():
            if key in extra:
                name, unit = extra[key]
                wastage = 0.0
            else:
                m = self.rates.materials[key]
                name, unit, wastage = m.name, m.unit, m.wastage
            lines.append(
                MaterialLine(
                    key=key,
                    name=name,
                    unit=unit,
                    net_quantity=qty,
                    wastage=wastage,
                    quantity=qty * (1 + wastage),
                    sources=sources[key],
                )
            )
        return lines
