# Backend Multi-City Execution Checklist

Reference plan: `BACKEND_MULTI_CITY_PLAN.md`

This checklist is final-state only:
- No default city anywhere.
- No backward-compatibility layer.
- City is mandatory for all non-health spatial endpoints.

## Phase 0 - Baseline Snapshot And Safety Net

### 0.1 Baseline commands
- [ ] Run `make lint`
- [ ] Run `make test`
- [ ] Run `make baseline`
- [ ] Save command outputs to `docs/debug/multi-city-migration-baseline/` (new folder)

### 0.2 Inventory current data before migration
- [ ] Record GTFS source inventory:
  - `find gouv_paris_gtfs-export -type f | sort`
- [ ] Record current interim inventory:
  - `find backend/offline/data/interim -type f | sort`
- [ ] Record current artifacts inventory:
  - `find backend/offline/data/artifacts -type f | sort`
- [ ] Generate pre-migration checksums for all above files.

### 0.3 Safety gate
- [ ] Confirm checksum files are committed before moving data.
- [ ] Confirm rollback procedure is prepared (restore paths from checksum manifest + git status).

## Phase 1 - Shared Settings Schema Refactor To City Catalog

### 1.1 Files to modify
- [ ] `backend/config/settings.toml`
- [ ] `backend/shared/src/transit_shared/settings_schema.py`
- [ ] `backend/shared/src/transit_shared/settings_parser.py`
- [ ] `backend/shared/src/transit_shared/settings.py`
- [ ] `backend/tests/helpers.py`
- [ ] `backend/offline/tests/helpers.py`
- [x] Consolidate on `backend/config/settings.toml` as the only settings file.

### 1.2 Required structural changes
- [ ] Replace single-city settings fields with `cities.<city_id>` map.
- [ ] Keep shared knobs global (`service`, `modes`, `search`, `weights`, `grid`, `runtime`, `graph`).
- [ ] Introduce per-city settings objects:
  - [ ] `label`
  - [ ] `artifact_version`
  - [ ] `paths.gtfs_input`
  - [ ] `scope.use_bbox`
  - [ ] `scope.bbox`
  - [ ] `scope.default_view`
  - [ ] `validation` (including `od_pairs`)
  - [ ] `geocoding.country_codes`
  - [ ] `geocoding.viewbox`
  - [ ] `geocoding.bounded`
- [ ] Ensure parser rejects empty city map and invalid city ids.

### 1.3 Automated tests
- [ ] Add parser test: valid one-city config parses.
- [ ] Add parser test: valid two-city config parses.
- [ ] Add parser test: missing per-city keys fails.
- [ ] Add parser test: empty `cities` fails.
- [ ] Add parser test: malformed `bbox` or `default_view` fails.
- [ ] Update all helpers to generate city-catalog settings fixtures.

### 1.4 Manual checks
- [ ] Start Python REPL with parser and parse config once.
- [ ] Verify parsed object exposes all configured city ids.

## Phase 2 - City-Aware Path Resolution (Offline + Backend)

### 2.1 Files to modify
- [ ] `backend/offline/src/transit_offline/common/config.py`
- [ ] `backend/src/transit_backend/config/settings.py`

### 2.2 Required changes
- [ ] Add city resolver API:
  - [ ] `resolve_city_config(city_id)` in offline config.
  - [ ] backend config exposes city catalog and city path resolvers.
- [ ] Remove single `gtfs_input` and single artifact-version assumptions in config objects.

### 2.3 Automated tests
- [ ] Unit test: resolving known city returns expected paths.
- [ ] Unit test: unknown city raises explicit error.
- [ ] Unit test: resolved artifact dir is city-scoped.

### 2.4 Manual checks
- [ ] Print resolved paths for `paris` and verify they point to city folders.

## Phase 3 - Paris Data Migration (Non-Loss, Critical)

### 3.1 Prepare city directories
- [ ] Create:
  - [ ] `backend/offline/data/gtfs/paris`
  - [ ] `backend/offline/data/interim/paris`
  - [ ] `backend/offline/data/artifacts/paris`

