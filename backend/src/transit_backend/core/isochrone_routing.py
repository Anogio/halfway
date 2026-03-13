from __future__ import annotations

from transit_backend.core.artifacts import RuntimeData
from transit_backend.core.cells import cells_from_cell_times, total_in_scope_cells_for_walk_limit
from transit_backend.core.heatmap import compute_origin_cell_times
from transit_backend.core.isochrones import GridTopology, build_isochrone_feature_collection
from transit_backend.core.spatial import SpatialIndex


def compute_isochrones(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    topology: GridTopology,
    origin_lat: float,
    origin_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    compute_max_time_s: int,
    render_max_time_s: int,
    bucket_size_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    origin_grid = compute_origin_cell_times(
        runtime,
        spatial,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        first_mile_radius_m=first_mile_radius_m,
        first_mile_fallback_k=first_mile_fallback_k,
        max_seed_nodes=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
        max_time_s=compute_max_time_s,
    )
    cells = cells_from_cell_times(runtime, origin_grid["cell_times"])
    render_cells = [cell for cell in cells if int(cell["time_s"]) <= render_max_time_s]

    feature_collection = build_isochrone_feature_collection(
        render_cells,
        topology=topology,
        bucket_size_s=bucket_size_s,
        max_time_s=render_max_time_s,
    )
    response = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "profile": runtime.profile,
        "feature_collection": feature_collection,
    }
    if include_stats:
        total_scoped_cells = total_in_scope_cells_for_walk_limit(
            runtime,
            max_walk_s=int(round(first_mile_radius_m / walk_speed_mps)),
        )
        response["stats"] = {
            "seed_count": int(origin_grid["seed_count"]),
            "reachable_cells_compute_horizon": len(cells),
            "reachable_cells_render_horizon": len(render_cells),
            "reachable_cells": len(render_cells),
            "total_linked_cells": total_scoped_cells,
            "compute_max_time_s": int(compute_max_time_s),
            "render_max_time_s": int(render_max_time_s),
            "bucket_size_s": bucket_size_s,
            "bucket_count": len(feature_collection["features"]),
        }
    return response


def compute_multi_isochrones(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    topology: GridTopology,
    origins: list[dict[str, object]],
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
    bucket_size_s: int,
    cached_origin_cells: dict[str, dict[int, int]] | None = None,
    cached_seed_counts: dict[str, int] | None = None,
    include_stats: bool = True,
) -> dict[str, object]:
    merged: dict[int, int] | None = None
    seed_count_by_origin: dict[str, int] | None = {} if include_stats else None

    for origin in origins:
        origin_id = str(origin["id"])
        origin_lat = float(origin["lat"])
        origin_lon = float(origin["lon"])

        cached_cells = (cached_origin_cells or {}).get(origin_id)
        cached_seed_count = (cached_seed_counts or {}).get(origin_id)
        if cached_cells is None or (include_stats and cached_seed_count is None):
            origin_grid = compute_origin_cell_times(
                runtime,
                spatial,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                first_mile_radius_m=first_mile_radius_m,
                first_mile_fallback_k=first_mile_fallback_k,
                max_seed_nodes=max_seed_nodes,
                walk_speed_mps=walk_speed_mps,
                max_time_s=max_time_s,
            )
            cell_times = dict(origin_grid["cell_times"])
            seed_count = int(origin_grid["seed_count"])
        else:
            cell_times = dict(cached_cells)
            seed_count = int(cached_seed_count) if cached_seed_count is not None else 0

        if seed_count_by_origin is not None:
            seed_count_by_origin[origin_id] = seed_count

        if merged is None:
            merged = cell_times
            continue

        reconciled: dict[int, int] = {}
        for cell_id, current_time in merged.items():
            next_time = cell_times.get(cell_id)
            if next_time is None:
                continue
            reconciled[cell_id] = max(current_time, int(next_time))
        merged = reconciled

    if merged is None:
        merged = {}

    cells = cells_from_cell_times(runtime, merged)
    render_cells = [cell for cell in cells if int(cell["time_s"]) <= max_time_s]
    feature_collection = build_isochrone_feature_collection(
        render_cells,
        topology=topology,
        bucket_size_s=bucket_size_s,
        max_time_s=max_time_s,
    )
    response = {
        "origins": [
            {"id": str(origin["id"]), "lat": float(origin["lat"]), "lon": float(origin["lon"])}
            for origin in origins
        ],
        "profile": runtime.profile,
        "feature_collection": feature_collection,
    }
    if include_stats:
        total_scoped_cells = total_in_scope_cells_for_walk_limit(
            runtime,
            max_walk_s=int(round(first_mile_radius_m / walk_speed_mps)),
        )
        response["stats"] = {
            "origin_count": len(origins),
            "seed_count": sum((seed_count_by_origin or {}).values()),
            "origin_seed_counts": seed_count_by_origin or {},
            "reachable_cells_compute_horizon": len(cells),
            "reachable_cells_render_horizon": len(render_cells),
            "reachable_cells": len(render_cells),
            "total_linked_cells": total_scoped_cells,
            "compute_max_time_s": int(max_time_s),
            "render_max_time_s": int(max_time_s),
            "bucket_size_s": bucket_size_s,
            "bucket_count": len(feature_collection["features"]),
        }
    return response
