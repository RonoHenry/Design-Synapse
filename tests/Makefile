# Makefile for integration testing
# This defines the expected interface for running integration tests

.PHONY: help install test test-unit test-integration test-all clean setup teardown

# Default target
help:
	@echo "Integration Test Commands:"
	@echo "  make install          - Install test dependencies"
	@echo "  make setup           - Set up test infrastructure"
	@echo "  make test            - Run all integration tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-all        - Run all tests with coverage"
	@echo "  make teardown        - Clean up test infrastructure"
	@echo "  make clean           - Clean up all test artifacts"

# Install test dependencies
install:
	@echo "📦 Installing integration test dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Set up test infrastructure
setup:
	@echo "🚀 Setting up integration test infrastructure..."
	docker-compose -f docker-compose.integration.yml -p integration-tests up -d --build
	@echo "⏳ Waiting for services to be ready..."
	sleep 30
	@echo "✅ Infrastructure ready"

# Run integration tests only
test-integration:
	@echo "🧪 Running integration tests..."
	python -m pytest integration/ -v -m integration --tb=short

# Run unit tests only
test-unit:
	@echo "🧪 Running unit tests..."
	python -m pytest unit/ -v -m "not integration" --tb=short

# Run all tests
test: test-integration

# Run all tests with coverage
test-all:
	@echo "🧪 Running all tests with coverage..."
	python run_integration_tests.py

# Tear down test infrastructure
teardown:
	@echo "🧹 Tearing down integration test infrastructure..."
	docker-compose -f docker-compose.integration.yml -p integration-tests down -v --remove-orphans
	@echo "✅ Infrastructure cleaned up"

# Clean up all test artifacts
clean: teardown
	@echo "🧹 Cleaning up test artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	@echo "✅ All artifacts cleaned up"

# Quick test cycle (setup, test, teardown)
test-cycle: setup test teardown

# Development mode - keep infrastructure running
dev-setup: setup
	@echo "🔧 Development mode: infrastructure running"
	@echo "Run 'make test-integration' to run tests"
	@echo "Run 'make teardown' when done"

# Check test infrastructure status
status:
	@echo "📊 Checking integration test infrastructure status..."
	docker-compose -f docker-compose.integration.yml -p integration-tests ps

# View logs from test infrastructure
logs:
	@echo "📋 Viewing integration test infrastructure logs..."
	docker-compose -f docker-compose.integration.yml -p integration-tests logs -f

# Run specific test file
test-file:
	@echo "🧪 Running specific test file: $(FILE)"
	python -m pytest $(FILE) -v --tb=short

# Run tests with specific marker
test-marker:
	@echo "🧪 Running tests with marker: $(MARKER)"
	python -m pytest -v -m "$(MARKER)" --tb=short