### 3.2 Move data
- [ ] Move GTFS files from `gouv_paris_gtfs-export/` to `backend/offline/data/gtfs/paris/`.
- [ ] Move interim files into `backend/offline/data/interim/paris/`.
- [ ] Move artifacts into `backend/offline/data/artifacts/paris/`.

### 3.3 Verify integrity
- [ ] Recompute checksums after move.
- [ ] Compare pre/post checksum manifests; all files must match byte-for-byte.
- [ ] Confirm `graph_v1_weekday.json` and other tracked Paris artifacts still exist in new path.

### 3.4 Update ignore/include rules
- [ ] Update `.gitignore` for city-scoped interim/artifacts paths.
- [ ] Preserve tracking of Paris release artifacts under new location.

### 3.5 Manual checks
- [ ] `ls` old paths show empty or removed.
- [ ] `ls` new paths show all expected Paris files.
- [ ] `git status` does not show unintended deletions of required tracked files.

## Phase 4 - Offline CLI And Pipeline City Parameterization

### 4.1 Files to modify
- [ ] `backend/offline/src/transit_offline/cli.py`
- [ ] `backend/offline/src/transit_offline/ingest/pipeline.py`
- [ ] `backend/offline/src/transit_offline/graph/pipeline.py`
- [ ] `backend/offline/src/transit_offline/grid/pipeline.py`
- [ ] `backend/offline/src/transit_offline/validation/pipeline.py`
- [ ] `backend/offline/src/transit_offline/export/pipeline.py`
- [ ] `backend/offline/Makefile`

### 4.2 Required changes
- [ ] `--city` required for each offline command.
- [ ] Fail with clear error if city missing/unknown.
- [ ] Ensure all read/write paths are city-scoped.
- [ ] Keep artifact naming unchanged inside each city folder.

### 4.3 Automated tests
- [ ] CLI test: missing `--city` fails.
- [ ] CLI test: unknown city fails.
- [ ] Pipeline tests updated to pass city and assert city-scoped outputs.
- [ ] Validation test checks city-neutral wording (no Paris-specific message strings).

### 4.4 Manual checks
- [ ] Run:
  - [ ] `make -C backend/offline ingest CITY=paris`
  - [ ] `make -C backend/offline build-graph CITY=paris`
  - [ ] `make -C backend/offline build-grid CITY=paris`
  - [ ] `make -C backend/offline validate-data CITY=paris`
  - [ ] `make -C backend/offline export CITY=paris`
- [ ] Verify only `.../paris/` files are touched.

## Phase 5 - Backend Runtime Loads All Cities

### 5.1 Files to modify
- [ ] `backend/src/transit_backend/api/state.py`
- [ ] `backend/src/transit_backend/core/artifacts.py` (if loader helpers need city metadata)

### 5.2 Required changes
- [ ] Introduce `CityRuntimeState` object.
- [ ] Build `cities_by_id` map at startup.
- [ ] Build per-city spatial index, topology, and origin cache.
- [ ] Remove single-runtime app state assumptions.
- [ ] Startup fails if any configured city cannot load.

### 5.3 Automated tests
- [ ] State-loading test: one city loads.
- [ ] State-loading test: two cities load.
- [ ] State-loading test: one missing artifact causes startup failure with city id in error.

### 5.4 Manual checks
- [ ] Start backend once; confirm startup logs list loaded city ids.

## Phase 6 - API Contracts Require City (No Fallback)

### 6.1 Files to modify
- [ ] `backend/src/transit_backend/api/contracts.py`
- [ ] `backend/src/transit_backend/api/routing_handlers.py`
- [ ] `backend/src/transit_backend/api/server.py`
- [ ] `backend/tests/api_integration_base.py`
- [ ] `backend/tests/test_api_contracts_*.py`
- [ ] `backend/tests/test_api_integration_routes.py`

