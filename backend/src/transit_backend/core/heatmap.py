from __future__ import annotations

from typing import Any

from transit_backend.core.artifacts import RuntimeData
from transit_backend.core.cells import cell_times_from_dist
from transit_backend.core.spatial import SpatialIndex, dijkstra, resolve_seeds

def compute_origin_cell_times(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    origin_lat: float,
    origin_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
) -> dict[str, Any]:
    seeds = resolve_seeds(
        runtime,
        spatial,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        first_mile_radius_m=first_mile_radius_m,
        first_mile_fallback_k=first_mile_fallback_k,
        max_seed_nodes=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
    )
    dist = dijkstra(runtime, seeds, max_time_s=max_time_s)
    return {
        "seed_count": len(seeds),
        "cell_times": cell_times_from_dist(runtime, dist, max_time_s=max_time_s),
    }
