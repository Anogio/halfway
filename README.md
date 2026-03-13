# Transportation Heatmap (Multi-City Backend)

Canonical plan: `BACKEND_MULTI_CITY_PLAN.md`.
Execution checklist: `BACKEND_MULTI_CITY_EXECUTION_CHECKLIST.md`.

This repository contains:
- `backend/offline`: offline GTFS ingest, graph/grid precomputation, validation.
- `backend`: runtime API that serves travel-time heatmaps from precomputed artifacts.
- `frontend`: Next.js map client.
- `backend/config/settings.toml`: single shared configuration source.

## Architecture Summary
- Backend/offline are multi-city by design.
- All city-specific settings live under `cities.<city_id>` in `backend/config/settings.toml`.
- Shared runtime knobs remain global (`search`, `weights`, `grid`, `runtime`, etc.).
- Artifacts are city-scoped on disk:
  - `backend/offline/data/artifacts/<city_id>/...`

## Data Layout
- GTFS input: `backend/offline/data/gtfs/<city_id>/`
- Interim outputs: `backend/offline/data/interim/<city_id>/`
- Runtime artifacts: `backend/offline/data/artifacts/<city_id>/`
- Archived prior outputs: `backend/offline/data/artifacts/<city_id>/old/`

## Offline Commands
All offline build commands require explicit `CITY`.

```bash
make build-offline CITY=paris
# equivalent full pipeline:
make -C backend/offline ingest CITY=paris
make -C backend/offline build-graph CITY=paris
make -C backend/offline build-grid CITY=paris
make -C backend/offline validate-data CITY=paris
make -C backend/offline export CITY=paris
```

## Runtime API
- `GET /health`
- `GET /metadata`
- `POST /heatmap` (requires `city`)
- `POST /multi_isochrones` (requires `city`)
- `POST /multi_path` (requires `city`)
- `GET /geocode` (requires `city` query param)
- `GET /reverse_geocode` (requires `city` query param)

Removed endpoints:
- `POST /isochrones`
- `POST /path`

## Baseline
Baseline snapshot generation now requires explicit city:

```bash
BASELINE_CITY=paris make baseline
```

## Requirements
- Python 3.13+
- Node 24.x
- `uv` 0.10+

## Standard workflow
```bash
make doctor
make setup
make lint
make test
```
