from __future__ import annotations

from collections.abc import Mapping, Sequence

from transit_backend.core.artifacts import RuntimeData


def _legend(runtime: RuntimeData) -> dict[int, str]:
    return runtime.edge_kind_legend or {
        0: "ride",
        1: "transfer_pathway",
        2: "transfer_gtfs",
        3: "transfer_fallback",
    }


def _visible_node_payload(runtime: RuntimeData, node_idx: int) -> dict[str, object]:
    node = runtime.nodes[node_idx]
    return {
        "node_idx": node_idx,
        "stop_id": node.stop_id,
        "stop_name": node.name,
        "lat": node.lat,
        "lon": node.lon,
    }


def _build_nodes_payload(runtime: RuntimeData, node_path: list[int]) -> list[dict[str, object]]:
    visible: list[int] = []
    for node_idx in node_path:
        physical_idx = runtime.physical_node_idx_for(node_idx)
        if not visible or visible[-1] != physical_idx:
            visible.append(physical_idx)
    return [_visible_node_payload(runtime, node_idx) for node_idx in visible]


def _prev_edge_for(prev_edge: Sequence[int] | Mapping[int, int], node_idx: int) -> int:
    if isinstance(prev_edge, Mapping):
        return int(prev_edge.get(node_idx, -1))
    if 0 <= node_idx < len(prev_edge):
        return int(prev_edge[node_idx])
    return -1


def _build_v1_segments(
    runtime: RuntimeData,
    *,
    node_path: list[int],
    prev_edge: Sequence[int] | Mapping[int, int],
    origin_walk_s: int,
    destination_walk_s: int,
    best_node: int,
) -> list[dict[str, object]]:
    legend = _legend(runtime)
    segments: list[dict[str, object]] = []
    first_node = runtime.nodes[node_path[0]]
    if origin_walk_s > 0:
        segments.append(
            {
                "type": "walk_origin",
                "kind": "walk_origin",
                "seconds": origin_walk_s,
                "from_label": "origin",
                "to_label": first_node.name,
                "to_stop_id": first_node.stop_id,
            }
        )

    for pos in range(1, len(node_path)):
        to_idx = node_path[pos]
        from_idx = node_path[pos - 1]
        edge_idx = _prev_edge_for(prev_edge, to_idx)
        if edge_idx < 0:
            continue

        edge_kind = runtime.edge_kinds[edge_idx] if edge_idx < len(runtime.edge_kinds) else 0
        kind_name = legend.get(edge_kind, f"kind_{edge_kind}")
        route_id = runtime.edge_route_ids[edge_idx] if edge_idx < len(runtime.edge_route_ids) else ""
        route_label = runtime.route_labels.get(route_id, route_id) if route_id else ""

        from_node = runtime.nodes[from_idx]
        to_node = runtime.nodes[to_idx]

        segments.append(
            {
                "type": "graph_edge",
                "kind": kind_name,
                "seconds": int(runtime.weights[edge_idx]),
                "from_node_idx": from_idx,
                "to_node_idx": to_idx,
                "from_stop_id": from_node.stop_id,
                "from_stop_name": from_node.name,
                "to_stop_id": to_node.stop_id,
                "to_stop_name": to_node.name,
                "route_id": route_id,
                "route_label": route_label,
            }
        )

    last_node = runtime.nodes[best_node]
    if destination_walk_s > 0:
        segments.append(
            {
                "type": "walk_destination",
                "kind": "walk_destination",
                "seconds": int(destination_walk_s),
                "from_label": last_node.name,
                "from_stop_id": last_node.stop_id,
                "to_label": "destination",
            }
        )
    return segments


