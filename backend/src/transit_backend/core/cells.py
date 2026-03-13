from __future__ import annotations

from transit_backend.core.artifacts import RuntimeData
from transit_backend.core.spatial import SpatialIndex, dijkstra, resolve_seeds
from transit_shared.routing import INF


def total_in_scope_cells(runtime: RuntimeData) -> int:
    if not runtime.grid_cells:
        return len(runtime.grid_links)
    return sum(1 for cell in runtime.grid_cells.values() if cell.in_scope)


def total_in_scope_cells_for_walk_limit(runtime: RuntimeData, *, max_walk_s: int) -> int:
    if max_walk_s < 0:
        return 0
    if not runtime.grid_links:
        return 0
    return sum(
        1
        for links in runtime.grid_links.values()
        if links and min(walk_seconds for _, walk_seconds in links) <= max_walk_s
    )


def cell_times_from_dist(
    runtime: RuntimeData,
    dist: list[int],
    *,
    max_time_s: int,
) -> dict[int, int]:
    cell_times: dict[int, int] = {}
    for cell_id, links in runtime.grid_links.items():
        best = INF
        for node_idx, walk_seconds in links:
            cand = dist[node_idx] + walk_seconds
            if cand < best:
                best = cand
        if best >= INF or best > max_time_s:
            continue
        cell_times[int(cell_id)] = int(best)
    return cell_times


def cells_from_cell_times(
    runtime: RuntimeData,
    cell_times: dict[int, int],
) -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    for cell_id in sorted(cell_times):
        cell = runtime.grid_cells.get(cell_id)
        if cell is None:
            continue
        cells.append(
            {
                "cell_id": cell_id,
                "lat": cell.lat,
                "lon": cell.lon,
                "time_s": int(cell_times[cell_id]),
            }
        )
    return cells


def reachable_cells(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    origin_lat: float,
    origin_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
) -> tuple[list[tuple[int, int]], list[dict[str, object]]]:
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
    cell_times = cell_times_from_dist(runtime, dist, max_time_s=max_time_s)
    return seeds, cells_from_cell_times(runtime, cell_times)
