# DesignSynapse

Construction cost estimates for houses in Kenya, measured directly from the building design.

In Kenya, a homeowner's estimate usually means a quantity surveyor taking dimensions off the drawings into a bill of quantities (BOQ), then someone phoning hardware suppliers for prices. The drawings, the BOQ and the prices live in separate files, so every design change means re-measuring by hand, and the three drift apart.

DesignSynapse keeps one building model and derives everything else from it. Quantities are measured from the geometry, and material lists come from the quantities. Supplier prices, coming next, will come from the material list. Change a wall and the bill changes with it.

## Status

Early development. I'm building one connected chain first and leaving everything else aside until it works end to end.

| Stage | Status |
|---|---|
| Building model (walls, openings, rooms, foundation, slab, ring beam, roof) | Done |
| Quantity takeoff: bill of quantities and material schedule | Done; rates awaiting review by a quantity surveyor |
| Vendor pricing: match materials to local suppliers' products, price in KES | Next |
| Drawings and schedules: floor plan, door/window schedules, BOQ as PDF | Planned |
| Layout from a written brief, web app, deployment | Planned |

## Example

The test suite takes off a 10 × 8 m single-storey house with two rooms, 200 mm external stone walls, a 150 mm partition, two doors, three windows and a 25° gable roof. It produces 38 BOQ items in ten sections and a 32-line material schedule.

Each item records how it was measured, so a quantity surveyor can check it line by line:

| Item | Description | Unit | Qty | Measured as |
|---|---|---|---:|---|
| A2 | Excavate foundation trench not exceeding 1.5 m deep | m³ | 26.04 | external walls 36.00 m × 0.6 × 1.0 = 21.60; internal walls 7.40 m × 0.6 × 1.0 = 4.44 |
| A12 | Concrete class 20 (1:2:4) in 150 mm ground floor slab | m³ | 11.29 | inside external walls 76.44 m² − internal wall footprint 1.17 m² = 75.27 m² × 0.15 |
| B2 | Y12 main bars in ring beam | kg | 155.73 | 43.80 m × 4 bars × 0.889 kg/m |
| C1 | 200 mm machine-cut stone walling in cement-sand (1:4) mortar | m² | 94.59 | external walls 36.00 m × 2.8 high = 100.80, less openings 6.21 |
| D1 | Gauge 30 box profile roofing sheets, measured on slope | m² | 118.24 | plan 11.40 × 9.40 = 107.16 m² ÷ cos 25° |
| G1 | 12 mm cement-sand (1:4) plaster to internal walls | m² | 141.93 | Living 27.25 m × 3.00 − openings 5.01; Bedroom 23.25 m × 3.00 − openings 4.56 |

The material schedule turns those items into what you would actually buy, with wastage:

| Material | Unit | Qty |
|---|---|---:|
| Portland cement 32.5N (50 kg) | bag | 200.2 |
| River sand | t | 33.7 |
| Ballast 20 mm | t | 25.6 |
| Machine-cut stone 400 × 200 × 200 mm | pc | 1761.2 |
| Box profile roofing sheet, gauge 30 | m² | 136.0 |
| Y12 high yield bar, 12 m | pc | 15.3 |

Every quantity is checked in [`test_takeoff_two_room_house.py`](apps/platform/tests/test_takeoff_two_room_house.py) against a hand calculation, written out as arithmetic.

## How quantities are measured

- **Centreline (girth) method.** Walls, trenches and beams are measured on their centrelines, which is exact at L-corners. Where a partition meets another wall in a T, it is shortened by half the width of what it meets.
- **Openings** are deducted from walling, plaster and render. Each door or window is assigned to the rooms on either side of it, so room finishes and skirtings deduct only their own openings.
- **Rates are data, not code.** Specifications, material constants (for example, stones per m² or cement bags per m³ of concrete) and wastage live in a TOML rate table: [`kenya_default.toml`](apps/platform/src/designsynapse/quantities/rate_tables/kenya_default.toml). A quantity surveyor can review and adjust it without touching the code.
- **Nothing is guessed.** Quantities come only from geometry and the rate table. If a building is outside what the takeoff supports (currently, roofs over non-rectangular plans), it raises an error instead of estimating.

Current limits: single storey, orthogonal plans, one external wall thickness. Reveals are not measured, and the ring beam is assumed to act as the lintel over openings. The default rate table is marked unverified until a practising quantity surveyor has reviewed it.

## Repository layout

```
apps/
  platform/          Active development: building model, takeoff, and the stages that follow
  design-service/    Earlier FastAPI prototype (AI design generation); parts will be ported into platform
  user-service/      Earlier prototype: users and authentication
  analytics-service/ Earlier prototype
  frontend/          Earlier Next.js prototype
docs/                Original design notes and requirements
```

The other services from the original multi-service design (engineering, architectural, vendor, labor, project, knowledge) are on their own branches and frozen. I'll bring them in one at a time once the core chain works.

## Running the takeoff

Requires Python 3.12 or newer.

```bash
cd apps/platform
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # on macOS/Linux: .venv/bin/pip
.venv/Scripts/python -m pytest
```

To take off your own building, describe it as a `Building` (see [`tests/conftest.py`](apps/platform/tests/conftest.py) for a complete example) and call `takeoff(building, default_rate_table())`.

## Author

Henry Rono · [github.com/RonoHenry](https://github.com/RonoHenry)

## License

[MIT](LICENSE)
