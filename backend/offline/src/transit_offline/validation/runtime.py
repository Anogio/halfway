from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from transit_shared.geo import bucket_key
from transit_shared.routing import dijkstra_min_times
from transit_shared.seed_selection import (
    NearestNodeIndex,
    build_nearest_node_index,
    nearest_k_seed_candidates,
    resolve_access_candidates as shared_resolve_access_candidates,
)


@dataclass(frozen=True)
class Node:
    idx: int
    stop_id: str
    lat: float
    lon: float
    name: str
    is_rail_like: bool = False


def read_nodes(path: Path) -> list[Node]:
    nodes = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            node_kind = (row.get("node_kind") or "physical").strip() or "physical"
            if node_kind != "physical":
                continue
            nodes.append(
                Node(
                    idx=int(row["node_idx"]),
                    stop_id=row.get("stop_id", ""),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    name=row.get("stop_name", ""),
                    is_rail_like=row.get("is_rail_like", "0") == "1",
                )
            )
    nodes.sort(key=lambda n: n.idx)
    return nodes


def read_graph(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_bucket_index(nodes: list[Node], radius_m: float) -> dict[tuple[int, int], list[int]]:
    index: dict[tuple[int, int], list[int]] = defaultdict(list)
    for node in nodes:
        index[bucket_key(node.lat, node.lon, radius_m)].append(node.idx)
    return index


def build_nearest_index(nodes: list[Node]) -> NearestNodeIndex:
    return build_nearest_node_index({node.idx: (node.lat, node.lon) for node in nodes})


def nearby_nodes(
    lat: float,
    lon: float,
    radius_m: float,
    walk_speed_mps: float,
    bucket_index: dict[tuple[int, int], list[int]],
    node_coords: dict[int, tuple[float, float]],
    limit: int,
) -> list[tuple[int, int]]:
    return shared_resolve_access_candidates(
        lat=lat,
        lon=lon,
        search_radius_m=radius_m,
        bucket_radius_m=radius_m,
        bucket_index=bucket_index,
        node_coords=node_coords,
        walk_speed_mps=walk_speed_mps,
        limit=limit,
        fallback_k=0,
        allow_global_fallback=False,
    )


def nearest_k(
    lat: float,
    lon: float,
    node_coords: dict[int, tuple[float, float]],
    walk_speed_mps: float,
    k: int,
    nearest_index: NearestNodeIndex | None = None,
) -> list[tuple[int, int]]:
    return nearest_k_seed_candidates(
        lat=lat,
        lon=lon,
        node_coords=node_coords,
        walk_speed_mps=walk_speed_mps,
        k=k,
        nearest_index=nearest_index,
    )


def resolve_access_candidates(
    lat: float,
    lon: float,
    radius_m: float,
    fallback_k: int,
    limit: int,
    walk_speed_mps: float,
    bucket_index: dict[tuple[int, int], list[int]],
    node_coords: dict[int, tuple[float, float]],
    nearest_index: NearestNodeIndex,
    rail_node_ids: frozenset[int],
    rail_nearest_index: NearestNodeIndex | None,
) -> list[tuple[int, int]]:
    return shared_resolve_access_candidates(
        lat=lat,
        lon=lon,
        search_radius_m=radius_m,
        bucket_radius_m=radius_m,
        bucket_index=bucket_index,
        node_coords=node_coords,
        walk_speed_mps=walk_speed_mps,
        limit=limit,
        fallback_k=max(1, fallback_k),
        allow_global_fallback=True,
        force_inclusion_ids=rail_node_ids,
        forced_k=max(1, fallback_k),
        nearest_index=nearest_index,
        forced_nearest_index=rail_nearest_index,
    )


def resolve_seeds(
    lat: float,
    lon: float,
    radius_m: float,
    fallback_k: int,
    max_seed_nodes: int,
    walk_speed_mps: float,
    bucket_index: dict[tuple[int, int], list[int]],
    node_coords: dict[int, tuple[float, float]],
    nearest_index: NearestNodeIndex,
    rail_node_ids: frozenset[int],
    rail_nearest_index: NearestNodeIndex | None,
) -> list[tuple[int, int]]:
    return resolve_access_candidates(
        lat,
        lon,
        radius_m,
        fallback_k,
        max_seed_nodes,
        walk_speed_mps,
        bucket_index,
        node_coords,
        nearest_index,
        rail_node_ids,
        rail_nearest_index,
    )


def dijkstra(
    offsets: list[int],
    targets: list[int],
    weights: list[int],
    seeds: list[tuple[int, int]],
    max_time_s: int,
) -> list[int]:
    return dijkstra_min_times(
        offsets=offsets,
        targets=targets,
        weights=weights,
        seeds=seeds,
        max_time_s=max_time_s,
    )


def load_grid_links(path: Path) -> dict[int, list[tuple[int, int]]]:
    links: dict[int, list[tuple[int, int]]] = defaultdict(list)
    if not path.exists():
        return links
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            links[int(row["cell_id"])].append((int(row["node_idx"]), int(row["walk_seconds"])))
    return links


def load_grid_cell_scope(path: Path) -> dict[int, bool]:
    scope: dict[int, bool] = {}
    if not path.exists():
        return scope
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            scope[int(row["cell_id"])] = row.get("in_scope", "0") == "1"
    return scope
