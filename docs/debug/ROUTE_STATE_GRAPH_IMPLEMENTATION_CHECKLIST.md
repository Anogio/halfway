# Route-State Graph Implementation Checklist

This is the execution checklist for implementing the route-state graph described
in:

- `docs/debug/ROUTE_STATE_GRAPH_PLAN.md`

The goals are:

- keep Dijkstra unchanged
- move wait to boarding edges
- make transfer costs explicit in graph structure
- make path payload reconstruction production-grade rather than debug-grade

## Phase 0: Lock The Scope

- [ ] Keep seeds and destination candidates on physical nodes only
- [ ] Keep grid links on physical nodes only
- [ ] Use median-based wait for the first implementation
- [ ] Use onboard node key `(physical_node_idx, route_id, direction_id)`
- [ ] Ship as new artifact version (`v2`)

## Phase 1: Define Artifact Schema

Files:

- `backend/offline/src/transit_offline/graph/pipeline.py`
- `backend/src/transit_backend/core/artifacts.py`

Tasks:

- [ ] Add `node_kind` to exported node metadata
- [ ] Add `physical_node_idx` for onboard nodes
- [ ] Add `route_id` for onboard nodes
- [ ] Add `direction_id` for onboard nodes
- [ ] Preserve `stop_id`, `stop_name`, `lat`, `lon` on both node kinds
- [ ] Write new artifact names:
  - [ ] `graph_v2_weekday.json`
  - [ ] `nodes_v2.csv`
- [ ] Keep `v1` generation untouched until `v2` is validated

## Phase 2: Build Physical And Onboard Node Tables

Files:

- `backend/offline/src/transit_offline/graph/pipeline.py`

Tasks:

- [ ] Load current physical nodes from interim `nodes.csv`
- [ ] Build a stable physical node table
- [ ] Scan selected stop-times usage and create onboard nodes for each:
  - [ ] `(physical_node_idx, route_id, direction_id)`
- [ ] Build lookup maps:
  - [ ] `physical -> onboard nodes`
  - [ ] `(physical, route, direction) -> onboard idx`
  - [ ] `onboard idx -> physical idx`

## Phase 3: Rebuild Edge Semantics

Files:

- `backend/offline/src/transit_offline/graph/pipeline.py`

Tasks:

- [ ] Remove physical-layer ride edges from `v2`
- [ ] Build onboarding wait edges:
  - [ ] `physical -> onboard`
- [ ] Build onboard continuation edges:
  - [ ] `onboard -> onboard`
- [ ] Build alight edges:
  - [ ] `onboard -> physical`
- [ ] Keep physical transfer edges:
  - [ ] `pathways.txt`
  - [ ] `transfers.txt`
  - [ ] synthetic hub transfers
  - [ ] spatial fallback transfers
- [ ] Preserve transfer floor logic

## Phase 4: Wait And Runtime Accounting

Files:

- `backend/offline/src/transit_offline/graph/pipeline.py`

Tasks:

- [ ] Keep `_compute_waits()` as median headway / 2 for initial `v2`
- [ ] Stop amortizing wait over ride edges in `v2`
- [ ] Put wait only on boarding edges
- [ ] Keep onboard ride edges as pure in-vehicle runtime
- [ ] Keep current mean inter-stop runtime aggregation initially

## Phase 5: Runtime Loader Support

Files:

- `backend/src/transit_backend/core/artifacts.py`

Tasks:

- [ ] Load `node_kind`
- [ ] Load `physical_node_idx`
- [ ] Load onboard `route_id`
- [ ] Load onboard `direction_id`
- [ ] Add helper accessors or derived maps for runtime use
- [ ] Keep runtime capable of loading `v1` during migration if needed

## Phase 6: Keep Seed / Grid Semantics Stable

Files:

- `backend/src/transit_backend/core/spatial.py`
- `backend/src/transit_backend/core/pathing.py`
- `backend/src/transit_backend/core/cells.py`
- `backend/offline/src/transit_offline/grid/pipeline.py`

Tasks:

- [ ] Ensure origin seeding only targets physical nodes
- [ ] Ensure runtime destination candidates only target physical nodes
- [ ] Ensure precomputed grid links only target physical nodes
- [ ] Add assertions/tests preventing onboard nodes from leaking into access links

## Phase 7: Payload Reconstruction Rewrite

Files:

