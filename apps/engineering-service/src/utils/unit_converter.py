"""Unit conversion utilities for engineering calculations."""
from enum import Enum
from typing import Tuple


class UnitConversionError(Exception):
    """Exception raised for invalid unit conversions."""

    pass


class UnitSystem(str, Enum):
    """Unit system enumeration."""

    IMPERIAL = "imperial"
    METRIC = "metric"


class Unit(str, Enum):
    """Unit enumeration for engineering calculations."""

    # Length units
    FEET = "ft"
    INCHES = "in"
    METERS = "m"
    MILLIMETERS = "mm"
    CENTIMETERS = "cm"

    # Force units
    POUNDS = "lb"
    KIPS = "kip"
    NEWTONS = "N"
    KILONEWTONS = "kN"

    # Pressure units
    PSF = "psf"  # pounds per square foot
    PSI = "psi"  # pounds per square inch
    PASCALS = "Pa"
    KILOPASCALS = "kPa"

    # Area units
    SQUARE_FEET = "sf"
    SQUARE_METERS = "m2"

    # Volume units
    CUBIC_FEET = "cf"
    CUBIC_METERS = "m3"


class UnitCategory(str, Enum):
    """Unit category enumeration."""

    LENGTH = "length"
    FORCE = "force"
    PRESSURE = "pressure"
    AREA = "area"
    VOLUME = "volume"