def _build_v2_segments(
    runtime: RuntimeData,
    *,
    node_path: list[int],
    prev_edge: Sequence[int] | Mapping[int, int],
    origin_walk_s: int,
    destination_walk_s: int,
    best_node: int,
) -> tuple[list[dict[str, object]], int, int]:
    legend = _legend(runtime)
    segments: list[dict[str, object]] = []
    first_physical = runtime.nodes[runtime.physical_node_idx_for(node_path[0])]
    if origin_walk_s > 0:
        segments.append(
            {
                "type": "walk_origin",
                "kind": "walk_origin",
                "seconds": origin_walk_s,
                "from_label": "origin",
                "to_label": first_physical.name,
                "to_stop_id": first_physical.stop_id,
            }
        )

    pending_boarding_wait_s = 0
    boarding_wait_s = 0
    transfer_s = 0

    for pos in range(1, len(node_path)):
        to_idx = node_path[pos]
        from_idx = node_path[pos - 1]
        edge_idx = _prev_edge_for(prev_edge, to_idx)
        if edge_idx < 0:
            continue

        edge_kind = runtime.edge_kinds[edge_idx] if edge_idx < len(runtime.edge_kinds) else 0
        kind_name = legend.get(edge_kind, f"kind_{edge_kind}")
        route_id = runtime.edge_route_ids[edge_idx] if edge_idx < len(runtime.edge_route_ids) else ""
        route_label = runtime.route_labels.get(route_id, route_id) if route_id else ""
        seconds = int(runtime.weights[edge_idx])

        if kind_name == "boarding":
            pending_boarding_wait_s += seconds
            boarding_wait_s += seconds
            continue

        if kind_name == "alight":
            continue

        if kind_name == "ride":
            from_physical_idx = runtime.physical_node_idx_for(from_idx)
            to_physical_idx = runtime.physical_node_idx_for(to_idx)
            from_node = runtime.nodes[from_physical_idx]
            to_node = runtime.nodes[to_physical_idx]
            if (
                segments
                and segments[-1]["type"] == "graph_edge"
                and segments[-1]["kind"] == "ride"
                and segments[-1]["route_id"] == route_id
            ):
                segments[-1]["seconds"] = int(segments[-1]["seconds"]) + seconds
                segments[-1]["ride_runtime_s"] = int(segments[-1]["ride_runtime_s"]) + seconds
                segments[-1]["to_node_idx"] = to_physical_idx
                segments[-1]["to_stop_id"] = to_node.stop_id
                segments[-1]["to_stop_name"] = to_node.name
            else:
                segments.append(
                    {
                        "type": "graph_edge",
                        "kind": "ride",
                        "seconds": pending_boarding_wait_s + seconds,
                        "boarding_wait_s": pending_boarding_wait_s,
                        "ride_runtime_s": seconds,
                        "from_node_idx": from_physical_idx,
                        "to_node_idx": to_physical_idx,
                        "from_stop_id": from_node.stop_id,
                        "from_stop_name": from_node.name,
                        "to_stop_id": to_node.stop_id,
                        "to_stop_name": to_node.name,
                        "route_id": route_id,
                        "route_label": route_label,
                    }
                )
            pending_boarding_wait_s = 0
            continue

        if kind_name.startswith("transfer_"):
            from_physical_idx = runtime.physical_node_idx_for(from_idx)
            to_physical_idx = runtime.physical_node_idx_for(to_idx)
            from_node = runtime.nodes[from_physical_idx]
            to_node = runtime.nodes[to_physical_idx]
            transfer_s += seconds
            segments.append(
                {
                    "type": "graph_edge",
                    "kind": kind_name,
                    "seconds": seconds,
                    "from_node_idx": from_physical_idx,
                    "to_node_idx": to_physical_idx,
                    "from_stop_id": from_node.stop_id,
                    "from_stop_name": from_node.name,
                    "to_stop_id": to_node.stop_id,
                    "to_stop_name": to_node.name,
                    "route_id": "",
                    "route_label": "",
                }
            )

    last_node = runtime.nodes[runtime.physical_node_idx_for(best_node)]
    if destination_walk_s > 0:
        segments.append(
            {
                "type": "walk_destination",
                "kind": "walk_destination",
                "seconds": int(destination_walk_s),
                "from_label": last_node.name,
                "from_stop_id": last_node.stop_id,
                "to_label": "destination",
            }
        )
    return segments, boarding_wait_s, transfer_s