- `backend/src/transit_backend/core/path_payloads.py`
- `backend/src/transit_backend/core/pathing.py`

Tasks:

- [ ] Introduce an internal path-event normalization step
- [ ] Normalize raw graph traversal into logical events:
  - [ ] `walk_origin`
  - [ ] `board`
  - [ ] `ride`
  - [ ] `alight`
  - [ ] `transfer`
  - [ ] `walk_destination`
- [ ] Collapse internal bookkeeping transitions
- [ ] Group consecutive same-route onboard edges into one ride segment
- [ ] Represent transfer as:
  - [ ] alight
  - [ ] physical transfer movement
  - [ ] next boarding
- [ ] Hide onboard/physical internal node churn from API payloads

## Phase 8: Improve Path Summary Semantics

Files:

- `backend/src/transit_backend/core/path_payloads.py`

Tasks:

- [ ] Split total into:
  - [ ] `origin_walk_s`
  - [ ] `boarding_wait_s`
  - [ ] `ride_runtime_s`
  - [ ] `transfer_s`
  - [ ] `destination_walk_s`
  - [ ] `total_time_s`
- [ ] Keep existing summary fields temporarily if frontend compatibility needs them
- [ ] Document which fields are compatibility vs canonical

## Phase 9: Tests For Structural Correctness

Files:

- `backend/offline/tests/test_graph.py`
- `backend/tests/test_routing_paths.py`
- `backend/tests/test_path_payloads.py`

Tasks:

- [ ] Add graph tests asserting:
  - [ ] physical nodes exist
  - [ ] onboard nodes exist
  - [ ] ride edges are onboard-only
  - [ ] boarding edges are physical-to-onboard
  - [ ] alight edges are onboard-to-physical
  - [ ] transfer edges are physical-to-physical
- [ ] Add routing tests asserting:
  - [ ] first boarding pays wait once
  - [ ] same-line continuation does not repay wait
  - [ ] changing route pays transfer movement + new wait
- [ ] Add payload tests asserting:
  - [ ] grouped ride legs
  - [ ] explicit transfer segments
  - [ ] no internal bookkeeping leakage

## Phase 10: OD Regression Set

Files:

- add under `docs/debug/` or `backend/offline/tests/fixtures/` if needed

Tasks:

- [ ] Curate Paris OD checks:
  - [ ] no-transfer metro
  - [ ] metro transfer in big hub
  - [ ] bus + metro
  - [ ] Gare de l'Est 5 -> 4
- [ ] Curate London OD checks:
  - [ ] Tube only
  - [ ] bus only
  - [ ] mixed bus + Tube
  - [ ] major interchange
- [ ] Record expected qualitative outcomes, not just seconds

## Phase 11: Dual-Run Comparison Tooling

Files:

- likely new script under `backend/scripts/` or `backend/offline/scripts/`

Tasks:

- [ ] Add a script that runs the same OD against `v1` and `v2`
- [ ] Compare:
  - [ ] total time
  - [ ] ride runtime
  - [ ] transfer time
  - [ ] boarding wait
  - [ ] transfer count
  - [ ] chosen lines
- [ ] Emit machine-readable diff plus compact human summary

## Phase 12: Calibration Pass

Files:

- `backend/offline/src/transit_offline/graph/pipeline.py`
- maybe config if new knobs are needed

Tasks:

- [ ] Calibrate boarding wait caps after `v2` is structurally correct
- [ ] Revisit transfer floor under `v2`
- [ ] Revisit walk circuity separately from transit semantics
- [ ] Defer time-bucketed wait unless clearly needed

## Phase 13: Cutover

Files:

- runtime artifact loading/config where version is selected

Tasks:

- [ ] Switch runtime to prefer `v2`
- [ ] Keep `v1` available briefly for rollback
- [ ] Re-run validation for Paris and London
- [ ] Re-run curated OD comparisons
- [ ] Remove dead `v1`-specific assumptions after stabilization

## Important Non-Goals For First Iteration

- [ ] Do not make Dijkstra route-aware
- [ ] Do not add time-of-day routing
- [ ] Do not synthesize extra platform topology beyond current GTFS/hub structure unless blocked
- [ ] Do not mix major walk-model changes into the first structural migration

## Suggested Implementation Order

1. Artifact schema
2. Offline graph build
3. Runtime loader
4. Payload normalization
5. Structural tests
6. OD regression set
7. Dual-run comparison
8. Calibration
9. Cutover