class UnitConverter:
    """Handles unit conversions between Imperial and Metric systems."""

    # Conversion factors to base units (meters, newtons, pascals)
    _CONVERSION_FACTORS = {
        # Length conversions (to meters)
        Unit.FEET: 0.3048,
        Unit.INCHES: 0.0254,
        Unit.METERS: 1.0,
        Unit.MILLIMETERS: 0.001,
        Unit.CENTIMETERS: 0.01,
        # Force conversions (to newtons)
        Unit.POUNDS: 4.44822,
        Unit.KIPS: 4448.22,
        Unit.NEWTONS: 1.0,
        Unit.KILONEWTONS: 1000.0,
        # Pressure conversions (to pascals)
        Unit.PSF: 47.8803,
        Unit.PSI: 6894.76,
        Unit.PASCALS: 1.0,
        Unit.KILOPASCALS: 1000.0,
        # Area conversions (to square meters)
        Unit.SQUARE_FEET: 0.092903,
        Unit.SQUARE_METERS: 1.0,
        # Volume conversions (to cubic meters)
        Unit.CUBIC_FEET: 0.0283168,
        Unit.CUBIC_METERS: 1.0,
    }

    # Unit categories
    _UNIT_CATEGORIES = {
        Unit.FEET: UnitCategory.LENGTH,
        Unit.INCHES: UnitCategory.LENGTH,
        Unit.METERS: UnitCategory.LENGTH,
        Unit.MILLIMETERS: UnitCategory.LENGTH,
        Unit.CENTIMETERS: UnitCategory.LENGTH,
        Unit.POUNDS: UnitCategory.FORCE,
        Unit.KIPS: UnitCategory.FORCE,
        Unit.NEWTONS: UnitCategory.FORCE,
        Unit.KILONEWTONS: UnitCategory.FORCE,
        Unit.PSF: UnitCategory.PRESSURE,
        Unit.PSI: UnitCategory.PRESSURE,
        Unit.PASCALS: UnitCategory.PRESSURE,
        Unit.KILOPASCALS: UnitCategory.PRESSURE,
        Unit.SQUARE_FEET: UnitCategory.AREA,
        Unit.SQUARE_METERS: UnitCategory.AREA,
        Unit.CUBIC_FEET: UnitCategory.VOLUME,
        Unit.CUBIC_METERS: UnitCategory.VOLUME,
    }

    # Default imperial units for each category
    _DEFAULT_IMPERIAL_UNITS = {
        UnitCategory.LENGTH: Unit.FEET,
        UnitCategory.FORCE: Unit.POUNDS,
        UnitCategory.PRESSURE: Unit.PSF,
        UnitCategory.AREA: Unit.SQUARE_FEET,
        UnitCategory.VOLUME: Unit.CUBIC_FEET,
    }

    # Default metric units for each category
    _DEFAULT_METRIC_UNITS = {
        UnitCategory.LENGTH: Unit.METERS,
        UnitCategory.FORCE: Unit.NEWTONS,
        UnitCategory.PRESSURE: Unit.PASCALS,
        UnitCategory.AREA: Unit.SQUARE_METERS,
        UnitCategory.VOLUME: Unit.CUBIC_METERS,
    }

    # Unit display names
    _UNIT_DISPLAY_NAMES = {
        Unit.FEET: "ft",
        Unit.INCHES: "in",
        Unit.METERS: "m",
        Unit.MILLIMETERS: "mm",
        Unit.CENTIMETERS: "cm",
        Unit.POUNDS: "lb",
        Unit.KIPS: "kip",
        Unit.NEWTONS: "N",
        Unit.KILONEWTONS: "kN",
        Unit.PSF: "psf",
        Unit.PSI: "psi",
        Unit.PASCALS: "Pa",
        Unit.KILOPASCALS: "kPa",
        Unit.SQUARE_FEET: "sf",
        Unit.SQUARE_METERS: "m²",
        Unit.CUBIC_FEET: "cf",
        Unit.CUBIC_METERS: "m³",
    }

    def convert(self, value: float, from_unit: Unit, to_unit: Unit) -> float:
        """
        Convert a value from one unit to another.

        Args:
            value: The value to convert
            from_unit: The source unit
            to_unit: The target unit

        Returns:
            The converted value

        Raises:
            UnitConversionError: If units are incompatible
        """
        # Same unit, no conversion needed
        if from_unit == to_unit:
            return value

        # Check if units are in the same category
        from_category = self._UNIT_CATEGORIES.get(from_unit)
        to_category = self._UNIT_CATEGORIES.get(to_unit)

        if from_category != to_category:
            raise UnitConversionError(
                f"Cannot convert from {from_unit.value} to {to_unit.value}: "
                f"incompatible unit categories ({from_category} vs {to_category})"
            )

        # Convert to base unit, then to target unit
        from_factor = self._CONVERSION_FACTORS[from_unit]
        to_factor = self._CONVERSION_FACTORS[to_unit]

        base_value = value * from_factor
        result = base_value / to_factor

        return result

    def to_imperial(self, value: float, metric_unit: Unit) -> Tuple[float, Unit]:
        """
        Convert a metric value to imperial units.

        Args:
            value: The value to convert
            metric_unit: The metric unit

        Returns:
            Tuple of (converted_value, imperial_unit)
        """
        category = self._UNIT_CATEGORIES.get(metric_unit)
        imperial_unit = self._DEFAULT_IMPERIAL_UNITS[category]
        converted_value = self.convert(value, metric_unit, imperial_unit)
        return converted_value, imperial_unit

    def to_metric(self, value: float, imperial_unit: Unit) -> Tuple[float, Unit]:
        """
        Convert an imperial value to metric units.

        Args:
            value: The value to convert
            imperial_unit: The imperial unit

        Returns:
            Tuple of (converted_value, metric_unit)
        """
        category = self._UNIT_CATEGORIES.get(imperial_unit)
        metric_unit = self._DEFAULT_METRIC_UNITS[category]
        converted_value = self.convert(value, imperial_unit, metric_unit)
        return converted_value, metric_unit

    def format_value(
        self, value: float, unit: Unit, system: UnitSystem, precision: int = 2
    ) -> str:
        """
        Format a value with its unit for display.

        Args:
            value: The value to format
            unit: The unit
            system: The unit system (for consistency checking)
            precision: Number of decimal places

        Returns:
            Formatted string with value and unit
        """
        unit_display = self._UNIT_DISPLAY_NAMES.get(unit, unit.value)
        formatted_value = f"{value:.{precision}f}"
        return f"{formatted_value} {unit_display}"
