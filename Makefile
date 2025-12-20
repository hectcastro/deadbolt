.PHONY: setup build test test-unit test-integration types lint format ci clean help

setup:
	uv sync --group dev

build:
	@echo "==> Building and installing package..."
	maturin develop

test: build
	@echo "==> Running tests..."
	pytest tests/

test-unit: build
	@echo "==> Running unit tests..."
	pytest tests/ -m "not integration" -v

test-integration: build
	@echo "==> Running integration tests..."
	pytest tests/ -m integration -v

types:
	@echo "==> Running type checker..."
	ty check python/ tests/

lint:
	@echo "==> Running linter..."
	ruff check .
	cargo clippy -- -D warnings

format:
	@echo "==> Running code formatters..."
	ruff format .
	cargo fmt

format-check:
	@echo "==> Checking code formatting..."
	ruff format --check .
	cargo fmt --check

ci: format-check lint types test
	@echo "==> All CI checks passed!"
