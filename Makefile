.PHONY: setup build test test-unit test-integration types lint format ci clean help

setup:
	uv sync --group dev

build:
	@echo "==> Building and installing package..."
	maturin develop

test: build
	@echo "==> Running tests..."
	uv run pytest tests/

test-unit: build
	@echo "==> Running unit tests..."
	uv run uv run pytest tests/ -m "not integration" -v

test-integration: build
	@echo "==> Running integration tests..."
	uv run uv run pytest tests/ -m integration -v

types:
	@echo "==> Running type checker..."
	uv run ty check python/ tests/

lint:
	@echo "==> Running linter..."
	uv run ruff check .
	cargo clippy -- -D warnings

format:
	@echo "==> Running code formatters..."
	uv run ruff format .
	cargo fmt

format-check:
	@echo "==> Checking code formatting..."
	uv run ruff format --check .
	cargo fmt --check

ci: format-check lint types test
	@echo "==> All CI checks passed!"
