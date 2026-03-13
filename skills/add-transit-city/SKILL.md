---
name: add-transit-city
description: Use when adding a new city to the transit app backend/offline pipeline. Covers finding source data, deciding between direct GTFS and custom source conversion, registering source adapters and city plugins, choosing a narrow bbox, building v2 artifacts, writing OD validation checks, running manual QA, and avoiding common pitfalls such as night buses, replacement buses, and incomplete rail coverage.
---

# Add Transit City

Use this skill when onboarding a new city into the app.

The goal is not just to make the pipeline run. The goal is to ship a city whose:
- source data is understood
- artifacts are buildable and reproducible
- bbox is narrow enough for acceptable runtime
- OD checks are defensible
- path quality is manually reviewed
- city-specific filtering and naming rules live in city-specific code, not shared branches

## Outcome

A correct city onboarding usually means all of the following exist:
- `backend/config/settings.toml` entry under `cities.<city_id>`
- source adapter registration in `backend/offline/src/transit_offline/sources/registry.py`
- city plugin registration in `backend/offline/src/transit_offline/cities/registry.py`
- GTFS data under `backend/offline/data/gtfs/<city_id>/`
- raw source data under `backend/offline/data/raw/<city_id>/` if conversion is needed
- successful `ingest`, `build-graph`, `build-grid`, `validate-data`, `export`
- manual QA on real OD pairs

## 1. Start With The Data

First determine what data you actually have.

Preferred order:
1. good-quality GTFS with stops, stop_times, transfers/pathways, calendars
2. multiple official feeds that can be converted to GTFS
3. APIs / XML / PDFs / site-specific data that require heavy synthesis

Questions to answer before writing code:
- Is this full-network transit or only one operator/mode?
- Are rail, metro, tram, ferry, and bus all present?
- Are transfers/pathways included or missing?
- Is schedule data static, frequency-based, or API-only?
- Are night/replacement/event routes mixed into the daytime feed?
- Are stop coordinates and parent-station relationships usable?

Do not assume “official feed” means “complete feed”.
London is the cautionary example:
- the current TfL-derived dataset covers Tube, bus, DLR, tram, cable car, etc.
- but it does not currently include National Rail-style service to corridors like `Richmond -> Waterloo`
- the router can only use what exists in the feed

## 2. Decide: Direct GTFS Or Source Adapter

If the city already has GTFS that is good enough, use the direct adapter:
- register `DirectGtfsSourceAdapter()` in `backend/offline/src/transit_offline/sources/registry.py`

If the city needs conversion:
- create `backend/offline/src/transit_offline/sources/<city_id>/adapter.py`
- optionally add `validators.py`
- keep raw-format parsing there

Boundary rules:
- `sources/<city_id>/*` is for raw-source parsing and GTFS conversion only
- `cities/<city_id>/*` is for city policy in shared stages:
  - route inclusion/exclusion
  - stop-name normalization
  - route label formatting

Do not add `if city == ...` branches in shared ingest/graph code.

## 3. Add The City Config First

Add the city to `backend/config/settings.toml`.

Required fields:
- `label`
- `artifact_version`
- `paths.gtfs_input`
- `scope.use_bbox`, `scope.bbox`, `scope.default_view`
- `geocoding.country_codes`, `geocoding.viewbox`, `geocoding.bounded`
- `validation.mape_threshold`, `validation.range_tolerance_ratio`, `validation.performance_p95_ms_threshold`
- `validation.od_pairs`

Use `artifact_version = "v2"` for new cities.

Keep the bbox narrow.
Do not use a huge administrative region just because the feed technically covers it.
A wide bbox will:
- blow up grid size
- slow `/multi_isochrones`
- dilute reachability metrics
- increase manual QA noise on fringe cells

Practical rule:
- include the real urban/service area you want to support in the app
- cut obvious rural/exurban tails unless they are core to the product

## 4. Register The City In Both Registries

