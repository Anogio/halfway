.PHONY: setup test lint format run run-browser-check baseline

UV_CACHE_DIR ?= .uv-cache

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync

test:
	CORS_ALLOW_ORIGIN_REGEX=$${CORS_ALLOW_ORIGIN_REGEX:-^http://(localhost|127\.0\.0\.1):3[0-9][0-9][0-9]$$} PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m unittest discover -s tests -p "test_*.py"

lint:
	PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check src tests shared/src scripts
	PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m compileall -q src tests shared/src

format:
	PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff format src tests shared/src scripts

baseline:
	@test -n "$$BASELINE_CITY" || (echo "BASELINE_CITY is required (example: BASELINE_CITY=paris make baseline)" && exit 1)
	PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python scripts/generate_baseline_snapshot.py --city "$$BASELINE_CITY"

run:
	CORS_ALLOW_ORIGIN_REGEX=$${CORS_ALLOW_ORIGIN_REGEX:-^http://(localhost|127\.0\.0\.1):3[0-9][0-9][0-9]$$} PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run uvicorn transit_backend.api.server:app --host $${HOST:-127.0.0.1} --port $${PORT:-8000} --reload

run-browser-check:
	CORS_ALLOW_ORIGIN=$${CORS_ALLOW_ORIGIN:-http://127.0.0.1:3010} PYTHONPATH=src:shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run uvicorn transit_backend.api.server:app --host $${HOST:-127.0.0.1} --port $${PORT:-8001} --reload
