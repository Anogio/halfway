# Backend Multi-City Plan (Final-State, No Backward Compatibility)

Execution checklist: `BACKEND_MULTI_CITY_EXECUTION_CHECKLIST.md`

## 1. Scope And Rules
- Goal: make backend and offline pipeline strictly multi-city.
- Keep only Paris data in practice for now, but architecture must support N cities immediately.
- No default city anywhere (config, API, server state, geocoding, metadata).
- Shared runtime knobs remain global (walk speed, caps, search radii, etc.).
- City-specific values move under city entries (GTFS path, artifact version, bbox/view, validation pairs, geocoding filters).
- No transition layer: breaking current frontend/backend contracts is acceptable.

## 2. Current Constraints Confirmed In Code
- Single GTFS input path in config.
- Single artifact version in config.
- Offline CLI has no city parameter.
- Runtime server loads one artifact set at startup.
- Compute endpoints are city-agnostic today.
- Geocoding has hardcoded FR and Ile-de-France defaults.
- Validation wording/logic still references Paris center.

## 3. Target Architecture
- Single server process loads all configured cities at startup.
- In-memory state is a map: `cities_by_id[city_id] -> CityRuntimeState`.
- Each request to compute/geocode endpoints must carry `city`.
- Artifacts are city-scoped on disk, with independent version sequence per city.
- Metadata provides only frontend-needed city bootstrap info.

## 4. Workstream A: Config Refactor (Shared + City Catalog)
- Replace single-city settings model with:
  - shared sections: `service`, `modes`, `search`, `weights`, `grid`, `runtime`, `graph`
  - city catalog: `cities.<city_id>.*`
- Per-city required keys:
  - `label`
  - `artifact_version`
  - `paths.gtfs_input`
  - `scope.use_bbox`
  - `scope.bbox`
  - `scope.default_view`
  - `validation.*` and `validation.od_pairs`
  - `geocoding.country_codes`
  - `geocoding.viewbox`
  - `geocoding.bounded`
- Parser validation:
  - city map is non-empty
  - no empty city ids
  - each city has complete required keys
  - per-city od pairs are valid
- Keep one source of truth for settings (`backend/config/settings.toml`).

## 5. Workstream B: Data Layout And Offline Pipeline
### 5.1 Folder layout
- GTFS input: `backend/offline/data/gtfs/<city_id>/...`
- Interim: `backend/offline/data/interim/<city_id>/...`
- Artifacts: `backend/offline/data/artifacts/<city_id>/...`

### 5.2 Artifact naming
- Keep current file naming inside each city folder:
  - `graph_<version>_weekday.json`
  - `nodes_<version>.csv`
  - `grid_cells_<version>.csv`
  - `grid_links_<version>.csv`
  - `validation_<version>.json`
  - `manifest_<version>.json`
  - reports (`graph_report_<version>.json`, `grid_report_<version>.json`)
- Version sequence is per city (`paris: v0,v1,...`, `london: v0,v1,...`).

### 5.3 CLI and Makefile changes
- Offline CLI requires `--city <city_id>` for:
  - `ingest`
  - `build-graph`
  - `build-grid`
  - `validate`
  - `export`
- `backend/offline/Makefile` requires `CITY` and forwards it.
- Hard fail when city is missing or unknown.

## 6. Workstream C: Paris Input/Output Migration (Critical, Non-Loss)
- Pre-migration checksum inventory:
  - `gouv_paris_gtfs-export/*`
  - `backend/offline/data/interim/*`
  - `backend/offline/data/artifacts/*`
- Move GTFS:
  - `gouv_paris_gtfs-export/` -> `backend/offline/data/gtfs/paris/`
- Move interim:
  - `backend/offline/data/interim/*` -> `backend/offline/data/interim/paris/`
- Move artifacts:
  - `backend/offline/data/artifacts/*` -> `backend/offline/data/artifacts/paris/`
- Recompute checksums and compare with pre-migration inventory.
- Update `.gitignore` to new city paths while preserving tracked release artifacts.
- Do not delete legacy paths until checksum match is confirmed.