def build_direct_walk_path_payload(
    runtime: RuntimeData,
    *,
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    seed_count: int,
    destination_candidate_count: int,
    total_walk_s: int,
    max_time_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    payload = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": destination_lat, "lon": destination_lon},
        "profile": runtime.profile,
        "reachable": True,
        "summary": {
            "total_time_s": int(total_walk_s),
            "max_time_s": max_time_s,
        },
        "segments": [
            {
                "type": "walk_origin",
                "kind": "walk_origin",
                "seconds": int(total_walk_s),
                "from_label": "origin",
                "to_label": "destination",
            }
        ],
        "nodes": [],
    }
    if include_stats:
        payload["stats"] = {
            "seed_count": seed_count,
            "destination_candidate_count": destination_candidate_count,
            "node_count": 0,
            "segment_count": 1,
            "origin_walk_s": int(total_walk_s),
            "graph_time_s": 0,
            "destination_walk_s": 0,
        }
    return payload


def build_reachable_path_payload(
    runtime: RuntimeData,
    *,
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    seeds: list[tuple[int, int]],
    destination_candidates: list[tuple[int, int]],
    node_path: list[int],
    prev_edge: Sequence[int] | Mapping[int, int],
    graph_time_s: int,
    best_node: int,
    destination_walk_s: int,
    best_total: int,
    max_time_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    seed_costs = {node_idx: cost for node_idx, cost in seeds}
    origin_walk_s = int(seed_costs.get(node_path[0], 0))
    nodes_payload = _build_nodes_payload(runtime, node_path)
    boarding_wait_s = 0
    transfer_s = 0
    if runtime.version == "v2":
        segments, boarding_wait_s, transfer_s = _build_v2_segments(
            runtime,
            node_path=node_path,
            prev_edge=prev_edge,
            origin_walk_s=origin_walk_s,
            destination_walk_s=destination_walk_s,
            best_node=best_node,
        )
    else:
        segments = _build_v1_segments(
            runtime,
            node_path=node_path,
            prev_edge=prev_edge,
            origin_walk_s=origin_walk_s,
            destination_walk_s=destination_walk_s,
            best_node=best_node,
        )

    payload = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": destination_lat, "lon": destination_lon},
        "profile": runtime.profile,
        "reachable": True,
        "summary": {
            "total_time_s": int(best_total),
            "max_time_s": max_time_s,
        },
        "nodes": nodes_payload,
        "segments": segments,
    }
    if include_stats:
        ride_runtime_s = max(0, graph_time_s - boarding_wait_s - transfer_s)
        payload["stats"] = {
            "seed_count": len(seeds),
            "destination_candidate_count": len(destination_candidates),
            "node_count": len(nodes_payload),
            "segment_count": len(segments),
            "origin_walk_s": origin_walk_s,
            "graph_time_s": graph_time_s,
            "boarding_wait_s": boarding_wait_s,
            "ride_runtime_s": ride_runtime_s,
            "transfer_s": transfer_s,
            "destination_walk_s": int(destination_walk_s),
        }
    return payload


def build_unreachable_path_payload(
    runtime: RuntimeData,
    *,
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
    seed_count: int,
    destination_candidate_count: int,
    max_time_s: int,
    include_stats: bool = True,
) -> dict[str, object]:
    payload = {
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": destination_lat, "lon": destination_lon},
        "profile": runtime.profile,
        "reachable": False,
        "summary": {"max_time_s": max_time_s},
        "segments": [],
        "nodes": [],
    }
    if include_stats:
        payload["stats"] = {
            "seed_count": seed_count,
            "destination_candidate_count": destination_candidate_count,
        }
    return payload
