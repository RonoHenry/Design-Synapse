# Bugfix Requirements Document

## Introduction

Six property-based tests in `test_mep_system_sizing_properties.py` are failing or timing out when run with default Hypothesis settings. These tests validate critical MEP (Mechanical, Electrical, Plumbing) system sizing properties that ensure equipment meets calculated loads with appropriate safety factors per industry standards (ASHRAE, NEC, IPC, NFPA 13).

The tests are designed to verify that:
- HVAC equipment capacity meets heating/cooling loads with safety factors
- Electrical panels handle loads with NEC-required safety factors
- Circuit sizing meets NEC requirements for ampacity and voltage drop
- Plumbing systems meet peak demand with acceptable velocity
- Water supply systems are adequately sized
- Fire protection systems meet NFPA 13 requirements

The failures prevent validation of these critical engineering calculations, which could lead to undersized or oversized equipment in production use.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the test `test_hvac_equipment_meets_loads_with_safety_factor` is executed THEN the system times out or fails due to assertion violations on safety factor ranges or airflow calculations

1.2 WHEN the test `test_electrical_panel_handles_load_with_safety_factor` is executed THEN the system times out or fails due to assertion violations on panel sizing or safety factor constraints

1.3 WHEN the test `test_circuit_sizing_meets_nec_requirements` is executed THEN the system times out or fails due to assertion violations on conductor ampacity, breaker sizing, or voltage drop calculations

1.4 WHEN the test `test_plumbing_system_meets_peak_demand` is executed THEN the system times out or fails due to assertion violations on pipe sizing, velocity constraints, or friction loss calculations

1.5 WHEN the test `test_water_supply_system_adequacy` is executed THEN the system times out or fails due to assertion violations on service sizing, meter sizing, or pressure requirements

1.6 WHEN the test `test_fire_protection_meets_nfpa_requirements` is executed THEN the system times out or fails due to assertion violations on sprinkler density, coverage, hose allowance, or residual pressure requirements

### Expected Behavior (Correct)

2.1 WHEN the test `test_hvac_equipment_meets_loads_with_safety_factor` is executed THEN the system SHALL pass all assertions validating that equipment heating/cooling capacity meets calculated loads with safety factors between 1.0 and 1.5, and airflow is proportional to cooling capacity

2.2 WHEN the test `test_electrical_panel_handles_load_with_safety_factor` is executed THEN the system SHALL pass all assertions validating that panel amperage meets calculated load with NEC 125% safety factor and is not excessively oversized

2.3 WHEN the test `test_circuit_sizing_meets_nec_requirements` is executed THEN the system SHALL pass all assertions validating that conductor ampacity meets design current, breaker size is appropriate, voltage drop is within 5% NEC recommendation, and breaker protects conductor

2.4 WHEN the test `test_plumbing_system_meets_peak_demand` is executed THEN the system SHALL pass all assertions validating that pipe flow rate matches peak demand, velocity is within 2-8 ft/s range, friction loss is reasonable, and peak demand is proportional to fixture units

2.5 WHEN the test `test_water_supply_system_adequacy` is executed THEN the system SHALL pass all assertions validating that peak demand is reasonable for fixture count, service size is adequate for peak demand, and required pressure is within 15-80 psi range

2.6 WHEN the test `test_fire_protection_meets_nfpa_requirements` is executed THEN the system SHALL pass all assertions validating that sprinkler density is within NFPA 13 range (0.10-0.40 GPM/sq ft), coverage per head is within limits (50-250 sq ft), hose allowance is within NFPA 13 range (100-500 GPM), residual pressure meets minimum 7 psi, and number of heads matches area of application

### Unchanged Behavior (Regression Prevention)

3.1 WHEN property-based tests for other MEP calculations are executed THEN the system SHALL CONTINUE TO pass all existing assertions

3.2 WHEN unit tests for HVAC, electrical, plumbing, and fire protection calculators are executed THEN the system SHALL CONTINUE TO pass all existing test cases

3.3 WHEN the calculators are used with valid input data within realistic ranges THEN the system SHALL CONTINUE TO produce correct engineering calculations per industry standards

3.4 WHEN the calculators apply safety factors per code requirements THEN the system SHALL CONTINUE TO apply the correct multipliers (e.g., 1.25x for continuous loads, standard equipment sizing)
