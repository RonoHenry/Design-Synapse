import pytest
from designsynapse.model import Building
from designsynapse.quantities import default_rate_table


def p(x, y):
    return {"x": x, "y": y}


def two_room_house(**overrides) -> dict:
    """10 x 8 m (centrelines) bungalow split by one internal wall at x = 6.

    External walls 200 mm, internal 150 mm, wall height 2.8 m.
    Openings: front door D1, internal door D2, three windows W1.
    """
    data = {
        "name": "Two-room test house",
        "wall_height": 2.8,
        "walls": [
            {
                "id": "S",
                "kind": "external",
                "start": p(0, 0),
                "end": p(10, 0),
                "thickness": 0.2,
            },
            {
                "id": "E",
                "kind": "external",
                "start": p(10, 0),
                "end": p(10, 8),
                "thickness": 0.2,
            },
            {
                "id": "N",
                "kind": "external",
                "start": p(10, 8),
                "end": p(0, 8),
                "thickness": 0.2,
            },
            {
                "id": "W",
                "kind": "external",
                "start": p(0, 8),
                "end": p(0, 0),
                "thickness": 0.2,
            },
            {
                "id": "I",
                "kind": "internal",
                "start": p(6, 0),
                "end": p(6, 8),
                "thickness": 0.15,
            },
        ],
        "openings": [
            {
                "id": "o1",
                "wall_id": "S",
                "kind": "door",
                "mark": "D1",
                "width": 0.9,
                "height": 2.1,
                "offset": 2.0,
            },
            {
                "id": "o2",
                "wall_id": "S",
                "kind": "window",
                "mark": "W1",
                "width": 1.2,
                "height": 1.2,
                "sill": 0.9,
                "offset": 7.5,
            },
            {
                "id": "o3",
                "wall_id": "N",
                "kind": "window",
                "mark": "W1",
                "width": 1.2,
                "height": 1.2,
                "sill": 0.9,
                "offset": 2.0,
            },
            {
                "id": "o4",
                "wall_id": "W",
                "kind": "window",
                "mark": "W1",
                "width": 1.2,
                "height": 1.2,
                "sill": 0.9,
                "offset": 3.0,
            },
            {
                "id": "o5",
                "wall_id": "I",
                "kind": "door",
                "mark": "D2",
                "width": 0.8,
                "height": 2.1,
                "offset": 3.0,
            },
        ],
        "rooms": [
            {
                "name": "Living",
                "floor_finish": "ceramic_tiles",
                "polygon": [p(0.1, 0.1), p(5.925, 0.1), p(5.925, 7.9), p(0.1, 7.9)],
            },
            {
                "name": "Bedroom",
                "floor_finish": "ceramic_tiles",
                "polygon": [p(6.075, 0.1), p(9.9, 0.1), p(9.9, 7.9), p(6.075, 7.9)],
            },
        ],
        "foundation": {
            "trench_width": 0.6,
            "trench_depth": 1.0,
            "footing_thickness": 0.2,
            "plinth_height": 0.3,
        },
        "slab": {"thickness": 0.15},
        "ring_beam": {
            "depth": 0.2,
            "main_bars": 4,
            "main_bar_diameter": 12,
            "link_diameter": 8,
            "link_spacing": 0.2,
            "cover": 0.025,
        },
        "roof": {
            "kind": "gable",
            "pitch": 25,
            "overhang": 0.6,
            "truss_spacing": 0.9,
            "purlin_spacing": 0.9,
        },
    }
    data.update(overrides)
    return data


@pytest.fixture
def house() -> Building:
    return Building.model_validate(two_room_house())


@pytest.fixture(scope="session")
def rates():
    return default_rate_table()
