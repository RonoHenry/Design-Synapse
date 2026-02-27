#!/usr/bin/env python3
"""
Example demonstrating circuit breaker pattern with monitoring.
"""

import asyncio
import time
from datetime import datetime

from circuit_breaker import (CircuitBreaker, CircuitBreakerConfig,
                             CircuitBreakerOpenException, circuit_breaker,
                             get_all_circuit_breaker_status)
from monitoring import get_resilience_monitor


class ExampleService:
    """Example service that can fail."""

    def __init__(self):
        self.call_count = 0
        self.should_fail = False

    def call(self, data: str = "test") -> str:
        """Service call that may fail."""
        self.call_count += 1
        print(f"Service call #{self.call_count} with data: {data}")

        if self.should_fail:
            raise ConnectionError(f"Service unavailable (call #{self.call_count})")

        return f"Success: {data} (call #{self.call_count})"


def demonstrate_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("=== Circuit Breaker Pattern Demo ===\n")

    # Create service and circuit breaker
    service = ExampleService()
    config = CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=2,  # 2 seconds
        success_threshold=2,
        timeout=5,
    )
    breaker = CircuitBreaker("example-service", config)

    print("1. Testing successful calls...")
    for i in range(3):
        try:
            result = breaker.call(service.call, f"request-{i+1}")
            print(f"   ✓ {result}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    print(f"\nCircuit breaker state: {breaker.state}")
    print(f"Status: {breaker.status}")

    print("\n2. Testing failure scenario...")
    service.should_fail = True

    # Make calls that will fail and open the circuit
    for i in range(5):
        try:
            result = breaker.call(service.call, f"failing-request-{i+1}")
            print(f"   ✓ {result}")
        except CircuitBreakerOpenException as e:
            print(f"   ⚡ Circuit breaker open: {e}")
        except Exception as e:
            print(f"   ✗ Service error: {e}")

    print(f"\nCircuit breaker state: {breaker.state}")
    print(f"Status: {breaker.status}")


if __name__ == "__main__":
    demonstrate_circuit_breaker()
