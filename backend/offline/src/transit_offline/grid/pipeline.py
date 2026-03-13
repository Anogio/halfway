from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from transit_offline.common.artifacts import GRID_ARTIFACT_PATTERNS, archive_existing_artifacts
from transit_offline.common.config import AppConfig, ensure_dirs, load_config
from transit_shared.geo import bucket_key
from transit_shared.seed_selection import build_nearest_node_index, resolve_access_candidates


@dataclass(frozen=True)
class Node:
    idx: int
    stop_id: str
    lat: float
    lon: float
    is_rail_like: bool = False


def _read_nodes(nodes_csv: Path) -> list[Node]:
    nodes: list[Node] = []
    with nodes_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            node_kind = (row.get("node_kind") or "physical").strip() or "physical"
            if node_kind != "physical":
                continue
            nodes.append(
                Node(
                    idx=int(row["node_idx"]),
                    stop_id=row["stop_id"],
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    is_rail_like=row.get("is_rail_like", "0") == "1",
                )
            )
    return nodes


def _frange(start: float, stop: float, step: float):
    value = start
    while value <= stop + 1e-12:
        yield value
        value += step

@dataclass
class _ProgressBar:
    total: int
    label: str
    width: int = 28

    def __post_init__(self) -> None:
        self._enabled = self.total > 0 and sys.stderr.isatty()
        self._last_render_at = 0.0
        self._last_completed = -1

    def update(self, completed: int) -> None:
        if not self._enabled or completed == self._last_completed:
            return
        now = time.monotonic()
        if completed < self.total and (now - self._last_render_at) < 0.1:
            return
        ratio = min(1.0, max(0.0, completed / self.total))
        filled = int(round(self.width * ratio))
        bar = "#" * filled + "-" * max(0, self.width - filled)
        sys.stderr.write(
            f"\r{self.label} [{bar}] {ratio * 100:5.1f}% ({completed}/{self.total})"
        )
        sys.stderr.flush()
        self._last_render_at = now
        self._last_completed = completed

    def finish(self) -> None:
        if not self._enabled:
            return
        self.update(self.total)
        sys.stderr.write("\n")
        sys.stderr.flush()


