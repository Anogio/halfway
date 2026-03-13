# Offline Precomputation

Builds graph and grid artifacts from GTFS files.

## Requirements
- Python 3.13+

## Data layout
- GTFS input: `backend/offline/data/gtfs/<city_id>/`
- Interim outputs: `backend/offline/data/interim/<city_id>/`
- Artifacts: `backend/offline/data/artifacts/<city_id>/`

Primary knobs live in `backend/config/settings.toml`.
Shared knobs are global; city-specific values are under `cities.<city_id>`.
Each city artifact folder may contain an ignored `old/` subdirectory where prior
generated outputs are archived before replacement.

## Commands
All commands require explicit city id:

```bash
make setup
make lint
make test
make prepare-data CITY=paris
make ingest CITY=paris
make build-graph CITY=paris
make build-grid CITY=paris
make validate-data CITY=paris
make export CITY=paris
make build-all CITY=paris
make build-all-from-sources CITY=paris
```

Artifact generation commands archive any existing files for their artifact
family into `backend/offline/data/artifacts/<city_id>/old/` before writing new
ones. That includes previous versions such as `v0` or prior `v1` outputs.

## Source Adapter Scaffold

`prepare-data` is the source-preparation entrypoint. It runs before `ingest` and
writes a `prepare_report.json` in `backend/offline/data/interim/<city_id>/`.

The architecture intentionally keeps a thin reusable core and city-specific code:

- Shared core (`src/transit_offline/sources/*`):
  - adapter contract (`SourceAdapter`)
  - shared report model (`PrepareReport`)
  - normalized feed models (`models.py`)
  - generic GTFS writer (`gtfs_writer.py`)
  - generic validators (`validators.py`)
  - source pipeline orchestration (`pipeline.py`)
- City-specific (`src/transit_offline/sources/<city_id>/*`):
  - source readers/parsers
  - mapping rules from source format to normalized records
  - city-only heuristics and sanity checks

Separate from source adapters, city policy hooks now live under
`src/transit_offline/cities/<city_id>/*` and are used by shared ingest/graph
stages for:

- route inclusion/exclusion
- stop-name normalization
- route label formatting

There is no fallback city plugin or source adapter. A configured city must be
registered explicitly in both registries or the pipeline fails fast.

### London Boundary

For London, all TfL/UK format-specific logic belongs under:

- `src/transit_offline/sources/london/adapter.py`
- `src/transit_offline/sources/london/validators.py`

The London adapter generates GTFS and emits identity warnings (for example,
non-UK publisher URL or stops outside the configured London bbox).

London display-policy logic belongs under:

- `src/transit_offline/cities/london/plugin.py`

Current conversion behavior:

- consumes London raw files under `backend/offline/data/raw/london/`
- generates required GTFS files into `backend/offline/data/gtfs/london/`
- uses live bus static files and station topology GTFS
- parses Journey Planner XML timetables from `journey/live_unpacked/*.xml`:
  - full non-bus set (tube/rail/tram/ferry/cable-car)
  - full bus set from `BUSES_PART_*`
  - excludes `REPLACEMENT_BUSES_*` by policy
- enriches journey-platform stops with station parent mapping from
  station detailed metadata, enabling pathway transfer edges in graph build
- graph build also synthesizes hub transfer edges when explicit GTFS transfers
  are sparse, using shared parent-hub relationships and calibrated penalties
- graph build floors all pathway/transfer edges to a minimum `120s` transfer
  cost so unrealistically short source transfer times do not create implausibly
  cheap interchanges
- London route labels are simplified city-specifically:
  - tube/rail lines prefer short names (for example `Jubilee`, `Northern`)
  - bus services are rendered as `<line> bus` (for example `109 bus`)

### Extraction Rule (Pragmatic)

Default new code to `sources/london/*`. Only move code into shared
`sources/*` once it is clearly format-agnostic or reused by at least one other
city adapter.

## Routing Safeguards (Generic)

These safeguards are global and apply to all configured cities:

- Path search seeds are rail-aware: if in-radius seeds are bus-only, nearest
  rail-like stops are force-included up to the seed cap.
- Rail-like status is derived from GTFS `route_type` usage per stop during
  graph build and persisted in `nodes_<version>.csv`; routing no longer infers
  rail stops from city-specific stop ID prefixes.
- Grid precomputation uses the same access-candidate selector and first-mile
  policy as runtime routing. `build-grid` now follows
  `search.first_mile_radius_m`, `search.first_mile_fallback_k`, and
  `runtime.max_seed_nodes`; the older grid-only candidate radius/cap settings
  are retained only for compatibility/reporting.
- Grid `in_scope` is stricter than `linked`: a cell is marked in-scope only if
  it has at least one in-radius access candidate before global fallback.
  Fallback-only fringe cells may still keep links for parity/debugging, but are
  excluded from reachability-denominator metrics.
- Rail forcing uses a prebuilt exact nearest-neighbor index over the rail-like
  node subset, so filtered fallback lookups do not scan the full node set.
- Transfer/pathway edges are floored to `120s` during graph build to avoid
  unrealistic ultra-cheap interchanges when source feeds omit or understate
  transfer times.
- Ride-edge waits are amortized over median trip segment counts (per route and
  direction) to avoid over-penalizing long multi-stop rides.
