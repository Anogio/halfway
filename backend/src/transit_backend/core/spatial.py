from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from transit_backend.core.artifacts import RuntimeData
from transit_shared.geo import bucket_key
from transit_shared.routing import (
    dijkstra_min_times,
    dijkstra_with_predecessors as shared_dijkstra_with_predecessors,
    nearest_k_seed_candidates,
    seed_candidates_within_radius,
)
from transit_shared.seed_selection import (
    NearestNodeIndex,
    build_nearest_node_index,
    resolve_access_candidates as shared_resolve_access_candidates,
)


@dataclass
class SpatialIndex:
    radius_m: float
    bucket: dict[tuple[int, int], list[int]]
    node_coords: dict[int, tuple[float, float]]
    nearest_index: NearestNodeIndex
    rail_node_ids: frozenset[int]
    rail_nearest_index: NearestNodeIndex | None


def build_spatial_index(runtime: RuntimeData, radius_m: float) -> SpatialIndex:
    bucket: dict[tuple[int, int], list[int]] = defaultdict(list)
    node_coords: dict[int, tuple[float, float]] = {}
    for node in runtime.nodes:
        if node.node_kind != "physical":
            continue
        bucket[bucket_key(node.lat, node.lon, radius_m)].append(node.idx)
        node_coords[node.idx] = (node.lat, node.lon)
    rail_node_coords = {
        node.idx: (node.lat, node.lon)
        for node in runtime.nodes
        if node.node_kind == "physical" and node.is_rail_like
    }
    return SpatialIndex(
        radius_m=radius_m,
        bucket=dict(bucket),
        node_coords=node_coords,
        nearest_index=build_nearest_node_index(node_coords),
        rail_node_ids=frozenset(rail_node_coords),
        rail_nearest_index=(
            build_nearest_node_index(rail_node_coords) if rail_node_coords else None
        ),
    )


def nearby_nodes(
    _runtime: RuntimeData,
    spatial: SpatialIndex,
    lat: float,
    lon: float,
    radius_m: float,
    walk_speed_mps: float,
    limit: int,
) -> list[tuple[int, int]]:
    return seed_candidates_within_radius(
        lat=lat,
        lon=lon,
        search_radius_m=radius_m,
        bucket_radius_m=spatial.radius_m,
        bucket_index=spatial.bucket,
        node_coords=spatial.node_coords,
        walk_speed_mps=walk_speed_mps,
        limit=limit,
    )


def nearest_k(
    runtime: RuntimeData,
    lat: float,
    lon: float,
    walk_speed_mps: float,
    k: int,
) -> list[tuple[int, int]]:
    node_coords = {node.idx: (node.lat, node.lon) for node in runtime.nodes if node.node_kind == "physical"}
    return nearest_k_seed_candidates(
        lat=lat,
        lon=lon,
        node_coords=node_coords,
        walk_speed_mps=walk_speed_mps,
        k=k,
        nearest_index=build_nearest_node_index(node_coords),
    )


def resolve_access_candidates(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    lat: float,
    lon: float,
    radius_m: float,
    fallback_k: int,
    limit: int,
    walk_speed_mps: float,
) -> list[tuple[int, int]]:
    cap = max(1, limit)
    return shared_resolve_access_candidates(
        lat=lat,
        lon=lon,
        search_radius_m=radius_m,
        bucket_radius_m=spatial.radius_m,
        bucket_index=spatial.bucket,
        node_coords=spatial.node_coords,
        walk_speed_mps=walk_speed_mps,
        limit=cap,
        fallback_k=max(1, fallback_k),
        allow_global_fallback=True,
        force_inclusion_ids=spatial.rail_node_ids,
        forced_k=max(1, fallback_k),
        nearest_index=spatial.nearest_index,
        forced_nearest_index=spatial.rail_nearest_index,
    )


def resolve_seeds(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    origin_lat: float,
    origin_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
) -> list[tuple[int, int]]:
    return resolve_access_candidates(
        runtime,
        spatial,
        lat=origin_lat,
        lon=origin_lon,
        radius_m=first_mile_radius_m,
        fallback_k=first_mile_fallback_k,
        limit=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
    )


def dijkstra(runtime: RuntimeData, seeds: list[tuple[int, int]], max_time_s: int) -> list[int]:
    return dijkstra_min_times(
        offsets=runtime.offsets,
        targets=runtime.targets,
        weights=runtime.weights,
        seeds=seeds,
        max_time_s=max_time_s,
    )


def dijkstra_with_predecessors(
    runtime: RuntimeData,
    seeds: list[tuple[int, int]],
    max_time_s: int,
) -> tuple[list[int], list[int], list[int]]:
    return shared_dijkstra_with_predecessors(
        offsets=runtime.offsets,
        targets=runtime.targets,
        weights=runtime.weights,
        seeds=seeds,
        max_time_s=max_time_s,
    )


def reverse_dijkstra_with_predecessors(
    runtime: RuntimeData,
    seeds: list[tuple[int, int]],
    max_time_s: int,
) -> tuple[list[int], list[int], list[int]]:
    return shared_dijkstra_with_predecessors(
        offsets=runtime.reverse_offsets,
        targets=runtime.reverse_targets,
        weights=runtime.reverse_weights,
        seeds=seeds,
        max_time_s=max_time_s,
    )
