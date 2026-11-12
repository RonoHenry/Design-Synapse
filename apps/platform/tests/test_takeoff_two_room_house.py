"""Takeoff of the two-room test house checked against a hand calculation.

Every expected value below is written out as the arithmetic a quantity
surveyor would do on paper, not computed with engine code.

Key dimensions (see conftest.two_room_house):
  external centreline girth  2 x (10 + 8)          = 36.0 m
  internal wall effective    8 - 0.1 - 0.1         = 7.8 m  (T both ends, half of 200)
  internal trench effective  8 - 0.3 - 0.3         = 7.4 m  (half of 600 trench)
  inside external walls      9.8 x 7.8             = 76.44 m2
  outer footprint            10.2 x 8.2            = 83.64 m2
"""

import math

import pytest
from designsynapse.quantities import takeoff

APPROX = dict(rel=1e-6, abs=1e-6)

COS25 = math.cos(math.radians(25))


@pytest.fixture
def boq(house, rates):
    return takeoff(house, rates)


def qty(boq, key):
    return boq.item(key).quantity


def test_substructure(boq):
    assert qty(boq, "substructure.oversite") == pytest.approx(10.2 * 8.2, **APPROX)
    # (36 + 7.4) m x 0.6 x 1.0
    assert qty(boq, "substructure.excavation") == pytest.approx(26.04, **APPROX)
    # (36 + 7.4) m x 0.6 x 0.2
    assert qty(boq, "substructure.footing_concrete") == pytest.approx(5.208, **APPROX)
    # walling height 1.0 - 0.2 + 0.3 = 1.1
    assert qty(boq, "substructure.foundation_walling.mcs_200") == pytest.approx(
        36 * 1.1, **APPROX
    )
    assert qty(boq, "substructure.foundation_walling.mcs_150") == pytest.approx(
        7.8 * 1.1, **APPROX
    )
    # 26.04 - 5.208 - (36 x 0.2 x 0.8) - (7.8 x 0.15 x 0.8)
    assert qty(boq, "substructure.backfill") == pytest.approx(14.136, **APPROX)

    # slab: 76.44 - (7.8 x 0.15) = 75.27 = rooms 5.825 x 7.8 + 3.825 x 7.8
    for key in ("hardcore", "blinding", "anti_termite", "dpm", "mesh"):
        assert qty(boq, f"substructure.{key}") == pytest.approx(75.27, **APPROX)
    assert qty(boq, "substructure.slab_concrete") == pytest.approx(
        75.27 * 0.15, **APPROX
    )
    assert qty(boq, "substructure.dpc.dpc_200") == pytest.approx(36, **APPROX)
    assert qty(boq, "substructure.dpc.dpc_150") == pytest.approx(7.8, **APPROX)


def test_ring_beam(boq):
    # 36 x 0.2 x 0.2 + 7.8 x 0.15 x 0.2
    assert qty(boq, "concrete.ring_beam") == pytest.approx(1.674, **APPROX)
    # 43.8 m x 4 bars x 12^2/162 kg/m
    assert qty(boq, "concrete.ring_beam_main_bars") == pytest.approx(
        43.8 * 4 * 144 / 162, **APPROX
    )
    # links 5 per metre; 0.70 m long in 200 walls, 0.60 m in 150 walls; 8^2/162 kg/m
    assert qty(boq, "concrete.ring_beam_links") == pytest.approx(
        (36 * 5 * 0.7 + 7.8 * 5 * 0.6) * 64 / 162, **APPROX
    )
    assert qty(boq, "concrete.ring_beam_formwork") == pytest.approx(
        43.8 * 2 * 0.2, **APPROX
    )


def test_walling(boq):
    # 36 x 2.8 = 100.8, less D1 0.9 x 2.1 and three W1 1.2 x 1.2
    assert qty(boq, "walling.mcs_200") == pytest.approx(100.8 - 1.89 - 4.32, **APPROX)
    # 7.8 x 2.8 = 21.84, less D2 0.8 x 2.1
    assert qty(boq, "walling.mcs_150") == pytest.approx(21.84 - 1.68, **APPROX)


