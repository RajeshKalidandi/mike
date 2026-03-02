.PHONY: help test test-unit test-integration test-e2e test-all test-coverage test-fast test-slow lint format clean

# Default target
help:
	@echo "ArchitectAI Testing Commands"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test              Run all tests"
	@echo "  make test-unit         Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-e2e          Run E2E tests only"
	@echo "  make test-fast         Run fast tests (exclude slow)"
	@echo "  make test-slow         Run slow tests only"
	@echo "  make test-coverage     Run tests with coverage report"
	@echo "  make test-coverage-html Run tests and open HTML coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              Run linters (ruff, mypy)"
	@echo "  make format            Format code (black, isort)"
	@echo "  make fix               Fix auto-fixable issues"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             Clean up test artifacts"
	@echo "  make clean-all         Clean everything including coverage"

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest -m unit

# Run integration tests only
test-integration:
	pytest -m integration

# Run E2E tests only
test-e2e:
	pytest -m e2e

# Run fast tests (exclude slow)
test-fast:
	pytest -m "not slow"

# Run slow tests only
test-slow:
	pytest -m slow

# Run tests with coverage report
test-coverage:
	pytest --cov=src/architectai --cov-report=term-missing --cov-report=html --cov-report=xml

# Run tests and open HTML coverage report (macOS)
test-coverage-html: test-coverage
	open htmlcov/index.html

# Run tests in parallel
test-parallel:
	pytest -n auto

# Run tests with verbose output
test-verbose:
	pytest -v --tb=long

# Run specific test file
test-scanner:
	pytest tests/unit/test_scanner.py -v

test-parser:
	pytest tests/unit/test_parser.py -v

test-agents:
	pytest tests/unit/test_agents/ -v

# Run performance tests
test-performance:
	pytest tests/performance/ -v

# Lint code
lint:
	ruff check src tests
	mypy src

# Format code
format:
	black src tests
	isort src tests

# Fix auto-fixable issues
fix:
	ruff check --fix src tests
	black src tests
	isort src tests

# Clean up test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete

# Clean everything including coverage
clean-all: clean
	rm -rf htmlcov
	rm -f coverage.xml
	rm -f .coverage
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Install all dependencies
install-all:
	pip install -e ".[all]"