## 7. Workstream D: Backend Runtime And APIs
### 7.1 Server state
- Introduce `CityRuntimeState` containing:
  - runtime artifacts
  - spatial index
  - grid topology
  - per-city origin grid cache
- App state contains:
  - shared params
  - `cities_by_id`
- Startup loads all cities; fail fast if any configured city cannot load.

### 7.2 Endpoint contract changes
- Keep:
  - `GET /health`
  - `GET /metadata`
  - `POST /heatmap`
  - `POST /multi_isochrones`
  - `POST /multi_path`
  - `GET /geocode`
  - `GET /reverse_geocode`
- Remove:
  - `POST /isochrones`
  - `POST /path`
- City required:
  - POST payloads include `"city": "<city_id>"`
  - geocoding queries include `city=<city_id>`
- Unknown/missing city -> `400`.

### 7.3 Metadata minimization
- Keep only fields needed by frontend bootstrap/city selection:
  - `cities: [{ id, label, default_view, bbox }]`
- Remove backend-internal extras from metadata if frontend does not consume them:
  - counts
  - params
  - manifest
  - single-city version/profile

## 8. Workstream E: Geocoding Must Be City-Scoped
- Remove hardcoded FR and Ile-de-France defaults from backend code.
- Resolve geocoding params from `city` config:
  - country codes
  - viewbox
  - bounded flag
- Keep provider URL/user-agent/timeout as global env controls.

## 9. Workstream F: Remove Paris-Specific Assumptions
- Replace Paris-specific comments/messages with city-neutral wording.
- Ensure validation reachability metric uses selected city view center from city config.
- Add grep gate in CI or local checks for hardcoded Paris-only markers in backend/config paths.

## 10. Workstream G: Tests And Verification
- Shared settings tests:
  - parse valid multi-city config
  - reject missing city fields
  - reject unknown city lookups
- Offline tests:
  - each command requires city
  - city-scoped read/write paths are correct
- API contract tests:
  - city required for compute/geocode endpoints
  - unknown city rejected
- Integration tests:
  - load two synthetic cities simultaneously
  - confirm no cross-city leakage in results
- Migration verification:
  - checksum parity pre/post move
  - existing Paris `v1` artifacts still load and serve correctly from `artifacts/paris`

## 11. Workstream H: Documentation
- Update:
  - root README
  - backend README
  - offline README
  - runbooks referencing removed endpoints
- Add `AGENTS.md` section: "How to add a new city"
  - required config keys
  - where GTFS files go
  - offline commands to run
  - expected artifacts
  - mandatory validation checks

## 12. Execution Order
1. Add new settings schema/parser/types for city catalog.
2. Implement city-aware path resolvers for offline/backend.
3. Migrate Paris files to city folders with checksum verification.
4. Refactor offline CLI + pipelines for required `--city`.
5. Refactor backend runtime to load all cities.
6. Refactor API contracts and handlers to require city.
7. Remove `/isochrones` and `/path`.
8. Make geocoding city-scoped.
9. Minimize metadata to frontend-used fields.
10. Remove residual Paris assumptions and update docs/tests.

## 13. Done Criteria
- Backend boots with all configured cities loaded.
- No default city exists in code/config/API.
- All non-health endpoints requiring spatial context reject missing city.
- Paris data remains intact after migration (checksum verified).
- Frontend-relevant metadata is available and minimal.
- `/isochrones` and `/path` are fully removed.
- Backend tests and offline tests pass under the new strict contract.

## Frontend Migration Recommendations (Brief)
- Add city selection state in frontend and send `city` on:
  - `POST /multi_isochrones`
  - `POST /multi_path`
  - `GET /geocode`
  - `GET /reverse_geocode`
- Update metadata client type/parser to consume `cities[]` and use selected city's `default_view`.
- Remove frontend calls/types for deleted endpoints (`/isochrones`, `/path`).
- Keep UX simple initially: one explicit city picker, no automatic fallback.