def test_gable_roof(boq):
    # outer 10.2 x 8.2 + 0.6 overhang each side -> 11.4 x 9.4
    assert qty(boq, "roofing.covering") == pytest.approx(11.4 * 9.4 / COS25, **APPROX)
    assert qty(boq, "roofing.ridge") == pytest.approx(11.4, **APPROX)
    assert qty(boq, "roofing.fascia") == pytest.approx(2 * 11.4, **APPROX)
    assert qty(boq, "roofing.barge") == pytest.approx(4 * 4.7 / COS25, **APPROX)
    # floor(10.2 / 0.9) + 1
    assert qty(boq, "roofing.trusses") == 12
    assert qty(boq, "roofing.purlins") == pytest.approx(
        11.4 * 9.4 / COS25 / 0.9, **APPROX
    )


def test_doors_and_windows(boq):
    assert qty(boq, "doors.D1") == 1
    assert qty(boq, "doors.D2") == 1
    assert qty(boq, "windows.W1") == 3


def test_finishes(boq):
    # Living 2 x (5.825 + 7.8) = 27.25 m; Bedroom 2 x (3.825 + 7.8) = 23.25 m
    # height 2.8 + 0.2 ring beam = 3.0
    # Living faces D1, one W1, D2:   81.75 - (1.89 + 1.44 + 1.68) = 76.74
    # Bedroom faces two W1, D2:      69.75 - (1.44 + 1.44 + 1.68) = 65.19
    assert qty(boq, "wall_finishes.plaster") == pytest.approx(141.93, **APPROX)
    # outer girth 36 + 8 x 0.1 = 36.8; height 0.3 + 3.0 = 3.3; less 6.21 openings
    assert qty(boq, "wall_finishes.render") == pytest.approx(
        36.8 * 3.3 - 6.21, **APPROX
    )

    assert qty(boq, "floor_finishes.screed") == pytest.approx(75.27, **APPROX)
    assert qty(boq, "floor_finishes.ceramic_tiles") == pytest.approx(75.27, **APPROX)
    # 27.25 - 0.9 - 0.8 + 23.25 - 0.8
    assert qty(boq, "floor_finishes.tile_skirting") == pytest.approx(48.0, **APPROX)
    assert qty(boq, "ceilings.ceiling") == pytest.approx(75.27, **APPROX)

    assert qty(boq, "painting.internal_walls") == pytest.approx(141.93, **APPROX)
    assert qty(boq, "painting.external_walls") == pytest.approx(
        36.8 * 3.3 - 6.21, **APPROX
    )
    assert qty(boq, "painting.ceilings") == pytest.approx(75.27, **APPROX)


def test_item_codes_are_sequential_per_section(boq):
    for section in boq.sections:
        codes = [i.code for i in section.items]
        assert codes == [f"{section.code}{n}" for n in range(1, len(codes) + 1)]


def test_material_schedule(boq):
    stone = boq.material("stone_mcs")
    # 200 mm walling: foundations 39.6 + superstructure 94.59 = 134.19 m2 x 12.5 per m2
    assert stone.net_quantity == pytest.approx(134.19 * 12.5, **APPROX)
    assert stone.quantity == pytest.approx(134.19 * 12.5 * 1.05, **APPROX)
    assert boq.material("opening.W1").quantity == 3
    # every spec'd item contributes to at least one material
    assert {code for m in boq.materials for code in m.sources} >= {
        i.code for i in boq.items() if i.spec and i.unit != "Nr"
    } - {i.code for i in boq.items() if i.spec and not boq_spec_materials(i.spec)}


def boq_spec_materials(spec_key):
    from designsynapse.quantities import default_rate_table

    return default_rate_table().spec(spec_key).materials


def test_result_flags_unverified_rates(boq):
    assert boq.rates_verified is False
    assert boq.currency == "KES"
    assert boq.notes