There is no fallback plugin or source adapter.
A configured city must be registered explicitly.

Files:
- `backend/offline/src/transit_offline/sources/registry.py`
- `backend/offline/src/transit_offline/cities/registry.py`

Typical pattern:
- source registry points to either direct GTFS or the new adapter
- city registry points to a new `CityPlugin` implementation

## 5. Build The City Plugin Early

Create `backend/offline/src/transit_offline/cities/<city_id>/plugin.py`.

Use it for:
- route filtering
- stop-name normalization
- route label formatting

This is where you should place city-specific cleanup such as:
- Paris: exclude `Noctilien` in daytime weekday profile
- London: exclude night buses (`N*`) and replacement buses (`UL*`)
- London: shorten route labels to `Jubilee`, `Northern`, `109 bus`
- London: remove suffixes like `Underground Station`

Do not postpone route filtering. If a route should not participate in routing, exclude it during ingest.
That keeps it out of:
- `routes_selected.csv`
- `trips_weekday.csv`
- graph build
- manual QA

## 6. Put Data In The Right Place

Data layout:
- raw source files: `backend/offline/data/raw/<city_id>/`
- GTFS inputs: `backend/offline/data/gtfs/<city_id>/`
- interim: `backend/offline/data/interim/<city_id>/`
- artifacts: `backend/offline/data/artifacts/<city_id>/`

Raw source data and large GTFS inputs should not be versioned.
The raw folder is intentionally treated like other large source inputs.

## 7. Build Incrementally

Use explicit city-qualified commands.

Direct GTFS city:
```bash
make -C backend/offline ingest CITY=<city_id>
make -C backend/offline build-graph CITY=<city_id>
make -C backend/offline build-grid CITY=<city_id>
make -C backend/offline validate-data CITY=<city_id>
make -C backend/offline export CITY=<city_id>
```

Converted-source city:
```bash
make -C backend/offline prepare-data CITY=<city_id>
make -C backend/offline ingest CITY=<city_id>
make -C backend/offline build-graph CITY=<city_id>
make -C backend/offline build-grid CITY=<city_id>
make -C backend/offline validate-data CITY=<city_id>
make -C backend/offline export CITY=<city_id>
```

Do not jump straight to `build-all` until the city is stable.
Inspect each stage.

## 8. Check The Right Interim Files

Before trusting the graph, inspect:
- `backend/offline/data/interim/<city_id>/routes_selected.csv`
- `backend/offline/data/interim/<city_id>/trips_weekday.csv`
- `backend/offline/data/interim/<city_id>/nodes.csv` or selected node outputs
- `prepare_report.json` and `ingest_report.json`

Questions to answer:
- Did route counts drop the way you expected after filtering?
- Are expected rail routes present?
- Are important hubs/stations present?
- Are unexpected night/replacement routes still selected?
- Are route types plausible?

Do this before path QA.
A bad path is often just missing source coverage.

## 9. Verify Modal Coverage Explicitly

Do not rely on high-level feed marketing.
Query the selected routes and stop_times.

Examples of useful checks:
- all selected `route_type` counts
- which routes serve a major station
- whether a key corridor is present at all
- whether a route is present in GTFS but filtered out by policy

This caught a real London issue:
- `Richmond -> Waterloo` routed poorly
- root cause was not graph structure
- the selected feed had no National Rail-style service for that corridor
- Richmond was only served by District + bus in selected trips

That kind of check should happen before trying to “fix routing”.

## 10. Write OD Validation Pairs Carefully

Put OD pairs in `backend/config/settings.toml`.

Choose pairs that test:
- central radial trip
- suburb to center
- short metro/tube trip
- major interchange
- mixed bus + rail
- one or two edge-of-coverage trips

Do not overfit the expected ranges.
Use broad but meaningful intervals.
The point is to catch broken data, not to force an exact schedule match.

Good validation catches:
- missing major mode coverage
- obviously broken travel times
- pathological runtime regressions

