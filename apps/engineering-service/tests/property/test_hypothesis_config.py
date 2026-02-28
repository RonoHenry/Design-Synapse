"""Test Hypothesis configuration and property-based testing setup."""

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.property
class TestHypothesisConfiguration:
    """Test that Hypothesis is properly configured."""

    @given(st.integers())
    def test_hypothesis_works_with_integers(self, value: int):
        """Test that Hypothesis can generate integers."""
        assert isinstance(value, int)

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_hypothesis_works_with_floats(self, value: float):
        """Test that Hypothesis can generate floats."""
        assert isinstance(value, float)
        assert not (value != value)  # Not NaN
        assert abs(value) != float("inf")  # Not infinity

    @given(st.text())
    def test_hypothesis_works_with_text(self, value: str):
        """Test that Hypothesis can generate text."""
        assert isinstance(value, str)

    @given(st.lists(st.integers(), min_size=0, max_size=10))
    def test_hypothesis_works_with_lists(self, values: list):
        """Test that Hypothesis can generate lists."""
        assert isinstance(values, list)
        assert len(values) <= 10
        assert all(isinstance(v, int) for v in values)

    @given(
        st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
    )
    def test_addition_is_commutative(self, a: float, b: float):
        """Property: Addition is commutative (a + b = b + a)."""
        assert abs((a + b) - (b + a)) < 1e-10

    @given(st.floats(min_value=0.1, max_value=1000.0, allow_nan=False))
    def test_positive_values_remain_positive(self, value: float):
        """Property: Positive values remain positive after operations."""
        assert value > 0
        assert value * 2 > 0
        assert value + 1 > 0


@pytest.mark.property
class TestEngineeringCalculationProperties:
    """Test properties relevant to engineering calculations."""

    @given(
        st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=10000.0, allow_nan=False),
    )
    def test_load_combination_is_non_negative(self, dead_load: float, live_load: float):
        """Property: Combined loads are always non-negative."""
        total_load = dead_load + live_load
        assert total_load >= 0

    @given(
        st.floats(min_value=1.0, max_value=100.0, allow_nan=False),
        st.floats(min_value=1.0, max_value=100.0, allow_nan=False),
    )
    def test_area_calculation_is_positive(self, length: float, width: float):
        """Property: Area calculations are always positive."""
        area = length * width
        assert area > 0

    @given(
        st.floats(min_value=0.0, max_value=1000.0, allow_nan=False),
        st.floats(min_value=1.0, max_value=10.0, allow_nan=False),
    )
    def test_safety_factor_increases_capacity(
        self, base_capacity: float, safety_factor: float
    ):
        """Property: Applying safety factor increases required capacity."""
        required_capacity = base_capacity * safety_factor
        assert required_capacity >= base_capacity
