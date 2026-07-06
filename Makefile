.PHONY: install test test-core test-mcp lint typecheck format audit

install:
	uv sync --extra otel

test: test-core test-mcp

test-core:
	uv run pytest packages/fss-core/tests -v

test-mcp:
	uv run pytest packages/fss-mcp/tests -v

lint:
	uv run ruff check .

typecheck:
	uv run mypy packages/

format:
	uv run ruff format .
	uv run ruff check --fix .

audit:
	uv run pip-audit packages/fss-core packages/fss-mcp