### 6.2 Required changes
- [ ] Add shared parser for `city` in request payloads.
- [ ] Require city in:
  - [ ] `/heatmap`
  - [ ] `/multi_isochrones`
  - [ ] `/multi_path`
- [ ] Route each request to `cities_by_id[city]`.
- [ ] Return `400` for missing/unknown city.

### 6.3 Automated tests
- [ ] Contract test: each endpoint rejects missing city.
- [ ] Contract test: each endpoint rejects unknown city.
- [ ] Integration test: endpoint succeeds with `city=paris`.
- [ ] Integration test: results for city A and city B differ when fixtures differ.

### 6.4 Manual checks (curl)
- [ ] Missing city:
  - [ ] `POST /multi_isochrones` -> 400
  - [ ] `POST /multi_path` -> 400
- [ ] Unknown city:
  - [ ] `POST /multi_isochrones` with `city=unknown` -> 400
- [ ] Valid city:
  - [ ] `POST /multi_isochrones` with `city=paris` -> 200

## Phase 7 - Remove Unused `/isochrones` And `/path`

### 7.1 Files to modify
- [ ] `backend/src/transit_backend/api/server.py`
- [ ] `backend/src/transit_backend/api/routing_handlers.py`
- [ ] `backend/src/transit_backend/api/contracts.py`
- [ ] `backend/tests/test_api_integration_routes.py`
- [ ] `backend/tests/test_api_contracts_isochrones.py`
- [ ] `backend/tests/test_api_contracts_paths.py`
- [ ] `backend/scripts/generate_baseline_snapshot.py`
- [ ] Docs referencing removed endpoints.

### 7.2 Required changes
- [ ] Remove routes and dead handlers.
- [ ] Remove dead request parsers/types.
- [ ] Update baseline generator to use retained endpoints only.

### 7.3 Automated tests
- [ ] Ensure no test references removed endpoints.
- [ ] Add test that `POST /isochrones` and `POST /path` return 404.

### 7.4 Manual checks
- [ ] Hit removed endpoints and confirm 404.

## Phase 8 - City-Scoped Geocoding

### 8.1 Files to modify
- [ ] `backend/src/transit_backend/api/geocoding.py`
- [ ] shared settings schema/parser for per-city geocoding keys
- [ ] geocoding tests

### 8.2 Required changes
- [ ] Require `city` query param on `/geocode` and `/reverse_geocode`.
- [ ] Resolve country codes/viewbox/bounded from selected city config.
- [ ] Remove hardcoded FR and Ile-de-France defaults.
- [ ] Keep global provider URL, timeout, user-agent env controls.

### 8.3 Automated tests
- [ ] Test: missing city on geocode -> 400.
- [ ] Test: unknown city -> 400.
- [ ] Test: provider params include selected city's viewbox/countrycodes.

### 8.4 Manual checks
- [ ] Call `/geocode?q=test&city=paris` and inspect mocked provider params in tests/logs.

## Phase 9 - Metadata Minimization To Frontend Needs

### 9.1 Files to modify
- [ ] `backend/src/transit_backend/api/contracts.py`
- [ ] `backend/src/transit_backend/api/server.py`
- [ ] backend metadata tests

### 9.2 Required changes
- [ ] `/metadata` returns only:
  - [ ] `cities: [{ id, label, default_view, bbox }]`
- [ ] Ensure no default/single-city metadata fields remain.

### 9.3 Automated tests
- [ ] Metadata contract test for exact expected keys.
- [ ] Metadata test ensures no forbidden legacy keys are present.

### 9.4 Manual checks
- [ ] `GET /metadata` returns city list and view/bbox values for Paris.

## Phase 10 - Remove Residual Paris-Specific Assumptions

### 10.1 Code and config sweep
- [ ] Replace Paris-specific comments and failure strings.
- [ ] Ensure validation messages are city-neutral.
- [ ] Ensure no hardcoded `gouv_paris_gtfs-export` path remains.

