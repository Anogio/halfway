# Source Preparation Architecture

This folder hosts the source-preparation scaffold used by `prepare-data`.

## What belongs in `sources/*`

Only reusable, city-agnostic building blocks:

- adapter contract and report model (`base.py`)
- orchestration (`pipeline.py`)
- normalized intermediate dataclasses (`models.py`)
- generic GTFS writer (`gtfs_writer.py`)
- generic validators (`validators.py`)

## What belongs in `sources/london/*`

London-specific logic only:

- readers/parsers for London data sources
- field mappings and mode mappings for London
- London heuristics and guardrails
- London-only data quality checks

## Practical rule

When in doubt, place logic in `sources/london/*` first.

## City Policy Plugins

Source adapters are not the place for every city-specific behavior.

- `sources/<city_id>/*` is for raw input parsing/conversion only
- `cities/<city_id>/*` is for shared-pipeline policy such as:
  - route inclusion/exclusion
  - stop-name normalization
  - route label formatting

There is no fallback adapter. Every configured city must be registered
explicitly.
Promote code into `sources/*` only when it is demonstrably reusable.

## Current London status

- `prepare-data --city london` now generates GTFS files from London raw sources.
- It currently uses:
  - live bus stop + bus sequence feeds
  - station topology GTFS files
  - Journey Planner XML timetables (`journey/live_unpacked/*.xml`) for:
    - non-bus modes (tube, rail, tram, ferry, cable-car)
    - bus modes from all `BUSES_PART_*` feeds

Current known limitations:

- service-day handling is coarse-grained (weekday/weekend masks only)
- replacement bus feeds (`REPLACEMENT_BUSES_*`) are intentionally excluded
- some bus stops are still dropped if no lat/lon exists in StopPoint lookup
