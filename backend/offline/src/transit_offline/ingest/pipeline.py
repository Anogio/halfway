from __future__ import annotations

import json

from transit_offline.cities import get_city_plugin
from transit_offline.common.config import AppConfig, ensure_dirs, load_config
from transit_offline.ingest.gtfs import (
    EXTENDED_BUS_ROUTE_TYPES,
    load_feed_info,
    load_nodes,
    load_routes,
    load_trips,
    load_weekday_service_ids,
    require_files,
    scan_stop_times,
    write_csv,
)


def run_ingest(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    ensure_dirs(cfg)

    gtfs_dir = cfg.paths.gtfs_input
    require_files(gtfs_dir)

    include_route_types = set(cfg.settings.modes.include_route_types)
    if cfg.settings.modes.include_all_bus:
        include_route_types |= EXTENDED_BUS_ROUTE_TYPES

    plugin = get_city_plugin(cfg.city_id)
    routes, route_to_type, mode_counter = load_routes(gtfs_dir, include_route_types, plugin=plugin)
    weekday_service_ids, calendar_stats = load_weekday_service_ids(
        gtfs_dir,
        weekdays_only=cfg.settings.service.weekdays_only,
        exclude_holidays=cfg.settings.service.exclude_holidays,
    )
    trips, direction_counter = load_trips(gtfs_dir, routes, weekday_service_ids)
    nodes, location_counter = load_nodes(gtfs_dir, plugin=plugin)

    node_ids = {row["stop_id"] for row in nodes}
    stop_times_stats = scan_stop_times(gtfs_dir, trips, node_ids)

    interim = cfg.paths.offline_interim_dir
    write_csv(
        interim / "routes_selected.csv",
        (
            {"route_id": rid, "route_type": route_to_type[rid]}
            for rid in sorted(routes)
        ),
        ["route_id", "route_type"],
    )
    write_csv(
        interim / "trips_weekday.csv",
        (
            {
                "trip_id": trip_id,
                "route_id": record.route_id,
                "direction_id": record.direction_id,
                "service_id": record.service_id,
            }
            for trip_id, record in sorted(trips.items())
        ),
        ["trip_id", "route_id", "direction_id", "service_id"],
    )
    write_csv(
        interim / "nodes.csv",
        nodes,
        ["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type"],
    )

    report = {
        "city": cfg.city_id,
        "feed_info": load_feed_info(gtfs_dir),
        "counts": {
            "routes_selected": len(routes),
            "weekday_service_ids": len(weekday_service_ids),
            "trips_selected": len(trips),
            "nodes_selected": len(nodes),
            **stop_times_stats,
        },
        "distributions": {
            "route_type_all": dict(mode_counter),
            "trip_direction_selected": dict(direction_counter),
            "stop_location_type_all": dict(location_counter),
        },
        "calendar_stats": calendar_stats,
    }

    report_path = interim / "ingest_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    return report
