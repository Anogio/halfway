from __future__ import annotations

import csv
from pathlib import Path
from typing import Protocol


class RouteLabelFormatter(Protocol):
    def __call__(
        self,
        *,
        route_id: str,
        short_name: str,
        long_name: str,
        route_type: str,
    ) -> str: ...


def read_stop_parent_map(gtfs_dir: Path) -> dict[str, str]:
    stop_parent: dict[str, str] = {}
    with (gtfs_dir / "stops.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            stop_parent[row["stop_id"].strip()] = (row.get("parent_station") or "").strip()
    return stop_parent


def read_trips(trips_csv: Path) -> dict[str, tuple[str, str]]:
    trip_map: dict[str, tuple[str, str]] = {}
    with trips_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            trip_map[row["trip_id"]] = (row["route_id"], row["direction_id"])
    return trip_map


def read_route_types(routes_csv: Path) -> dict[str, str]:
    route_types: dict[str, str] = {}
    with routes_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            route_types[row["route_id"]] = row["route_type"]
    return route_types


def _default_route_label(route_id: str, short_name: str, long_name: str) -> str:
    if short_name and long_name and short_name != long_name:
        return f"{short_name} - {long_name}"
    if short_name:
        return short_name
    if long_name:
        return long_name
    return route_id


def read_route_labels(
    routes_csv: Path,
    selected_route_ids: set[str],
    *,
    formatter: RouteLabelFormatter | None = None,
) -> dict[str, str]:
    labels: dict[str, str] = {}
    with routes_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            route_id = (row.get("route_id") or "").strip()
            if route_id not in selected_route_ids:
                continue
            short_name = (row.get("route_short_name") or "").strip()
            long_name = (row.get("route_long_name") or "").strip()
            route_type = (row.get("route_type") or "").strip()
            if formatter is None:
                labels[route_id] = _default_route_label(route_id, short_name, long_name)
                continue

            custom = formatter(
                route_id=route_id,
                short_name=short_name,
                long_name=long_name,
                route_type=route_type,
            ).strip()
            if custom:
                labels[route_id] = custom
            else:
                labels[route_id] = _default_route_label(route_id, short_name, long_name)
    return labels


def parse_pathways(
    gtfs_dir: Path,
    stop_to_idx: dict[str, int],
    station_to_nodes: dict[str, list[int]],
    stop_parent: dict[str, str],
    walk_speed_mps: float,
) -> dict[tuple[int, int], int]:
    edges: dict[tuple[int, int], int] = {}

    def resolve(stop_id: str) -> list[int]:
        if stop_id in stop_to_idx:
            return [stop_to_idx[stop_id]]
        parent = stop_parent.get(stop_id, "")
        if parent and parent in station_to_nodes:
            return station_to_nodes[parent]
        return station_to_nodes.get(stop_id, [])

    path = gtfs_dir / "pathways.txt"
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            from_stop = row.get("from_stop_id", "").strip()
            to_stop = row.get("to_stop_id", "").strip()
            from_nodes = resolve(from_stop)
            to_nodes = resolve(to_stop)
            if not from_nodes or not to_nodes:
                continue

            traversal = (row.get("traversal_time") or "").strip()
            length = (row.get("length") or "").strip()
            if traversal:
                time_s = int(float(traversal))
            elif length:
                time_s = int(round(float(length) / walk_speed_mps))
            else:
                continue

            if time_s < 0:
                continue

            for a in from_nodes:
                for b in to_nodes:
                    if a == b:
                        continue
                    edges[(a, b)] = min(edges.get((a, b), time_s), time_s)
                    if (row.get("is_bidirectional") or "0").strip() == "1":
                        edges[(b, a)] = min(edges.get((b, a), time_s), time_s)

    return edges


def parse_transfers(gtfs_dir: Path, stop_to_idx: dict[str, int]) -> dict[tuple[int, int], int]:
    edges: dict[tuple[int, int], int] = {}
    path = gtfs_dir / "transfers.txt"
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            from_stop = row.get("from_stop_id", "").strip()
            to_stop = row.get("to_stop_id", "").strip()
            if from_stop not in stop_to_idx or to_stop not in stop_to_idx:
                continue
            time_s = int(float((row.get("min_transfer_time") or "0").strip() or "0"))
            if time_s < 0:
                continue
            key = (stop_to_idx[from_stop], stop_to_idx[to_stop])
            edges[key] = min(edges.get(key, time_s), time_s)
    return edges
