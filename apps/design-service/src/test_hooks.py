"""Test module for demonstrating pre-commit hooks functionality.

This module contains sample functions to verify that our pre-commit hooks
are working correctly and enforcing our code quality standards.
"""
from typing import Dict, List


def calculate_something(x: int, y: int, debug: bool = False) -> int:
    """Calculate the sum of two numbers with optional debugging.

    Args:
        x: First number to add
        y: Second number to add
        debug: Whether to print debug information

    Returns:
        The sum of x and y
    """
    if debug:
        print("debugging")

    result = x + y
    return result


def process_data(data: Dict[str, any]) -> List[str]:
    """Process a dictionary and convert its items to formatted strings.

    Args:
        data: Dictionary containing key-value pairs to process

    Returns:
        List of strings formatted as 'key:value'
    """
    results = []
    for key, value in data.items():
        if value:
            results.append(f"{key}:{value}")
    return results


if __name__ == "__main__":
    test_data = {"a": 1, "b": 2, "c": 3}
    print(process_data(test_data))
    print(calculate_something(1, 2, debug=True))
