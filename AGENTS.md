# Agent Instructions

- For any frontend user-facing text change, always add or update both English and French entries in:
  - `frontend/src/i18n/messages/en.ts`
  - `frontend/src/i18n/messages/fr.ts`
- Do not introduce hardcoded user-facing strings in frontend components or hooks; use the i18n catalog.
- If a new translation key is added, both language files must be updated in the same change.
- Keep routing and isochrone debug statistics behind an explicit request-level `debug` flag that defaults to `false`.
- Do not compute expensive debug-only routing or isochrone statistics on the default production path.
- Store project plans, implementation option writeups, and similar planning documents in `docs/debug/` unless the user explicitly asks for a different location.
- Keep a stable browser-automation map adapter on `window.__transitMap` with `getSize()`, `containerPointToLatLng()`, `fire("click", { latlng })`, and only the minimal extra debug helpers that are actually used by the Playwright flows.
- When changing map libraries, update Playwright selectors/helpers away from library-specific DOM classes (`leaflet-*`, etc.) and preserve the `window.__transitMap` contract.
- For browser debugging of map interactions, prefer Playwright scripts/tests that use `window.__transitMap` over fragile canvas ref clicks.
- For MapLibre/WebGL checks on this machine, prefer a headed Playwright browser. Headless Chromium may fail to create a WebGL context and never initialize `window.__transitMap`.
- Keep map/WebGL E2E coverage in dedicated `*-map.spec.ts` files so Playwright can run them in a separate headed project while the rest of the suite stays headless.
- Keep default Playwright/CI runs on `http://127.0.0.1:3000` for deterministic managed web-server startup.
- When local backend/frontend test servers are already running and the frontend is only reachable on `localhost`, use `frontend` scripts that set both `PLAYWRIGHT_BASE_URL=http://localhost:3000` and `PW_SKIP_WEBSERVER=1` (`npm run e2e:existing`, `npm run e2e:map:existing`) to avoid duplicate Playwright web-server launches.

## Adding A New City (Backend/Offline)

- Add a new city entry in `backend/config/settings.toml` under `cities.<city_id>` with:
  - `label`
  - `artifact_version`
  - `paths.gtfs_input`
  - `scope.use_bbox`, `scope.bbox`, `scope.default_view`
  - `geocoding.country_codes`, `geocoding.viewbox`, `geocoding.bounded`
  - `validation.mape_threshold`, `validation.range_tolerance_ratio`, `validation.performance_p95_ms_threshold`, and `validation.od_pairs`
- Place raw GTFS files in `backend/offline/data/gtfs/<city_id>/`.
- Build artifacts with explicit city:
  - `make -C backend/offline ingest CITY=<city_id>`
  - `make -C backend/offline build-graph CITY=<city_id>`
  - `make -C backend/offline build-grid CITY=<city_id>`
  - `make -C backend/offline validate-data CITY=<city_id>`
  - `make -C backend/offline export CITY=<city_id>`
- Confirm artifacts exist in `backend/offline/data/artifacts/<city_id>/`.
- Smoke-check API using city-qualified requests:
  - `POST /multi_isochrones` with `"city":"<city_id>"`
  - `POST /multi_path` with `"city":"<city_id>"`
  - `GET /geocode?city=<city_id>&q=...`

## Skills

### Available skills

- add-transit-city: Use when adding a new city to the transit app backend/offline pipeline. Covers finding source data, deciding between direct GTFS and custom source conversion, registering source adapters and city plugins, choosing a narrow bbox, building v2 artifacts, writing OD validation checks, running manual QA, and avoiding common pitfalls such as night buses, replacement buses, and incomplete rail coverage. (file: /Users/antoineogier/Documents/Perso/Code/transportation/skills/add-transit-city/SKILL.md)

### How to use skills

- If a user request clearly matches a skill description, use that skill for the turn.
- Read only the relevant `SKILL.md` and any directly needed referenced files.
- Resolve relative paths mentioned by a skill from the skill directory first.