def run_build_grid(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    ensure_dirs(cfg)

    version = cfg.city.artifact_version
    artifacts = cfg.paths.offline_artifacts_dir

    nodes = _read_nodes(artifacts / f"nodes_{version}.csv")
    if not nodes:
        raise RuntimeError("No nodes available. Run build-graph first.")

    cell_size_m = cfg.settings.grid.cell_size_m
    configured_candidate_radius_m = cfg.settings.search.grid_candidate_radius_m
    configured_max_candidates = cfg.settings.grid.max_candidates_per_cell
    selection_radius_m = cfg.settings.search.first_mile_radius_m
    selection_fallback_k = cfg.settings.search.first_mile_fallback_k
    selection_limit = cfg.settings.runtime.max_seed_nodes
    walk_speed = cfg.settings.weights.walk_speed_mps

    if cfg.city.scope.use_bbox:
        min_lon, min_lat, max_lon, max_lat = cfg.city.scope.bbox
    else:
        min_lat = min(n.lat for n in nodes)
        max_lat = max(n.lat for n in nodes)
        min_lon = min(n.lon for n in nodes)
        max_lon = max(n.lon for n in nodes)

    mid_lat = (min_lat + max_lat) / 2.0
    lat_step = cell_size_m / 111_320.0
    lon_step = cell_size_m / (111_320.0 * max(math.cos(math.radians(mid_lat)), 0.2))
    lat_values = list(_frange(min_lat, max_lat, lat_step))
    lon_values = list(_frange(min_lon, max_lon, lon_step))
    progress = _ProgressBar(total=len(lat_values) * len(lon_values), label=f"build-grid {cfg.city_id}")

    by_bucket: dict[tuple[int, int], list[int]] = defaultdict(list)
    node_coords: dict[int, tuple[float, float]] = {}
    for node in nodes:
        by_bucket[bucket_key(node.lat, node.lon, selection_radius_m)].append(node.idx)
        node_coords[node.idx] = (node.lat, node.lon)
    nearest_index = build_nearest_node_index(node_coords)
    rail_node_coords = {node.idx: (node.lat, node.lon) for node in nodes if node.is_rail_like}
    rail_node_ids = frozenset(rail_node_coords)
    rail_nearest_index = build_nearest_node_index(rail_node_coords) if rail_node_coords else None

    archive_existing_artifacts(artifacts, patterns=GRID_ARTIFACT_PATTERNS)

    cells_path = artifacts / f"grid_cells_{version}.csv"
    links_path = artifacts / f"grid_links_{version}.csv"

    cell_count = 0
    in_scope_cells = 0
    linked_cells = 0
    link_count = 0

    with cells_path.open("w", newline="", encoding="utf-8") as cells_fh, links_path.open(
        "w", newline="", encoding="utf-8"
    ) as links_fh:
        cells_writer = csv.writer(cells_fh)
        links_writer = csv.writer(links_fh)
        cells_writer.writerow(["cell_id", "cell_lat", "cell_lon", "in_scope"])
        links_writer.writerow(["cell_id", "node_idx", "walk_seconds"])

        cell_id = 0
        for lat in lat_values:
            for lon in lon_values:
                in_scope_candidates = resolve_access_candidates(
                    lat=lat,
                    lon=lon,
                    search_radius_m=selection_radius_m,
                    bucket_radius_m=selection_radius_m,
                    bucket_index=by_bucket,
                    node_coords=node_coords,
                    walk_speed_mps=walk_speed,
                    limit=selection_limit,
                    fallback_k=selection_fallback_k,
                    allow_global_fallback=False,
                    force_inclusion_ids=rail_node_ids,
                    forced_k=selection_fallback_k,
                    allow_forced_global_search=False,
                    nearest_index=nearest_index,
                )
                selected = resolve_access_candidates(
                    lat=lat,
                    lon=lon,
                    search_radius_m=selection_radius_m,
                    bucket_radius_m=selection_radius_m,
                    bucket_index=by_bucket,
                    node_coords=node_coords,
                    walk_speed_mps=walk_speed,
                    limit=selection_limit,
                    fallback_k=selection_fallback_k,
                    allow_global_fallback=True,
                    force_inclusion_ids=rail_node_ids,
                    forced_k=selection_fallback_k,
                    nearest_index=nearest_index,
                    forced_nearest_index=rail_nearest_index,
                )
                in_scope = 1 if in_scope_candidates else 0
                cells_writer.writerow([cell_id, f"{lat:.7f}", f"{lon:.7f}", in_scope])
                if in_scope:
                    in_scope_cells += 1
                if selected:
                    linked_cells += 1
                    for idx, walk_seconds in selected:
                        links_writer.writerow([cell_id, idx, walk_seconds])
                        link_count += 1

                cell_count += 1
                cell_id += 1
                progress.update(cell_count)

    progress.finish()

    coverage = float(linked_cells) / float(cell_count) if cell_count else 0.0
    report = {
        "city": cfg.city_id,
        "cells": cell_count,
        "in_scope_cells": in_scope_cells,
        "linked_cells": linked_cells,
        "links": link_count,
        "coverage_ratio": coverage,
        "in_scope_ratio": (float(in_scope_cells) / float(cell_count) if cell_count else 0.0),
        "cell_size_m": cell_size_m,
        "selection_policy": "runtime_aligned",
        "access_radius_m": selection_radius_m,
        "access_fallback_k": selection_fallback_k,
        "access_limit": selection_limit,
        "configured_grid_candidate_radius_m": configured_candidate_radius_m,
        "configured_max_candidates_per_cell": configured_max_candidates,
    }

    (artifacts / f"grid_report_{version}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )

    return report
