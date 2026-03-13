# Route Quality Runbook

## Goal
Debug questionable travel times or suspicious paths with repeatable steps.

## 1) Verify artifact baseline
- Inspect [baseline metadata](/Users/antoineogier/Documents/Perso/Code/transportation/docs/debug/baseline-2026-03-09/metadata.json).
- Compare current artifact hashes against:
  - [artifact hashes](/Users/antoineogier/Documents/Perso/Code/transportation/docs/debug/baseline-2026-03-09/artifact_hashes.sha256)

## 2) Validate offline build quality
- Run `make -C backend/offline validate-data CITY=<city_id>`.
- Check `validation_<version>.json` for:
  - `mape`
  - OD pairs out-of-range
  - reachability ratio
  - p95 performance

## 3) Inspect a suspicious path
- Call `/multi_path` with one origin in `origins` and explicit `city`.
- Validate:
  - transfer count is plausible
  - no impossible jumps between distant stops without ride edges
  - line labels and stop sequence look realistic

## 4) Compare with heatmap and isochrones
- For the same origin, compare `/heatmap` cell values and `/multi_isochrones` bucket.
- If path time is much lower than local cell times near destination:
  - inspect transfer/fallback edges near destination
  - verify first/last-mile seed radius and cap in config

## 5) Common root causes
- Wrong config values:
  - `weights.walk_speed_mps`
  - `search.first_mile_radius_m`
  - `search.transfer_fallback_radius_m`
  - `weights.transfer_penalty_s`
  - `runtime.max_time_s`
- GTFS scope mismatch:
  - route types filtered too aggressively
  - service filtering too restrictive
- Artifact mismatch:
  - backend loading stale artifacts after offline rebuild
