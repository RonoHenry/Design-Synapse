import math

import pytest
from conftest import p, two_room_house
from designsynapse.model import Building
from designsynapse.model.analysis import end_hosts, outline
from designsynapse.quantities import TakeoffError, takeoff
from pydantic import ValidationError


def test_outline_areas(house):
    o = outline(house)
    assert o.area == pytest.approx(80)
    assert o.girth == pytest.approx(36)
    assert o.inner_area == pytest.approx(9.8 * 7.8)
    assert o.outer_area == pytest.approx(10.2 * 8.2)
    assert o.outer_girth == pytest.approx(2 * (10.2 + 8.2))


def test_l_shaped_outline_offsets_exactly():
    # L-shape: 10 x 8 with a 4 x 3 notch out of one corner (one reflex corner)
    pts = [(0, 0), (10, 0), (10, 5), (6, 5), (6, 8), (0, 8)]
    walls = [
        {
            "id": f"e{i}",
            "kind": "external",
            "start": p(*a),
            "end": p(*b),
            "thickness": 0.2,
        }
        for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1]))
    ]
    b = Building.model_validate(
        two_room_house(walls=walls, openings=[], rooms=[], roof=None)
    )
    o = outline(b)
    assert o.area == pytest.approx(80 - 12)
    # inner polygon: (0.1,0.1)-(9.9,0.1)-(9.9,4.9)-(5.9,4.9)-(5.9,7.9)-(0.1,7.9)
    assert o.inner_area == pytest.approx(9.8 * 4.8 + 5.8 * 3.0)


def test_t_junction_found_on_wall_interior(house):
    hosts = end_hosts(house)
    assert [h.id for h in hosts["I"]] == ["S", "N"]
    assert all(hosts[w] == [] for w in "SENW")


def test_split_external_wall_gives_same_quantities(house, rates):
    data = two_room_house()
    walls = [w for w in data["walls"] if w["id"] != "S"]
    walls += [
        {
            "id": "S1",
            "kind": "external",
            "start": p(0, 0),
            "end": p(6, 0),
            "thickness": 0.2,
        },
        {
            "id": "S2",
            "kind": "external",
            "start": p(6, 0),
            "end": p(10, 0),
            "thickness": 0.2,
        },
    ]
    openings = [dict(o) for o in data["openings"]]
    openings[0].update(wall_id="S1")  # D1 at x = 2.0
    openings[1].update(wall_id="S2", offset=1.5)  # W1 at x = 7.5
    split = Building.model_validate(two_room_house(walls=walls, openings=openings))

    a, b = takeoff(house, rates), takeoff(split, rates)
    for item in a.items():
        assert b.item(item.key).quantity == pytest.approx(item.quantity), item.key


def test_hip_roof(rates):
    b = Building.model_validate(
        two_room_house(roof={"kind": "hip", "pitch": 25, "overhang": 0.6})
    )
    r = takeoff(b, rates)
    half = 9.4 / 2
    hip = math.sqrt(2 * half**2 + (half * math.tan(math.radians(25))) ** 2)
    assert r.item("roofing.ridge").quantity == pytest.approx((11.4 - 9.4) + 4 * hip)
    assert r.item("roofing.fascia").quantity == pytest.approx(2 * (11.4 + 9.4))
    with pytest.raises(KeyError):
        r.item("roofing.barge")


def test_non_rectangular_roof_is_refused(rates):
    pts = [(0, 0), (10, 0), (10, 5), (6, 5), (6, 8), (0, 8)]
    walls = [
        {
            "id": f"e{i}",
            "kind": "external",
            "start": p(*a),
            "end": p(*b),
            "thickness": 0.2,
        }
        for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1]))
    ]
    b = Building.model_validate(two_room_house(walls=walls, openings=[], rooms=[]))
    with pytest.raises(TakeoffError, match="rectangular"):
        takeoff(b, rates)


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d["walls"].pop(1), "loop"),
        (lambda d: d["openings"][0].update(offset=9.5), "past the end"),
        (lambda d: d["openings"][0].update(wall_id="X"), "unknown wall"),
        (lambda d: d["openings"][1].update(width=1.5), "differ"),
        (lambda d: d["walls"][0].update(thickness=0.15), "one thickness"),
        (lambda d: d["walls"][4].update(id="S"), "unique"),
    ],
)
def test_invalid_buildings_are_rejected(change, message):
    data = two_room_house()
    change(data)
    with pytest.raises(ValidationError, match=message):
        Building.model_validate(data)


def test_unknown_wall_thickness_names_the_problem(rates):
    data = two_room_house()
    data["walls"][4]["thickness"] = 0.1
    b = Building.model_validate(data)
    with pytest.raises(KeyError, match="100 mm"):
        takeoff(b, rates)
