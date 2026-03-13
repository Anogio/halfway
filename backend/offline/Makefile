.PHONY: setup test lint format prepare-data ingest build-graph build-grid validate-data export build-all build-all-from-sources

UV_CACHE_DIR ?= .uv-cache

define require_city
	@test -n "$(CITY)" || (echo "CITY is required (example: CITY=paris make $@)" && exit 1)
endef

setup:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync

test:
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m unittest discover -s tests -p "test_*.py"

lint:
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check src tests
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m compileall -q src tests

format:
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff format src tests

prepare-data:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli prepare-data --city "$(CITY)"

ingest:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli ingest --city "$(CITY)"

build-graph:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli build-graph --city "$(CITY)"

build-grid:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli build-grid --city "$(CITY)"

validate-data:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli validate --city "$(CITY)"

export:
	$(require_city)
	PYTHONPATH=src:../shared/src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run python -m transit_offline.cli export --city "$(CITY)"

build-all: ingest build-graph build-grid validate-data export

build-all-from-sources: prepare-data build-all