Bad validation:
- too few pairs
- only simple central trips
- ranges so wide they never fail

## 11. Run Manual QA After Validation

Validation passing is not enough.
Manually inspect real paths.

Minimum manual QA set:
- 15 to 20 OD pairs per city
- include:
  - no-transfer rail/metro
  - one clean transfer
  - major hub interchange
  - bus-only trip
  - bus + rail feeder trip
  - suburb to center
  - center to suburb

For each route, check:
- does the mode sequence make sense?
- are line names readable?
- are there obvious missing transfers?
- are first/last-mile walks excessive?
- are replacement/night routes appearing incorrectly?
- is the path only “technically optimal” because a whole mode is missing?

## 12. Common Pitfalls

### Night buses in daytime profiles
Exclude them in the city plugin.
Examples:
- Paris `Noctilien`
- London `N*`

### Replacement buses
Exclude them in the city plugin.
Example:
- London `UL*`

### Incomplete rail coverage
A city can look good in the center and still be missing core rail corridors.
Check actual selected trips at important stations.

### Overly wide bbox
A huge bbox will make the city look worse and run slower.
Start narrow.
Expand only if product needs it.

### Believing route labels are harmless
Bad labels hurt QA because they hide what the router actually chose.
Clean them early.

### Confusing source conversion with city policy
Keep conversion in `sources/<city_id>` and policy in `cities/<city_id>`.

### Trying to fix missing data with weights
Do not compensate for missing rail or bad mode coverage by tweaking penalties.
Fix source coverage first.

### Over-trusting explicit transfers
Some feeds understate transfer times badly.
The graph currently floors explicit transfers to a minimum `120s`.
Keep that in mind during QA.

### Misreading same-stop changes in payloads
In the `v2` graph, same-stop route changes can be priced via a new boarding wait even when there is no separate transfer-movement edge. The cost can be real even if `transfer_s` stays zero.

## 13. Narrow BBox Heuristic

When picking the bbox:
- center it on the city people actually use
- include the dense commuter belt that matters to the app
- exclude distant tails that mostly add grid cells and little value

A good bbox is usually:
- much smaller than the feed’s formal area
- large enough to cover the practical everyday network

After choosing it:
- rebuild grid
- re-run validation
- benchmark `/multi_isochrones`

If performance is poor, revisit bbox before changing routing code.

## 14. API Smoke Checks

After export, smoke-check the city through the API:
- `POST /multi_isochrones` with `"city":"<city_id>"`
- `POST /multi_path` with `"city":"<city_id>"`
- `GET /geocode?city=<city_id>&q=...`

Do at least one live path request that should use:
- rail only
- bus only
- mixed modes

## 15. Done Criteria

A city is not done when the build succeeds.
A city is done when:
- expected source modes are actually present in selected trips
- policy filters remove the routes that should not appear
- bbox is narrow and runtime is acceptable
- validation passes
- manual OD checks look sane
- no city-specific branches were added to shared code

## File Checklist

Always expect to touch some subset of:
- `backend/config/settings.toml`
- `backend/offline/src/transit_offline/sources/registry.py`
- `backend/offline/src/transit_offline/cities/registry.py`
- `backend/offline/src/transit_offline/sources/<city_id>/adapter.py`
- `backend/offline/src/transit_offline/sources/<city_id>/validators.py`
- `backend/offline/src/transit_offline/cities/<city_id>/plugin.py`
- `backend/offline/data/gtfs/<city_id>/...`
- `backend/offline/data/raw/<city_id>/...`

## Short Workflow

1. Assess source completeness and modal coverage.
2. Decide direct GTFS vs source adapter.
3. Add narrow config and bbox.
4. Register source adapter and city plugin.
5. Add route filtering and naming cleanup in the city plugin.
6. Build incrementally and inspect interim files.
7. Verify major corridors and stations exist in selected trips.
8. Add OD checks.
9. Rebuild full artifacts.
10. Run manual QA and fix data-policy issues before tuning weights.
