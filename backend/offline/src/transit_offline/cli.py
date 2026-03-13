from __future__ import annotations

import argparse
import json

from transit_offline.export.pipeline import run_export
from transit_offline.graph.pipeline import run_build_graph
from transit_offline.grid.pipeline import run_build_grid
from transit_offline.ingest.pipeline import run_ingest
from transit_offline.sources.pipeline import run_prepare_data
from transit_offline.validation.pipeline import run_validate


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline transit pipeline")
    parser.add_argument(
        "command",
        choices=["prepare-data", "ingest", "build-graph", "build-grid", "validate", "export"],
    )
    parser.add_argument("--city", required=True, help="City id configured in backend/config/settings.toml")
    args = parser.parse_args()

    if args.command == "prepare-data":
        report = run_prepare_data(city_id=args.city)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "ingest":
        report = run_ingest(city_id=args.city)
        print(json.dumps(report["counts"], indent=2, sort_keys=True))
        return
    if args.command == "build-graph":
        report = run_build_graph(city_id=args.city)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "export":
        report = run_export(city_id=args.city)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "build-grid":
        report = run_build_grid(city_id=args.city)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "validate":
        report = run_validate(city_id=args.city)
        print(json.dumps(report, indent=2, sort_keys=True))
        return


if __name__ == "__main__":
    main()
