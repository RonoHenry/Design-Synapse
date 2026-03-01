"""Unit tests for UnitConverter class."""
import pytest
from src.utils.unit_converter import (Unit, UnitConversionError, UnitConverter,
                                      UnitSystem)


class TestUnitConverter:
    """Test suite for UnitConverter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = UnitConverter()

    # Test basic length conversions
    def test_feet_to_meters(self):
        """Test conversion from feet to meters."""
        result = self.converter.convert(10.0, Unit.FEET, Unit.METERS)
        assert abs(result - 3.048) < 0.001

    def test_meters_to_feet(self):
        """Test conversion from meters to feet."""
        result = self.converter.convert(3.048, Unit.METERS, Unit.FEET)
        assert abs(result - 10.0) < 0.001

    def test_inches_to_millimeters(self):
        """Test conversion from inches to millimeters."""
        result = self.converter.convert(1.0, Unit.INCHES, Unit.MILLIMETERS)
        assert abs(result - 25.4) < 0.001

    def test_millimeters_to_inches(self):
        """Test conversion from millimeters to inches."""
        result = self.converter.convert(25.4, Unit.MILLIMETERS, Unit.INCHES)
        assert abs(result - 1.0) < 0.001

    # Test force conversions
    def test_pounds_to_newtons(self):
        """Test conversion from pounds to newtons."""
        result = self.converter.convert(100.0, Unit.POUNDS, Unit.NEWTONS)
        assert abs(result - 444.822) < 0.01

    def test_newtons_to_pounds(self):
        """Test conversion from newtons to pounds."""
        result = self.converter.convert(444.822, Unit.NEWTONS, Unit.POUNDS)
        assert abs(result - 100.0) < 0.01

    def test_kips_to_kilonewtons(self):
        """Test conversion from kips to kilonewtons."""
        result = self.converter.convert(1.0, Unit.KIPS, Unit.KILONEWTONS)
        assert abs(result - 4.448) < 0.01

    # Test pressure conversions
    def test_psf_to_pascals(self):
        """Test conversion from pounds per square foot to pascals."""
        result = self.converter.convert(100.0, Unit.PSF, Unit.PASCALS)
        assert abs(result - 4788.026) < 0.1

    def test_psi_to_kilopascals(self):
        """Test conversion from psi to kilopascals."""
        result = self.converter.convert(100.0, Unit.PSI, Unit.KILOPASCALS)
        assert abs(result - 689.476) < 0.1

    # Test same unit conversion
    def test_same_unit_conversion(self):
        """Test that converting to the same unit returns the same value."""
        result = self.converter.convert(100.0, Unit.FEET, Unit.FEET)
        assert result == 100.0

    # Test zero value
    def test_zero_value_conversion(self):
        """Test conversion of zero value."""
        result = self.converter.convert(0.0, Unit.FEET, Unit.METERS)
        assert result == 0.0

    # Test negative values
    def test_negative_value_conversion(self):
        """Test conversion of negative values."""
        result = self.converter.convert(-10.0, Unit.FEET, Unit.METERS)
        assert abs(result - (-3.048)) < 0.001

    # Test invalid unit combination
    def test_invalid_unit_combination(self):
        """Test that converting incompatible units raises an error."""
        with pytest.raises(UnitConversionError):
            self.converter.convert(100.0, Unit.FEET, Unit.POUNDS)

    # Test to_imperial method
    def test_to_imperial_length(self):
        """Test conversion from metric to imperial for length."""
        value, unit = self.converter.to_imperial(10.0, Unit.METERS)
        assert abs(value - 32.808) < 0.01
        assert unit == Unit.FEET

    def test_to_imperial_force(self):
        """Test conversion from metric to imperial for force."""
        value, unit = self.converter.to_imperial(1000.0, Unit.NEWTONS)
        assert abs(value - 224.809) < 0.01
        assert unit == Unit.POUNDS

    # Test to_metric method
    def test_to_metric_length(self):
        """Test conversion from imperial to metric for length."""
        value, unit = self.converter.to_metric(100.0, Unit.FEET)
        assert abs(value - 30.48) < 0.01
        assert unit == Unit.METERS

    def test_to_metric_force(self):
        """Test conversion from imperial to metric for force."""
        value, unit = self.converter.to_metric(100.0, Unit.POUNDS)
        assert abs(value - 444.822) < 0.01
        assert unit == Unit.NEWTONS

    # Test format_value method
    def test_format_value_imperial(self):
        """Test formatting value with imperial units."""
        result = self.converter.format_value(10.5, Unit.FEET, UnitSystem.IMPERIAL)
        assert result == "10.50 ft"

    def test_format_value_metric(self):
        """Test formatting value with metric units."""
        result = self.converter.format_value(3.048, Unit.METERS, UnitSystem.METRIC)
        assert result == "3.05 m"

    def test_format_value_with_precision(self):
        """Test formatting value with custom precision."""
        result = self.converter.format_value(
            10.12345, Unit.FEET, UnitSystem.IMPERIAL, precision=3
        )
        assert result == "10.123 ft"

    # Test edge cases
    def test_very_large_value(self):
        """Test conversion of very large values."""
        result = self.converter.convert(1e6, Unit.FEET, Unit.METERS)
        assert abs(result - 304800.0) < 1.0

    def test_very_small_value(self):
        """Test conversion of very small values."""
        result = self.converter.convert(0.001, Unit.FEET, Unit.METERS)
        assert abs(result - 0.0003048) < 0.0000001