### 10.2 Automated grep gate
- [ ] Add/execute grep checks:
  - [ ] `rg -n "gouv_paris_gtfs-export|Ile-de-France|Île-de-France" backend/src backend/offline/src backend/shared/src config`
  - [ ] verify expected zero or intentional docs-only hits.

### 10.3 Manual checks
- [ ] Read validation output and confirm it does not mention Paris unless city label is intentionally injected.

## Phase 11 - Documentation Updates

### 11.1 Files to modify
- [ ] `README.md`
- [ ] `backend/README.md`
- [ ] `backend/offline/README.md`
- [ ] `AGENTS.md`
- [ ] debug/runbooks that mention removed endpoints

### 11.2 Required doc updates
- [ ] New folder layout by city.
- [ ] Offline command usage with required `CITY`.
- [ ] API contract now requires city.
- [ ] Removed endpoint documentation (`/isochrones`, `/path`).
- [ ] AGENTS section "How to add a new city":
  - [ ] required config entries
  - [ ] GTFS placement path
  - [ ] exact offline build commands
  - [ ] validation and smoke checks

## Phase 12 - Frontend Migration Touchpoints (Brief, For Follow-Up)
- [ ] Add city state in frontend app model.
- [ ] Send `city` in `multi_isochrones`, `multi_path`, `geocode`, `reverse_geocode` calls.
- [ ] Update metadata parsing to city list format.
- [ ] Remove frontend code paths for deleted endpoints.
- [ ] Verify map initializes from selected city `default_view`.

## Full Automated Test Matrix (Run Order)

### A. Fast unit/contract loops during development
- [ ] `make -C backend test` (after each backend/API phase)
- [ ] `make -C backend/offline test` (after each offline phase)

### B. Full backend/offline verification before merge
- [ ] `make -C backend lint`
- [ ] `make -C backend/offline lint`
- [ ] `make -C backend/offline test`
- [ ] `make -C backend test`

### C. End-to-end backend + frontend API contract sanity
- [ ] `make test` at repo root.
- [ ] Frontend unit tests pass after API typing updates.

### D. Data migration verification automation
- [ ] Pre/post checksum comparison script returns exact match.
- [ ] City-scoped Paris artifact loader test passes.

## Manual Test Matrix (Thorough)

### 1. Startup and metadata
- [ ] Backend starts successfully with city catalog.
- [ ] Startup fails cleanly if one configured city has missing artifacts.
- [ ] `/metadata` returns only expected city-list payload.

### 2. Compute endpoints
- [ ] `POST /multi_isochrones` with valid Paris city returns 200 and feature collection.
- [ ] `POST /multi_path` with valid Paris city returns 200 and paths.
- [ ] Missing city rejected with 400.
- [ ] Unknown city rejected with 400.

### 3. Removed endpoints
- [ ] `POST /isochrones` returns 404.
- [ ] `POST /path` returns 404.

### 4. Geocoding
- [ ] `GET /geocode` without city returns 400.
- [ ] `GET /reverse_geocode` without city returns 400.
- [ ] Valid city geocode works and uses city bounds.
- [ ] Unknown city geocode returns 400.

### 5. Data and artifact integrity
- [ ] Paris files exist only in new city-scoped locations.
- [ ] Checksums match pre-migration values.
- [ ] Existing Paris v1 artifacts still serve requests correctly.

### 6. No hidden Paris assumptions
- [ ] Grep scan passes for hardcoded Paris-only backend config/code markers.
- [ ] Validation/report messages are city-neutral.

## Final Merge Gate (All Must Be True)
- [ ] No default city exists in settings schema, parser, runtime state, or API behavior.
- [ ] Every non-health endpoint that depends on spatial context requires city.
- [ ] Paris migration is checksum-verified and complete.
- [ ] Removed endpoints are absent from code/tests/docs.
- [ ] Metadata shape is minimal and frontend-oriented.
- [ ] Backend and offline tests are green.
- [ ] Docs and AGENTS instructions are updated and consistent.
