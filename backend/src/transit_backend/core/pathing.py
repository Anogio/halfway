from __future__ import annotations

from transit_backend.core.artifacts import RuntimeData
from transit_backend.core.path_payloads import (
    build_direct_walk_path_payload,
    build_reachable_path_payload,
    build_unreachable_path_payload,
)
from transit_backend.core.spatial import (
    SpatialIndex,
    dijkstra_with_predecessors,
    reverse_dijkstra_with_predecessors,
    resolve_access_candidates,
    resolve_seeds,
)
from transit_shared.geo import haversine_m
from transit_shared.routing import INF


def compute_path(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    direct_walk_s = int(round(haversine_m(origin_lat, origin_lon, destination_lat, destination_lon) / walk_speed_mps))
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

    destination_candidates = resolve_access_candidates(
        runtime,
        spatial,
        lat=destination_lat,
        lon=destination_lon,
        radius_m=first_mile_radius_m,
        fallback_k=first_mile_fallback_k,
        limit=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
    )

    dist, prev_node, prev_edge = dijkstra_with_predecessors(runtime, seeds, max_time_s=max_time_s)

    best_node = -1
    destination_walk_s = INF
    best_total = INF
    for node_idx, walk_seconds in destination_candidates:
        cand = dist[node_idx] + walk_seconds
        if cand < best_total:
            best_total = cand
            best_node = node_idx
            destination_walk_s = walk_seconds

    if direct_walk_s <= max_time_s and direct_walk_s <= best_total:
        return build_direct_walk_path_payload(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            seed_count=len(seeds),
            destination_candidate_count=len(destination_candidates),
            total_walk_s=direct_walk_s,
            max_time_s=max_time_s,
            include_stats=include_stats,
        )

    if best_node < 0 or best_total >= INF:
        if direct_walk_s <= max_time_s:
            return build_direct_walk_path_payload(
                runtime,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                seed_count=len(seeds),
                destination_candidate_count=len(destination_candidates),
                total_walk_s=direct_walk_s,
                max_time_s=max_time_s,
                include_stats=include_stats,
            )
        return build_unreachable_path_payload(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            seed_count=len(seeds),
            destination_candidate_count=len(destination_candidates),
            max_time_s=max_time_s,
            include_stats=include_stats,
        )

    node_path: list[int] = []
    cursor = best_node
    while cursor >= 0:
        node_path.append(cursor)
        cursor = prev_node[cursor]
    node_path.reverse()

    if not node_path:
        return build_unreachable_path_payload(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            seed_count=len(seeds),
            destination_candidate_count=len(destination_candidates),
            max_time_s=max_time_s,
        )

    has_graph_edge = any(prev_edge[node_idx] >= 0 for node_idx in node_path[1:])
    if not has_graph_edge and direct_walk_s <= max_time_s:
        return build_direct_walk_path_payload(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            seed_count=len(seeds),
            destination_candidate_count=len(destination_candidates),
            total_walk_s=direct_walk_s,
            max_time_s=max_time_s,
            include_stats=include_stats,
        )

    origin_walk_s = min((cost for node_idx, cost in seeds if node_idx == node_path[0]), default=0)
    return build_reachable_path_payload(
        runtime,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        destination_lat=destination_lat,
        destination_lon=destination_lon,
        seeds=seeds,
        destination_candidates=destination_candidates,
        node_path=node_path,
        prev_edge=prev_edge,
        graph_time_s=int(dist[best_node] - origin_walk_s),
        best_node=best_node,
        destination_walk_s=destination_walk_s,
        best_total=best_total,
        max_time_s=max_time_s,
        include_stats=include_stats,
    )


def compute_multi_path(
    runtime: RuntimeData,
    spatial: SpatialIndex,
    origins: list[dict[str, object]],
    destination_lat: float,
    destination_lon: float,
    first_mile_radius_m: float,
    first_mile_fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    max_time_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    destination_candidates = resolve_access_candidates(
        runtime,
        spatial,
        lat=destination_lat,
        lon=destination_lon,
        radius_m=first_mile_radius_m,
        fallback_k=first_mile_fallback_k,
        limit=max_seed_nodes,
        walk_speed_mps=walk_speed_mps,
    )
    reverse_dist, reverse_prev_node, reverse_prev_edge = reverse_dijkstra_with_predecessors(
        runtime,
        destination_candidates,
        max_time_s=max_time_s,
    )
    destination_walk_by_node: dict[int, int] = {}
    for node_idx, walk_seconds in destination_candidates:
        current = destination_walk_by_node.get(node_idx)
        if current is None or walk_seconds < current:
            destination_walk_by_node[node_idx] = walk_seconds

    path_results: list[dict[str, object]] = []
    for origin in origins:
        origin_lat = float(origin["lat"])
        origin_lon = float(origin["lon"])
        direct_walk_s = int(round(haversine_m(origin_lat, origin_lon, destination_lat, destination_lon) / walk_speed_mps))
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

        best_origin_node = -1
        best_total = INF
        origin_walk_s = INF
        for node_idx, walk_seconds in seeds:
            cand = reverse_dist[node_idx] + walk_seconds
            if cand < best_total:
                best_total = cand
                best_origin_node = node_idx
                origin_walk_s = walk_seconds

        if direct_walk_s <= max_time_s and direct_walk_s <= best_total:
            path_payload = build_direct_walk_path_payload(
                runtime,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                seed_count=len(seeds),
                destination_candidate_count=len(destination_candidates),
                total_walk_s=direct_walk_s,
                max_time_s=max_time_s,
                include_stats=include_stats,
            )
            path_results.append({"origin_id": str(origin["id"]), **path_payload})
            continue

        if best_origin_node < 0 or best_total >= INF:
            if direct_walk_s <= max_time_s:
                path_payload = build_direct_walk_path_payload(
                    runtime,
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    seed_count=len(seeds),
                    destination_candidate_count=len(destination_candidates),
                    total_walk_s=direct_walk_s,
                    max_time_s=max_time_s,
                    include_stats=include_stats,
                )
            else:
                path_payload = build_unreachable_path_payload(
                    runtime,
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    destination_lat=destination_lat,
                    destination_lon=destination_lon,
                    seed_count=len(seeds),
                    destination_candidate_count=len(destination_candidates),
                    max_time_s=max_time_s,
                    include_stats=include_stats,
                )
            path_results.append({"origin_id": str(origin["id"]), **path_payload})
            continue

        node_path: list[int] = []
        forward_prev_edge: dict[int, int] = {}
        cursor = best_origin_node
        while cursor >= 0:
            node_path.append(cursor)
            next_node = reverse_prev_node[cursor]
            if next_node >= 0:
                reverse_edge_idx = reverse_prev_edge[cursor]
                if 0 <= reverse_edge_idx < len(runtime.reverse_edge_to_forward):
                    forward_prev_edge[next_node] = runtime.reverse_edge_to_forward[reverse_edge_idx]
            cursor = next_node

        if not node_path:
            path_payload = build_unreachable_path_payload(
                runtime,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                seed_count=len(seeds),
                destination_candidate_count=len(destination_candidates),
                max_time_s=max_time_s,
                include_stats=include_stats,
            )
            path_results.append({"origin_id": str(origin["id"]), **path_payload})
            continue

        best_node = node_path[-1]
        destination_walk_s = int(destination_walk_by_node.get(best_node, 0))
        has_graph_edge = any(node_idx in forward_prev_edge for node_idx in node_path[1:])
        if not has_graph_edge and direct_walk_s <= max_time_s:
            path_payload = build_direct_walk_path_payload(
                runtime,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                destination_lat=destination_lat,
                destination_lon=destination_lon,
                seed_count=len(seeds),
                destination_candidate_count=len(destination_candidates),
                total_walk_s=direct_walk_s,
                max_time_s=max_time_s,
                include_stats=include_stats,
            )
            path_results.append({"origin_id": str(origin["id"]), **path_payload})
            continue

        graph_time_s = max(0, int(best_total) - int(origin_walk_s) - int(destination_walk_s))
        path_payload = build_reachable_path_payload(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            seeds=seeds,
            destination_candidates=destination_candidates,
            node_path=node_path,
            prev_edge=forward_prev_edge,
            graph_time_s=graph_time_s,
            best_node=best_node,
            destination_walk_s=destination_walk_s,
            best_total=int(best_total),
            max_time_s=max_time_s,
            include_stats=include_stats,
        )
        path_results.append({"origin_id": str(origin["id"]), **path_payload})

    return {
        "destination": {"lat": destination_lat, "lon": destination_lon},
        "profile": runtime.profile,
        "paths": path_results,
    }
