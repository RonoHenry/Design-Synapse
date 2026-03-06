"""Property-based tests for unit conversion system.

**Validates: Requirements 7.6**

This module tests the property that converting from one unit system to another
and back preserves the original value within acceptable floating-point tolerance.
"""
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from src.utils.unit_converter import Unit, UnitCategory, UnitConverter


class TestUnitConversionProperties:
    """Property-based tests for unit conversion round-trip."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = UnitConverter()
        self.tolerance = 1e-9  # Floating point tolerance

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_length_conversion_round_trip_feet_meters(self, value):
        """
        Property: Converting feet to meters and back to feet preserves the value.

        This tests that the conversion is reversible within floating-point tolerance.
        """
        # Convert feet to meters
        meters = self.converter.convert(value, Unit.FEET, Unit.METERS)

        # Convert back to feet
        feet_back = self.converter.convert(meters, Unit.METERS, Unit.FEET)

        # Assert round-trip preserves value
        assert (
            abs(feet_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} ft -> {meters} m -> {feet_back} ft"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_length_conversion_round_trip_inches_millimeters(self, value):
        """
        Property: Converting inches to millimeters and back preserves the value.
        """
        # Convert inches to millimeters
        mm = self.converter.convert(value, Unit.INCHES, Unit.MILLIMETERS)

        # Convert back to inches
        inches_back = self.converter.convert(mm, Unit.MILLIMETERS, Unit.INCHES)

        # Assert round-trip preserves value
        assert (
            abs(inches_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} in -> {mm} mm -> {inches_back} in"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_force_conversion_round_trip_pounds_newtons(self, value):
        """
        Property: Converting pounds to newtons and back preserves the value.
        """
        # Convert pounds to newtons
        newtons = self.converter.convert(value, Unit.POUNDS, Unit.NEWTONS)

        # Convert back to pounds
        pounds_back = self.converter.convert(newtons, Unit.NEWTONS, Unit.POUNDS)

        # Assert round-trip preserves value
        assert (
            abs(pounds_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} lb -> {newtons} N -> {pounds_back} lb"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_force_conversion_round_trip_kips_kilonewtons(self, value):
        """
        Property: Converting kips to kilonewtons and back preserves the value.
        """
        # Convert kips to kilonewtons
        kn = self.converter.convert(value, Unit.KIPS, Unit.KILONEWTONS)

        # Convert back to kips
        kips_back = self.converter.convert(kn, Unit.KILONEWTONS, Unit.KIPS)

        # Assert round-trip preserves value
        assert (
            abs(kips_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} kip -> {kn} kN -> {kips_back} kip"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_pressure_conversion_round_trip_psf_pascals(self, value):
        """
        Property: Converting PSF to pascals and back preserves the value.
        """
        # Convert PSF to pascals
        pascals = self.converter.convert(value, Unit.PSF, Unit.PASCALS)

        # Convert back to PSF
        psf_back = self.converter.convert(pascals, Unit.PASCALS, Unit.PSF)

        # Assert round-trip preserves value
        assert (
            abs(psf_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} psf -> {pascals} Pa -> {psf_back} psf"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_pressure_conversion_round_trip_psi_kilopascals(self, value):
        """
        Property: Converting PSI to kilopascals and back preserves the value.
        """
        # Convert PSI to kilopascals
        kpa = self.converter.convert(value, Unit.PSI, Unit.KILOPASCALS)

        # Convert back to PSI
        psi_back = self.converter.convert(kpa, Unit.KILOPASCALS, Unit.PSI)

        # Assert round-trip preserves value
        assert (
            abs(psi_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} psi -> {kpa} kPa -> {psi_back} psi"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_area_conversion_round_trip_square_feet_square_meters(self, value):
        """
        Property: Converting square feet to square meters and back preserves the value.
        """
        # Convert square feet to square meters
        m2 = self.converter.convert(value, Unit.SQUARE_FEET, Unit.SQUARE_METERS)

        # Convert back to square feet
        sf_back = self.converter.convert(m2, Unit.SQUARE_METERS, Unit.SQUARE_FEET)

        # Assert round-trip preserves value
        assert (
            abs(sf_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} sf -> {m2} m² -> {sf_back} sf"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_volume_conversion_round_trip_cubic_feet_cubic_meters(self, value):
        """
        Property: Converting cubic feet to cubic meters and back preserves the value.
        """
        # Convert cubic feet to cubic meters
        m3 = self.converter.convert(value, Unit.CUBIC_FEET, Unit.CUBIC_METERS)

        # Convert back to cubic feet
        cf_back = self.converter.convert(m3, Unit.CUBIC_METERS, Unit.CUBIC_FEET)

        # Assert round-trip preserves value
        assert (
            abs(cf_back - value) < self.tolerance
        ), f"Round-trip conversion failed: {value} cf -> {m3} m³ -> {cf_back} cf"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_same_unit_conversion_is_identity(self, value):
        """
        Property: Converting a value to the same unit returns the original value.
        """
        # Test with various units
        units_to_test = [
            Unit.FEET,
            Unit.METERS,
            Unit.POUNDS,
            Unit.NEWTONS,
            Unit.PSF,
            Unit.PASCALS,
        ]

        for unit in units_to_test:
            result = self.converter.convert(value, unit, unit)
            assert (
                result == value
            ), f"Same-unit conversion failed for {unit}: {value} != {result}"

    @given(
        value=st.floats(
            min_value=0.1, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_conversion_preserves_positive_values(self, value):
        """
        Property: Converting positive values always results in positive values.
        """
        # Test various conversions
        conversions = [
            (Unit.FEET, Unit.METERS),
            (Unit.POUNDS, Unit.NEWTONS),
            (Unit.PSF, Unit.PASCALS),
            (Unit.SQUARE_FEET, Unit.SQUARE_METERS),
        ]

        for from_unit, to_unit in conversions:
            result = self.converter.convert(value, from_unit, to_unit)
            assert (
                result > 0
            ), f"Positive value became non-positive: {value} {from_unit} -> {result} {to_unit}"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=-0.1, allow_nan=False, allow_infinity=False
        )
    )
    def test_conversion_preserves_negative_values(self, value):
        """
        Property: Converting negative values always results in negative values.
        """
        # Test various conversions
        conversions = [
            (Unit.FEET, Unit.METERS),
            (Unit.POUNDS, Unit.NEWTONS),
            (Unit.PSF, Unit.PASCALS),
        ]

        for from_unit, to_unit in conversions:
            result = self.converter.convert(value, from_unit, to_unit)
            assert (
                result < 0
            ), f"Negative value became non-negative: {value} {from_unit} -> {result} {to_unit}"

    @given(
        value=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        )
    )
    def test_conversion_chain_is_transitive(self, value):
        """
        Property: Converting A->B->C should equal converting A->C directly.

        Tests transitivity: if we can convert feet to meters and meters to centimeters,
        then converting feet to centimeters directly should give the same result.
        """
        # Convert feet -> meters -> centimeters
        meters = self.converter.convert(value, Unit.FEET, Unit.METERS)
        cm_via_meters = self.converter.convert(meters, Unit.METERS, Unit.CENTIMETERS)

        # Convert feet -> centimeters directly
        cm_direct = self.converter.convert(value, Unit.FEET, Unit.CENTIMETERS)

        # Assert both paths give the same result
        assert abs(cm_via_meters - cm_direct) < self.tolerance, (
            f"Transitive conversion failed: {value} ft -> {meters} m -> {cm_via_meters} cm "
            f"vs direct {cm_direct} cm"
        )

    def test_zero_conversion_preserves_zero(self):
        """
        Property: Converting zero always results in zero.
        """
        conversions = [
            (Unit.FEET, Unit.METERS),
            (Unit.POUNDS, Unit.NEWTONS),
            (Unit.PSF, Unit.PASCALS),
            (Unit.SQUARE_FEET, Unit.SQUARE_METERS),
            (Unit.CUBIC_FEET, Unit.CUBIC_METERS),
        ]

        for from_unit, to_unit in conversions:
            result = self.converter.convert(0.0, from_unit, to_unit)
            assert (
                result == 0.0
            ), f"Zero conversion failed: 0 {from_unit} -> {result} {to_unit}"
