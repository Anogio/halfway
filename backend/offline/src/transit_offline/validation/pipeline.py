from __future__ import annotations

import json
import math
import time

from transit_offline.common.artifacts import VALIDATION_ARTIFACT_PATTERNS, archive_existing_artifacts
from transit_offline.common.config import AppConfig, load_config
from transit_offline.validation.runtime import (
    build_bucket_index,
    build_nearest_index,
    dijkstra,
    load_grid_links,
    read_graph,
    read_nodes,
    resolve_access_candidates,
    resolve_seeds,
)
from transit_shared.routing import INF


def run_validate(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    version = cfg.city.artifact_version
    artifacts = cfg.paths.offline_artifacts_dir

    nodes = read_nodes(artifacts / f"nodes_{version}.csv")
    graph = read_graph(artifacts / f"graph_{version}_weekday.json")

    offsets: list[int] = graph["adj_offsets"]
    targets: list[int] = graph["adj_targets"]
    weights: list[int] = graph["adj_weights_s"]

    first_mile_radius = cfg.settings.search.first_mile_radius_m
    max_seed_nodes = cfg.settings.runtime.max_seed_nodes
    walk_speed_mps = cfg.settings.weights.walk_speed_mps
    fallback_k = cfg.settings.search.first_mile_fallback_k
    max_time_s = cfg.settings.runtime.max_time_s
    mape_threshold = cfg.city.validation.mape_threshold
    range_tolerance_ratio = cfg.city.validation.range_tolerance_ratio
    perf_p95_threshold_ms = cfg.city.validation.performance_p95_ms_threshold

    bucket_index = build_bucket_index(nodes, first_mile_radius)
    nearest_index = build_nearest_index(nodes)
    rail_nodes = [node for node in nodes if node.is_rail_like]
    rail_node_ids = frozenset(node.idx for node in rail_nodes)
    rail_nearest_index = build_nearest_index(rail_nodes) if rail_nodes else None
    node_coords = {node.idx: (node.lat, node.lon) for node in nodes}

    od_results = []
    mape_terms = []
    failures = []

    for pair in cfg.city.validation.od_pairs:
        name = pair.name
        src_lat = pair.from_lat
        src_lon = pair.from_lon
        dst_lat = pair.to_lat
        dst_lon = pair.to_lon
        expected_min = pair.expected_min_s
        expected_max = pair.expected_max_s

        seeds = resolve_seeds(
            src_lat,
            src_lon,
            first_mile_radius,
            fallback_k,
            max_seed_nodes,
            walk_speed_mps,
            bucket_index,
            node_coords,
            nearest_index,
            rail_node_ids,
            rail_nearest_index,
        )

        dist = dijkstra(offsets, targets, weights, seeds, max_time_s=max_time_s)

        dst_candidates = resolve_access_candidates(
            dst_lat,
            dst_lon,
            first_mile_radius,
            fallback_k,
            max_seed_nodes,
            walk_speed_mps,
            bucket_index,
            node_coords,
            nearest_index,
            rail_node_ids,
            rail_nearest_index,
        )

        pred = INF
        for node_idx, walk_s in dst_candidates:
            cand = dist[node_idx] + walk_s
            if cand < pred:
                pred = cand

        expected_mid = (expected_min + expected_max) / 2.0
        if pred < expected_min:
            boundary_error = expected_min - pred
        elif pred > expected_max:
            boundary_error = pred - expected_max
        else:
            boundary_error = 0

        mape = boundary_error / expected_mid if expected_mid > 0 else 0.0
        mape_terms.append(mape)

        range_span = max(0, expected_max - expected_min)
        tolerance = int(round(range_span * range_tolerance_ratio))
        tol_min = max(0, expected_min - tolerance)
        tol_max = expected_max + tolerance
        ok = tol_min <= pred <= tol_max
        if not ok:
            failures.append(
                f"OD out of expected range: {name} predicted={pred}s "
                f"expected=[{expected_min},{expected_max}] tol=[{tol_min},{tol_max}]"
            )

        od_results.append(
            {
                "name": name,
                "predicted_s": int(pred),
                "expected_min_s": expected_min,
                "expected_max_s": expected_max,
                "in_expected_range": ok,
                "tolerance_min_s": tol_min,
                "tolerance_max_s": tol_max,
                "mape": mape,
            }
        )

    mape = float(sum(mape_terms) / len(mape_terms)) if mape_terms else 0.0
    if mape > mape_threshold:
        failures.append(f"MAPE too high: {mape:.4f} > {mape_threshold:.4f}")

    avg_out_degree = float(len(targets)) / float(len(nodes)) if nodes else 0.0
    if len(nodes) >= 10 and avg_out_degree < 1.0:
        failures.append("Graph out-degree too low")

    # Reachability sanity from configured city center based on grid links if present.
    origin_lat = cfg.city.scope.default_view[0]
    origin_lon = cfg.city.scope.default_view[1]
    seed_nodes = resolve_seeds(
        origin_lat,
        origin_lon,
        first_mile_radius,
        fallback_k,
        max_seed_nodes,
        walk_speed_mps,
        bucket_index,
        node_coords,
        nearest_index,
        rail_node_ids,
        rail_nearest_index,
    )

    dist_from_center = dijkstra(offsets, targets, weights, seed_nodes, max_time_s=max_time_s)
    links = load_grid_links(artifacts / f"grid_links_{version}.csv")
    max_in_scope_walk_s = int(round(first_mile_radius / walk_speed_mps)) if walk_speed_mps > 0 else 0

    reachable_cells = 0
    total_linked_cells = 0
    total_in_scope_cells = 0
    for cell_id, cell_links in links.items():
        total_linked_cells += 1
        if not cell_links:
            continue
        if min(walk_s for _, walk_s in cell_links) > max_in_scope_walk_s:
            continue
        total_in_scope_cells += 1
        best = INF
        for node_idx, walk_s in cell_links:
            best = min(best, dist_from_center[node_idx] + walk_s)
        if best < max_time_s:
            reachable_cells += 1

    reachability_ratio = (
        float(reachable_cells) / float(total_in_scope_cells) if total_in_scope_cells else 0.0
    )
    if total_in_scope_cells and reachability_ratio < 0.15:
        failures.append(
            f"Low reachability ratio from configured city center: {reachability_ratio:.3f}"
        )

    # Runtime performance sanity check on a small origin set.
    perf_origins = []
    seen = set()
    for pair in cfg.city.validation.od_pairs:
        origin = (pair.from_lat, pair.from_lon)
        if origin not in seen:
            perf_origins.append(origin)
            seen.add(origin)
    center_origin = (origin_lat, origin_lon)
    if center_origin not in seen:
        perf_origins.append(center_origin)
        seen.add(center_origin)

    perf_samples_ms: list[float] = []
    for lat, lon in perf_origins[:6]:
        start_ts = time.perf_counter()
        seeds = resolve_seeds(
            lat,
            lon,
            first_mile_radius,
            fallback_k,
            max_seed_nodes,
            walk_speed_mps,
            bucket_index,
            node_coords,
            nearest_index,
            rail_node_ids,
            rail_nearest_index,
        )
        dist = dijkstra(offsets, targets, weights, seeds, max_time_s=max_time_s)

        if links:
            # Approximate full query path by scanning grid links.
            reachable = 0
            for _, cell_links in links.items():
                best = INF
                for node_idx, walk_s in cell_links:
                    best = min(best, dist[node_idx] + walk_s)
                if best < max_time_s:
                    reachable += 1
            _ = reachable

        elapsed_ms = (time.perf_counter() - start_ts) * 1000.0
        perf_samples_ms.append(elapsed_ms)

    perf_samples_ms.sort()
    if perf_samples_ms:
        idx_95 = max(0, min(len(perf_samples_ms) - 1, math.ceil(0.95 * len(perf_samples_ms)) - 1))
        perf_p95_ms = perf_samples_ms[idx_95]
        perf_p50_ms = perf_samples_ms[len(perf_samples_ms) // 2]
        perf_max_ms = perf_samples_ms[-1]
    else:
        perf_p95_ms = 0.0
        perf_p50_ms = 0.0
        perf_max_ms = 0.0

    if perf_p95_ms > perf_p95_threshold_ms:
        failures.append(
            f"Performance p95 too high: {perf_p95_ms:.2f}ms > {perf_p95_threshold_ms:.2f}ms"
        )

    report = {
        "city": cfg.city_id,
        "version": version,
        "profile": "weekday_non_holiday",
        "od_results": od_results,
        "metrics": {
            "mape": mape,
            "mape_threshold": mape_threshold,
            "range_tolerance_ratio": range_tolerance_ratio,
            "performance_samples_ms": perf_samples_ms,
            "performance_p50_ms": perf_p50_ms,
            "performance_p95_ms": perf_p95_ms,
            "performance_max_ms": perf_max_ms,
            "performance_p95_threshold_ms": perf_p95_threshold_ms,
            "avg_out_degree": avg_out_degree,
            "grid_reachability_ratio_from_city_center": reachability_ratio,
            "grid_linked_cells": total_linked_cells,
            "grid_in_scope_cells": total_in_scope_cells,
        },
        "failures": failures,
        "ok": len(failures) == 0,
    }

    archive_existing_artifacts(artifacts, patterns=VALIDATION_ARTIFACT_PATTERNS)

    report_path = artifacts / f"validation_{version}.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if failures:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(failures))

    return report
