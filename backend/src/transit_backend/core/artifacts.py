from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Node:
    idx: int
    stop_id: str
    name: str
    lat: float
    lon: float
    is_rail_like: bool = False
    node_kind: str = "physical"
    node_key: str = ""
    physical_node_idx: int | None = None
    route_id: str = ""
    direction_id: str = ""


@dataclass(frozen=True)
class GridCell:
    cell_id: int
    lat: float
    lon: float
    in_scope: bool


@dataclass
class RuntimeData:
    version: str
    profile: str
    nodes: list[Node]
    offsets: list[int]
    targets: list[int]
    weights: list[int]
    grid_cells: dict[int, GridCell]
    grid_links: dict[int, list[tuple[int, int]]]
    metadata: dict[str, object]
    edge_kinds: list[int] = field(default_factory=list)
    edge_kind_legend: dict[int, str] = field(default_factory=dict)
    edge_route_ids: list[str] = field(default_factory=list)
    route_labels: dict[str, str] = field(default_factory=dict)
    node_key_index: dict[str, int] = field(default_factory=dict)
    reverse_offsets: list[int] = field(default_factory=list)
    reverse_targets: list[int] = field(default_factory=list)
    reverse_weights: list[int] = field(default_factory=list)
    reverse_edge_to_forward: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if (
            len(self.reverse_offsets) == len(self.offsets)
            and len(self.reverse_targets) == len(self.targets)
            and len(self.reverse_weights) == len(self.weights)
            and len(self.reverse_edge_to_forward) == len(self.targets)
        ):
            return
        (
            self.reverse_offsets,
            self.reverse_targets,
            self.reverse_weights,
            self.reverse_edge_to_forward,
        ) = build_reverse_graph(self.offsets, self.targets, self.weights)

    def is_physical_node(self, node_idx: int) -> bool:
        return 0 <= node_idx < len(self.nodes) and self.nodes[node_idx].node_kind == "physical"

    def physical_node_idx_for(self, node_idx: int) -> int:
        if not (0 <= node_idx < len(self.nodes)):
            return node_idx
        node = self.nodes[node_idx]
        return node.idx if node.node_kind == "physical" else int(node.physical_node_idx if node.physical_node_idx is not None else node.idx)


def build_reverse_graph(
    offsets: list[int],
    targets: list[int],
    weights: list[int],
) -> tuple[list[int], list[int], list[int], list[int]]:
    node_count = max(0, len(offsets) - 1)
    edge_count = len(targets)
    incoming_counts = [0] * node_count
    for target in targets:
        if 0 <= target < node_count:
            incoming_counts[target] += 1

    reverse_offsets = [0] * (node_count + 1)
    for node_idx in range(node_count):
        reverse_offsets[node_idx + 1] = reverse_offsets[node_idx] + incoming_counts[node_idx]

    reverse_targets = [0] * edge_count
    reverse_weights = [0] * edge_count
    reverse_edge_to_forward = [0] * edge_count
    next_positions = list(reverse_offsets[:-1])

    for source_idx in range(node_count):
        start = offsets[source_idx]
        end = offsets[source_idx + 1]
        for edge_idx in range(start, end):
            target_idx = targets[edge_idx]
            if not (0 <= target_idx < node_count):
                continue
            insert_at = next_positions[target_idx]
            reverse_targets[insert_at] = source_idx
            reverse_weights[insert_at] = weights[edge_idx]
            reverse_edge_to_forward[insert_at] = edge_idx
            next_positions[target_idx] += 1

    return reverse_offsets, reverse_targets, reverse_weights, reverse_edge_to_forward


def load_runtime_data(artifacts_dir: Path, version: str) -> RuntimeData:
    graph_path = artifacts_dir / f"graph_{version}_weekday.json"
    nodes_path = artifacts_dir / f"nodes_{version}.csv"
    grid_cells_path = artifacts_dir / f"grid_cells_{version}.csv"
    grid_links_path = artifacts_dir / f"grid_links_{version}.csv"
    manifest_path = artifacts_dir / f"manifest_{version}.json"

    if not graph_path.exists():
        raise FileNotFoundError(f"Missing graph artifact: {graph_path}")
    if not nodes_path.exists():
        raise FileNotFoundError(f"Missing nodes artifact: {nodes_path}")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    nodes: list[Node] = []
    with nodes_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            nodes.append(
                Node(
                    idx=int(row["node_idx"]),
                    stop_id=row["stop_id"],
                    name=row.get("stop_name", ""),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    is_rail_like=row.get("is_rail_like", "0") == "1",
                    node_kind=(row.get("node_kind") or "physical").strip() or "physical",
                    node_key=(row.get("node_key") or row["stop_id"]).strip() or row["stop_id"],
                    physical_node_idx=(
                        int(row["physical_node_idx"])
                        if (row.get("physical_node_idx") or "").strip()
                        else None
                    ),
                    route_id=(row.get("route_id") or "").strip(),
                    direction_id=(row.get("direction_id") or "").strip(),
                )
            )
    nodes.sort(key=lambda n: n.idx)

    grid_cells: dict[int, GridCell] = {}
    if grid_cells_path.exists():
        with grid_cells_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cid = int(row["cell_id"])
                grid_cells[cid] = GridCell(
                    cell_id=cid,
                    lat=float(row["cell_lat"]),
                    lon=float(row["cell_lon"]),
                    in_scope=(row["in_scope"] == "1"),
                )

    grid_links: dict[int, list[tuple[int, int]]] = defaultdict(list)
    if grid_links_path.exists():
        with grid_links_path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                grid_links[int(row["cell_id"])].append((int(row["node_idx"]), int(row["walk_seconds"])))

    metadata = {}
    if manifest_path.exists():
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))

    edge_kinds_raw = graph.get("edge_kind", [])
    edge_kinds = [int(v) for v in edge_kinds_raw] if len(edge_kinds_raw) == len(graph["adj_targets"]) else []

    legend_raw = graph.get("edge_kind_legend", {})
    edge_kind_legend: dict[int, str] = {}
    if isinstance(legend_raw, dict):
        for key, value in legend_raw.items():
            try:
                edge_kind_legend[int(key)] = str(value)
            except (TypeError, ValueError):
                continue

    edge_route_ids_raw = graph.get("edge_route_id", [])
    edge_route_ids = (
        [str(v) for v in edge_route_ids_raw]
        if len(edge_route_ids_raw) == len(graph["adj_targets"])
        else []
    )
    route_labels_raw = graph.get("route_labels", {})
    route_labels = (
        {str(key): str(value) for key, value in route_labels_raw.items()}
        if isinstance(route_labels_raw, dict)
        else {}
    )
    node_key_index_raw = graph.get("node_key_index", {})
    node_key_index = (
        {str(key): int(value) for key, value in node_key_index_raw.items()}
        if isinstance(node_key_index_raw, dict)
        else {}
    )

    return RuntimeData(
        version=graph.get("version", version),
        profile=graph.get("profile", "weekday_non_holiday"),
        nodes=nodes,
        offsets=graph["adj_offsets"],
        targets=graph["adj_targets"],
        weights=graph["adj_weights_s"],
        edge_kinds=edge_kinds,
        edge_kind_legend=edge_kind_legend,
        edge_route_ids=edge_route_ids,
        route_labels=route_labels,
        node_key_index=node_key_index,
        grid_cells=grid_cells,
        grid_links=dict(grid_links),
        metadata=metadata,
    )
