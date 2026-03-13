from __future__ import annotations

import csv
import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from transit_offline.cities import get_city_plugin
from transit_offline.common.artifacts import GRAPH_ARTIFACT_PATTERNS, archive_existing_artifacts
from transit_offline.common.config import AppConfig, ensure_dirs, load_config
from transit_offline.common.time import parse_gtfs_time_to_seconds
from transit_offline.graph.gtfs import (
    parse_pathways,
    parse_transfers,
    read_route_labels,
    read_route_types,
    read_stop_parent_map,
    read_trips,
)
from transit_shared.geo import bucket_key, haversine_m, neighbor_bucket_keys
from transit_shared.modes import is_rail_like_route_type


@dataclass
class RideStats:
    count: int = 0
    total: int = 0

    def add(self, value: int) -> None:
        self.count += 1
        self.total += value

    @property
    def avg(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total / self.count


@dataclass(frozen=True)
class Node:
    idx: int
    stop_id: str
    name: str
    lat: float
    lon: float
    parent_station: str
    location_type: str = "0"


@dataclass(frozen=True)
class RouteStateNode:
    idx: int
    node_kind: str
    node_key: str
    stop_id: str
    name: str
    lat: float
    lon: float
    parent_station: str
    location_type: str
    is_rail_like: bool
    physical_node_idx: int | None = None
    route_id: str = ""
    direction_id: str = ""


def _read_nodes(nodes_csv: Path) -> tuple[list[Node], dict[str, int], dict[int, str]]:
    nodes: list[Node] = []
    stop_to_idx: dict[str, int] = {}
    idx_to_stop: dict[int, str] = {}
    with nodes_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            idx = int(row["node_idx"])
            node = Node(
                idx=idx,
                stop_id=row["stop_id"],
                name=row.get("stop_name", ""),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                parent_station=row.get("parent_station", ""),
                location_type=row.get("location_type", "0"),
            )
            nodes.append(node)
            stop_to_idx[node.stop_id] = node.idx
            idx_to_stop[node.idx] = node.stop_id
    nodes.sort(key=lambda n: n.idx)
    return nodes, stop_to_idx, idx_to_stop


def _build_station_index(nodes: list[Node]) -> dict[str, list[int]]:
    station_to_nodes: dict[str, list[int]] = defaultdict(list)
    for node in nodes:
        if node.parent_station:
            station_to_nodes[node.parent_station].append(node.idx)
        station_to_nodes[node.stop_id].append(node.idx)
    return station_to_nodes


def _compute_waits(dep_by_route_dir: dict[tuple[str, str], list[int]], wait_cap: int) -> dict[tuple[str, str], int]:
    waits: dict[tuple[str, str], int] = {}
    for key, deps in dep_by_route_dir.items():
        if len(deps) < 2:
            waits[key] = wait_cap // 2
            continue
        deps_sorted = sorted(deps)
        intervals = [deps_sorted[i + 1] - deps_sorted[i] for i in range(len(deps_sorted) - 1)]
        intervals = [v for v in intervals if v > 0]
        if not intervals:
            waits[key] = wait_cap // 2
            continue
        med = statistics.median(intervals)
        waits[key] = int(min(wait_cap, med / 2.0))
    return waits


def _compute_route_dir_trip_segment_medians(
    trip_segment_counts: dict[str, int],
    trip_map: dict[str, tuple[str, str]],
) -> dict[tuple[str, str], int]:
    by_route_dir: dict[tuple[str, str], list[int]] = defaultdict(list)
    for trip_id, seg_count in trip_segment_counts.items():
        if seg_count <= 0:
            continue
        route_dir = trip_map.get(trip_id)
        if route_dir is None:
            continue
        by_route_dir[route_dir].append(seg_count)

    medians: dict[tuple[str, str], int] = {}
    for route_dir, counts in by_route_dir.items():
        if not counts:
            continue
        medians[route_dir] = max(1, int(round(statistics.median(counts))))
    return medians


def _add_best(
    edge_map: dict[tuple[int, int], tuple[int, int, str]],
    key: tuple[int, int],
    weight: int,
    kind: int,
    route_id: str = "",
) -> None:
    existing = edge_map.get(key)
    if existing is None:
        edge_map[key] = (weight, kind, route_id)
        return

    ex_weight, ex_kind, ex_route_id = existing
    if weight < ex_weight:
        edge_map[key] = (weight, kind, route_id)
    elif weight == ex_weight and kind < ex_kind:
        edge_map[key] = (weight, kind, route_id)
    elif weight == ex_weight and kind == ex_kind and kind == 0 and route_id and (
        not ex_route_id or route_id < ex_route_id
    ):
        edge_map[key] = (weight, kind, route_id)


def _build_adjacency(
    n: int,
    edge_map: dict[tuple[int, int], tuple[int, int, str]],
) -> tuple[dict[int, list[tuple[int, int, int, str]]], Counter, list[int], list[int], list[int], list[str]]:
    adj: dict[int, list[tuple[int, int, int, str]]] = defaultdict(list)
    edge_kind_counter: Counter = Counter()
    for (a, b), (weight, kind, route_id) in edge_map.items():
        adj[a].append((b, weight, kind, route_id))
        edge_kind_counter[kind] += 1

    offsets = [0]
    targets: list[int] = []
    weights: list[int] = []
    kinds: list[int] = []
    route_ids: list[str] = []

    for node_idx in range(n):
        row = adj.get(node_idx, [])
        row.sort(key=lambda item: item[0])
        for target, weight, kind, route_id in row:
            targets.append(target)
            weights.append(weight)
            kinds.append(kind)
            route_ids.append(route_id)
        offsets.append(len(targets))

    return adj, edge_kind_counter, offsets, targets, weights, kinds, route_ids


def _spatial_fallback_edges(
    nodes: list[Node],
    existing: set[tuple[int, int]],
    radius_m: float,
    walk_speed_mps: float,
    transfer_penalty_s: int,
    max_neighbors: int,
) -> dict[tuple[int, int], int]:
    by_bucket: dict[tuple[int, int], list[Node]] = defaultdict(list)
    for node in nodes:
        by_bucket[bucket_key(node.lat, node.lon, radius_m)].append(node)

    edges: dict[tuple[int, int], int] = {}
    for node in nodes:
        key = bucket_key(node.lat, node.lon, radius_m)
        candidates: list[tuple[float, Node]] = []

        for nb_key in neighbor_bucket_keys(key, rings=1):
            for other in by_bucket.get(nb_key, []):
                if other.idx == node.idx:
                    continue
                pair = (node.idx, other.idx)
                if pair in existing:
                    continue
                dist = haversine_m(node.lat, node.lon, other.lat, other.lon)
                if 0.0 < dist <= radius_m:
                    candidates.append((dist, other))

        candidates.sort(key=lambda item: item[0])
        for dist, other in candidates[:max_neighbors]:
            weight = int(round(dist / walk_speed_mps + transfer_penalty_s))
            edges[(node.idx, other.idx)] = min(edges.get((node.idx, other.idx), weight), weight)

    return edges


def _node_hub_ids(nodes: list[Node], stop_parent: dict[str, str]) -> dict[int, str]:
    def heuristic_hub_id(stop_id: str) -> str:
        # Many TfL rail platform stop_ids follow patterns like 9400ZZLUVIC2.
        # If parent_station is missing, derive a stable hub stem by dropping
        # the trailing platform designator.
        if stop_id.startswith("9400ZZ") and len(stop_id) > 7:
            tail = stop_id[-1]
            if tail.isalnum():
                return f"STEM_{stop_id[:-1]}"
        return ""

    hubs: dict[int, str] = {}
    for node in nodes:
        hub = (
            (node.parent_station or "").strip()
            or (stop_parent.get(node.stop_id, "") or "").strip()
            or heuristic_hub_id(node.stop_id)
        )
        if hub:
            hubs[node.idx] = hub
    return hubs


def _calibrate_hub_transfer_base(
    pathway_edges: dict[tuple[int, int], int],
    node_hubs: dict[int, str],
    fallback_s: int,
) -> int:
    same_hub_times: list[int] = []
    for (from_idx, to_idx), time_s in pathway_edges.items():
        if time_s <= 0:
            continue
        from_hub = node_hubs.get(from_idx, "")
        to_hub = node_hubs.get(to_idx, "")
        if from_hub and from_hub == to_hub:
            same_hub_times.append(time_s)

    if same_hub_times:
        base = int(round(statistics.median(same_hub_times)))
    else:
        base = fallback_s
    return max(60, min(900, base))


def _synthesize_hub_transfer_edges(
    nodes: list[Node],
    existing: set[tuple[int, int]],
    node_hubs: dict[int, str],
    walk_speed_mps: float,
    base_transfer_s: int,
    max_neighbors: int,
) -> dict[tuple[int, int], int]:
    hub_to_nodes: dict[str, list[Node]] = defaultdict(list)
    for node in nodes:
        hub = node_hubs.get(node.idx, "")
        if not hub:
            continue
        hub_to_nodes[hub].append(node)

    edges: dict[tuple[int, int], int] = {}
    for hub_nodes in hub_to_nodes.values():
        if len(hub_nodes) < 2:
            continue
        for node in hub_nodes:
            candidates: list[tuple[float, Node]] = []
            for other in hub_nodes:
                if other.idx == node.idx:
                    continue
                pair = (node.idx, other.idx)
                if pair in existing:
                    continue
                dist_m = haversine_m(node.lat, node.lon, other.lat, other.lon)
                candidates.append((dist_m, other))

            if not candidates:
                continue
            candidates.sort(key=lambda item: item[0])
            for dist_m, other in candidates[:max_neighbors]:
                walk_s = dist_m / walk_speed_mps if walk_speed_mps > 0 else 0.0
                # Add a small station-connection overhead and floor by calibrated base.
                weight = int(round(max(base_transfer_s, walk_s + 30.0)))
                edge = (node.idx, other.idx)
                prev = edges.get(edge)
                if prev is None or weight < prev:
                    edges[edge] = weight

    return edges


def _normalize_transfer_weight(weight: int, *, min_floor_s: int) -> tuple[int, bool]:
    if weight >= min_floor_s:
        return weight, False
    return max(1, min_floor_s), True


def run_build_graph(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    ensure_dirs(cfg)

    interim = cfg.paths.offline_interim_dir
    artifacts = cfg.paths.offline_artifacts_dir
    gtfs = cfg.paths.gtfs_input
    version = cfg.city.artifact_version

    nodes, stop_to_idx, _ = _read_nodes(interim / "nodes.csv")
    station_to_nodes = _build_station_index(nodes)
    stop_parent = read_stop_parent_map(gtfs)
    trip_map = read_trips(interim / "trips_weekday.csv")
    route_types = read_route_types(interim / "routes_selected.csv")
    plugin = get_city_plugin(cfg.city_id)
    route_labels = read_route_labels(gtfs / "routes.txt", set(route_types), formatter=plugin.format_route_label)

    wait_cap = cfg.settings.weights.wait_cap_s
    walk_speed = cfg.settings.weights.walk_speed_mps
    transfer_penalty = cfg.settings.weights.transfer_penalty_s
    transfer_min_floor_s = 120
    fallback_radius = cfg.settings.search.transfer_fallback_radius_m
    fallback_max_neighbors = cfg.settings.search.transfer_fallback_max_neighbors
    max_interstop_ride_s = cfg.settings.graph.max_interstop_ride_s

    ride_stats: dict[tuple[int, int, str, str], RideStats] = defaultdict(RideStats)
    departures: dict[tuple[str, str], list[int]] = defaultdict(list)
    node_is_rail_like = [False] * len(nodes)
    onboard_keys: set[tuple[int, str, str]] = set()

    prev_by_trip: dict[str, tuple[int, int]] = {}
    first_departure_seen: set[str] = set()
    trip_segment_counts: dict[str, int] = defaultdict(int)
    stop_times_rows = 0

    with (gtfs / "stop_times.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            trip_id = row["trip_id"].strip()
            trip_info = trip_map.get(trip_id)
            if trip_info is None:
                continue

            stop_id = row["stop_id"].strip()
            to_idx = stop_to_idx.get(stop_id)
            if to_idx is None:
                continue

            arr = parse_gtfs_time_to_seconds(row["arrival_time"].strip())
            dep = parse_gtfs_time_to_seconds(row["departure_time"].strip())
            stop_times_rows += 1

            route_id, direction_id = trip_info
            route_type = route_types.get(route_id, "")
            if is_rail_like_route_type(route_type):
                node_is_rail_like[to_idx] = True
            onboard_keys.add((to_idx, route_id, direction_id))

            if trip_id not in first_departure_seen:
                departures[(route_id, direction_id)].append(dep)
                first_departure_seen.add(trip_id)

            prev = prev_by_trip.get(trip_id)
            if prev is not None:
                from_idx, prev_dep = prev
                ride = arr - prev_dep
                if 0 < ride < max_interstop_ride_s:
                    ride_stats[(from_idx, to_idx, route_id, direction_id)].add(ride)
                    trip_segment_counts[trip_id] += 1

            prev_by_trip[trip_id] = (to_idx, dep)

    waits = _compute_waits(departures, wait_cap)
    route_dir_trip_segments = _compute_route_dir_trip_segment_medians(trip_segment_counts, trip_map)

    EDGE_KIND = {
        "ride": 0,
        "transfer_pathway": 1,
        "transfer_gtfs": 2,
        "transfer_fallback": 3,
    }

    edge_map: dict[tuple[int, int], tuple[int, int, str]] = {}
    ride_edges = 0
    for (a, b, route_id, direction_id), stats in ride_stats.items():
        wait = waits.get((route_id, direction_id), wait_cap // 2)
        trip_segments = route_dir_trip_segments.get((route_id, direction_id), 1)
        wait_per_edge = int(round(wait / max(1, trip_segments)))
        weight = int(round(stats.avg + wait_per_edge))
        _add_best(edge_map, (a, b), weight, EDGE_KIND["ride"], route_id=route_id)
        ride_edges += 1

    pathway_edges = parse_pathways(gtfs, stop_to_idx, station_to_nodes, stop_parent, walk_speed)
    transfer_edges = parse_transfers(gtfs, stop_to_idx)
    node_hubs = _node_hub_ids(nodes, stop_parent)
    hub_transfer_base_s = _calibrate_hub_transfer_base(pathway_edges, node_hubs, transfer_penalty)
    hub_transfer_edges = _synthesize_hub_transfer_edges(
        nodes,
        existing=set(edge_map.keys()) | set(pathway_edges.keys()) | set(transfer_edges.keys()),
        node_hubs=node_hubs,
        walk_speed_mps=walk_speed,
        base_transfer_s=hub_transfer_base_s,
        max_neighbors=max(1, fallback_max_neighbors),
    )

    pathway_edges_floored = 0
    transfer_edges_floored = 0
    for key, weight in pathway_edges.items():
        normalized, floored = _normalize_transfer_weight(weight, min_floor_s=transfer_min_floor_s)
        if floored:
            pathway_edges_floored += 1
        _add_best(edge_map, key, normalized, EDGE_KIND["transfer_pathway"])
    for key, weight in transfer_edges.items():
        normalized, floored = _normalize_transfer_weight(weight, min_floor_s=transfer_min_floor_s)
        if floored:
            transfer_edges_floored += 1
        _add_best(edge_map, key, normalized, EDGE_KIND["transfer_gtfs"])
    for key, weight in hub_transfer_edges.items():
        _add_best(edge_map, key, weight, EDGE_KIND["transfer_gtfs"])

    existing_pairs = set(edge_map.keys())
    fallback_edges = _spatial_fallback_edges(
        nodes,
        existing=existing_pairs,
        radius_m=fallback_radius,
        walk_speed_mps=walk_speed,
        transfer_penalty_s=transfer_penalty,
        max_neighbors=fallback_max_neighbors,
    )
    for key, weight in fallback_edges.items():
        _add_best(edge_map, key, weight, EDGE_KIND["transfer_fallback"])

    n = len(nodes)
    _, edge_kind_counter, offsets, targets, weights, kinds, route_ids = _build_adjacency(n, edge_map)

    stop_to_idx_json = {node.stop_id: node.idx for node in nodes}

    archive_existing_artifacts(artifacts, patterns=GRAPH_ARTIFACT_PATTERNS)

    graph_obj = {
        "version": version,
        "profile": "weekday_non_holiday",
        "nodes_count": n,
        "nodes_index": stop_to_idx_json,
        "adj_offsets": offsets,
        "adj_targets": targets,
        "adj_weights_s": weights,
        "edge_kind": kinds,
        "edge_route_id": route_ids,
        "route_labels": route_labels,
        "edge_kind_legend": {
            str(EDGE_KIND["ride"]): "ride",
            str(EDGE_KIND["transfer_pathway"]): "transfer_pathway",
            str(EDGE_KIND["transfer_gtfs"]): "transfer_gtfs",
            str(EDGE_KIND["transfer_fallback"]): "transfer_fallback",
        },
    }

    if version != "v2":
        graph_path = artifacts / f"graph_{version}_weekday.json"
        graph_path.write_text(json.dumps(graph_obj), encoding="utf-8")

        nodes_out = artifacts / f"nodes_{version}.csv"
        with nodes_out.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "node_idx",
                    "stop_id",
                    "stop_name",
                    "parent_station",
                    "lat",
                    "lon",
                    "location_type",
                    "is_rail_like",
                ]
            )
            for node in nodes:
                writer.writerow(
                    [
                        node.idx,
                        node.stop_id,
                        node.name,
                        node.parent_station,
                        f"{node.lat}",
                        f"{node.lon}",
                        node.location_type,
                        "1" if node_is_rail_like[node.idx] else "0",
                    ]
                )

    onboard_idx_by_key: dict[tuple[int, str, str], int] = {}
    route_state_nodes: list[RouteStateNode] = []
    for node in nodes:
        route_state_nodes.append(
            RouteStateNode(
                idx=node.idx,
                node_kind="physical",
                node_key=node.stop_id,
                stop_id=node.stop_id,
                name=node.name,
                lat=node.lat,
                lon=node.lon,
                parent_station=node.parent_station,
                location_type=node.location_type,
                is_rail_like=node_is_rail_like[node.idx],
            )
        )

    next_idx = len(route_state_nodes)
    for physical_idx, route_id, direction_id in sorted(onboard_keys, key=lambda item: (item[0], item[1], item[2])):
        physical = nodes[physical_idx]
        onboard_idx_by_key[(physical_idx, route_id, direction_id)] = next_idx
        route_state_nodes.append(
            RouteStateNode(
                idx=next_idx,
                node_kind="onboard",
                node_key=f"{physical.stop_id}::{route_id}::{direction_id}",
                stop_id=physical.stop_id,
                name=physical.name,
                lat=physical.lat,
                lon=physical.lon,
                parent_station=physical.parent_station,
                location_type=physical.location_type,
                is_rail_like=is_rail_like_route_type(route_types.get(route_id, "")),
                physical_node_idx=physical_idx,
                route_id=route_id,
                direction_id=direction_id,
            )
        )
        next_idx += 1

    EDGE_KIND_V2 = {
        "ride": 0,
        "boarding": 1,
        "alight": 2,
        "transfer_pathway": 3,
        "transfer_gtfs": 4,
        "transfer_fallback": 5,
    }

    edge_map_v2: dict[tuple[int, int], tuple[int, int, str]] = {}
    for (a, b), (weight, kind, route_id) in edge_map.items():
        if kind == EDGE_KIND["ride"]:
            continue
        if kind == EDGE_KIND["transfer_pathway"]:
            translated = EDGE_KIND_V2["transfer_pathway"]
        elif kind == EDGE_KIND["transfer_gtfs"]:
            translated = EDGE_KIND_V2["transfer_gtfs"]
        else:
            translated = EDGE_KIND_V2["transfer_fallback"]
        _add_best(edge_map_v2, (a, b), weight, translated, route_id=route_id)

    for physical_idx, route_id, direction_id in onboard_keys:
        onboard_idx = onboard_idx_by_key[(physical_idx, route_id, direction_id)]
        wait = waits.get((route_id, direction_id), wait_cap // 2)
        _add_best(
            edge_map_v2,
            (physical_idx, onboard_idx),
            wait,
            EDGE_KIND_V2["boarding"],
            route_id=route_id,
        )
        _add_best(
            edge_map_v2,
            (onboard_idx, physical_idx),
            0,
            EDGE_KIND_V2["alight"],
            route_id=route_id,
        )

    ride_edges_v2 = 0
    for (a, b, route_id, direction_id), stats in ride_stats.items():
        from_onboard = onboard_idx_by_key.get((a, route_id, direction_id))
        to_onboard = onboard_idx_by_key.get((b, route_id, direction_id))
        if from_onboard is None or to_onboard is None:
            continue
        weight = int(round(stats.avg))
        _add_best(
            edge_map_v2,
            (from_onboard, to_onboard),
            weight,
            EDGE_KIND_V2["ride"],
            route_id=route_id,
        )
        ride_edges_v2 += 1

    n_v2 = len(route_state_nodes)
    _, edge_kind_counter_v2, offsets_v2, targets_v2, weights_v2, kinds_v2, route_ids_v2 = _build_adjacency(
        n_v2, edge_map_v2
    )
    node_key_index_v2 = {node.node_key: node.idx for node in route_state_nodes}

    graph_v2_path = artifacts / f"graph_{version if version == 'v2' else 'v2'}_weekday.json"
    graph_v2_obj = {
        "version": "v2",
        "profile": "weekday_non_holiday",
        "nodes_count": n_v2,
        "physical_nodes_count": n,
        "onboard_nodes_count": n_v2 - n,
        "nodes_index": stop_to_idx_json,
        "node_key_index": node_key_index_v2,
        "adj_offsets": offsets_v2,
        "adj_targets": targets_v2,
        "adj_weights_s": weights_v2,
        "edge_kind": kinds_v2,
        "edge_route_id": route_ids_v2,
        "route_labels": route_labels,
        "edge_kind_legend": {
            str(EDGE_KIND_V2["ride"]): "ride",
            str(EDGE_KIND_V2["boarding"]): "boarding",
            str(EDGE_KIND_V2["alight"]): "alight",
            str(EDGE_KIND_V2["transfer_pathway"]): "transfer_pathway",
            str(EDGE_KIND_V2["transfer_gtfs"]): "transfer_gtfs",
            str(EDGE_KIND_V2["transfer_fallback"]): "transfer_fallback",
        },
    }
    graph_v2_path.write_text(json.dumps(graph_v2_obj), encoding="utf-8")

    nodes_v2_out = artifacts / f"nodes_{version if version == 'v2' else 'v2'}.csv"
    with nodes_v2_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "node_idx",
                "node_kind",
                "node_key",
                "stop_id",
                "stop_name",
                "parent_station",
                "lat",
                "lon",
                "location_type",
                "is_rail_like",
                "physical_node_idx",
                "route_id",
                "direction_id",
            ]
        )
        for node in route_state_nodes:
            writer.writerow(
                [
                    node.idx,
                    node.node_kind,
                    node.node_key,
                    node.stop_id,
                    node.name,
                    node.parent_station,
                    f"{node.lat}",
                    f"{node.lon}",
                    node.location_type,
                    "1" if node.is_rail_like else "0",
                    "" if node.physical_node_idx is None else node.physical_node_idx,
                    node.route_id,
                    node.direction_id,
                ]
            )

    avg_out_degree = float(len(targets)) / float(n) if n else 0.0

    report = {
        "city": cfg.city_id,
        "nodes": n,
        "graph_edges": len(targets),
        "ride_edges_raw": ride_edges,
        "pathway_edges": len(pathway_edges),
        "transfer_edges": len(transfer_edges) + len(hub_transfer_edges),
        "transfer_edges_explicit": len(transfer_edges),
        "transfer_edges_hub_synth": len(hub_transfer_edges),
        "hub_transfer_base_s": hub_transfer_base_s,
        "transfer_min_floor_s": transfer_min_floor_s,
        "pathway_edges_floored": pathway_edges_floored,
        "transfer_edges_floored": transfer_edges_floored,
        "fallback_edges": len(fallback_edges),
        "avg_out_degree": avg_out_degree,
        "rail_like_nodes": sum(1 for flag in node_is_rail_like if flag),
        "edge_kind_counts": {
            "ride": edge_kind_counter.get(EDGE_KIND["ride"], 0),
            "transfer_pathway": edge_kind_counter.get(EDGE_KIND["transfer_pathway"], 0),
            "transfer_gtfs": edge_kind_counter.get(EDGE_KIND["transfer_gtfs"], 0),
            "transfer_fallback": edge_kind_counter.get(EDGE_KIND["transfer_fallback"], 0),
        },
        "stop_times_rows_used": stop_times_rows,
        "routes_used": len(route_types),
        "wait_stats": {
            "routes_with_wait": len(waits),
            "min_wait_s": min(waits.values()) if waits else 0,
            "max_wait_s": max(waits.values()) if waits else 0,
            "mean_wait_s": float(sum(waits.values())) / float(len(waits)) if waits else 0.0,
        },
        "trip_segment_stats": {
            "route_dirs_with_trip_segments": len(route_dir_trip_segments),
            "min_median_trip_segments": min(route_dir_trip_segments.values()) if route_dir_trip_segments else 0,
            "max_median_trip_segments": max(route_dir_trip_segments.values()) if route_dir_trip_segments else 0,
            "mean_median_trip_segments": (
                float(sum(route_dir_trip_segments.values())) / float(len(route_dir_trip_segments))
                if route_dir_trip_segments
                else 0.0
            ),
        },
    }

    report_v2 = {
        "city": cfg.city_id,
        "version": "v2",
        "nodes": n_v2,
        "physical_nodes": n,
        "onboard_nodes": n_v2 - n,
        "graph_edges": len(targets_v2),
        "ride_edges_raw": ride_edges_v2,
        "boarding_edges": edge_kind_counter_v2.get(EDGE_KIND_V2["boarding"], 0),
        "alight_edges": edge_kind_counter_v2.get(EDGE_KIND_V2["alight"], 0),
        "edge_kind_counts": {
            "ride": edge_kind_counter_v2.get(EDGE_KIND_V2["ride"], 0),
            "boarding": edge_kind_counter_v2.get(EDGE_KIND_V2["boarding"], 0),
            "alight": edge_kind_counter_v2.get(EDGE_KIND_V2["alight"], 0),
            "transfer_pathway": edge_kind_counter_v2.get(EDGE_KIND_V2["transfer_pathway"], 0),
            "transfer_gtfs": edge_kind_counter_v2.get(EDGE_KIND_V2["transfer_gtfs"], 0),
            "transfer_fallback": edge_kind_counter_v2.get(EDGE_KIND_V2["transfer_fallback"], 0),
        },
        "wait_stats": report["wait_stats"],
    }
    if version == "v2":
        (artifacts / f"graph_report_{version}.json").write_text(
            json.dumps(report_v2, indent=2, sort_keys=True), encoding="utf-8"
        )
        return report_v2

    (artifacts / f"graph_report_{version}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    (artifacts / "graph_report_v2.json").write_text(
        json.dumps(report_v2, indent=2, sort_keys=True), encoding="utf-8"
    )

    return report
