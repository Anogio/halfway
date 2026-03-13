from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from typing import AbstractSet, Callable, Mapping, Sequence

from transit_shared.geo import bucket_key, haversine_m, neighbor_bucket_keys

IdxPredicate = Callable[[int], bool]


@dataclass(frozen=True)
class NearestNodeIndex:
    sorted_lats: tuple[float, ...]
    sorted_ids: tuple[int, ...]


def build_nearest_node_index(
    node_coords: Mapping[int, tuple[float, float]],
) -> NearestNodeIndex:
    rows = sorted((lat, idx) for idx, (lat, _lon) in node_coords.items())
    return NearestNodeIndex(
        sorted_lats=tuple(lat for lat, _ in rows),
        sorted_ids=tuple(idx for _, idx in rows),
    )


def candidate_distances_within_radius(
    *,
    lat: float,
    lon: float,
    search_radius_m: float,
    bucket_radius_m: float,
    bucket_index: Mapping[tuple[int, int], Sequence[int]],
    node_coords: Mapping[int, tuple[float, float]],
) -> list[tuple[float, int]]:
    key = bucket_key(lat, lon, bucket_radius_m)
    candidates: list[tuple[float, int]] = []
    for bkey in neighbor_bucket_keys(key, rings=1):
        for idx in bucket_index.get(bkey, ()):
            coords = node_coords.get(idx)
            if coords is None:
                continue
            node_lat, node_lon = coords
            dist = haversine_m(lat, lon, node_lat, node_lon)
            if dist <= search_radius_m:
                candidates.append((dist, idx))
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates


def nearest_k_candidate_distances(
    *,
    lat: float,
    lon: float,
    node_coords: Mapping[int, tuple[float, float]],
    k: int,
    predicate: IdxPredicate | None = None,
    nearest_index: NearestNodeIndex | None = None,
) -> list[tuple[float, int]]:
    if k <= 0:
        return []
    if nearest_index is not None and nearest_index.sorted_ids:
        return _nearest_k_candidate_distances_indexed(
            lat=lat,
            lon=lon,
            node_coords=node_coords,
            k=k,
            predicate=predicate,
            nearest_index=nearest_index,
        )
    candidates: list[tuple[float, int]] = []
    for idx, (node_lat, node_lon) in node_coords.items():
        if predicate is not None and not predicate(idx):
            continue
        dist = haversine_m(lat, lon, node_lat, node_lon)
        candidates.append((dist, idx))
    candidates.sort(key=lambda row: (row[0], row[1]))
    return candidates[:k]


def _nearest_k_candidate_distances_indexed(
    *,
    lat: float,
    lon: float,
    node_coords: Mapping[int, tuple[float, float]],
    k: int,
    predicate: IdxPredicate | None,
    nearest_index: NearestNodeIndex,
) -> list[tuple[float, int]]:
    best: list[tuple[float, int]] = []
    sorted_lats = nearest_index.sorted_lats
    sorted_ids = nearest_index.sorted_ids
    pos = bisect_left(sorted_lats, lat)
    left = pos - 1
    right = pos
    inf = float("inf")

    while left >= 0 or right < len(sorted_ids):
        left_gap = abs(lat - sorted_lats[left]) * 111_320.0 if left >= 0 else inf
        right_gap = abs(sorted_lats[right] - lat) * 111_320.0 if right < len(sorted_ids) else inf
        min_gap = min(left_gap, right_gap)
        if len(best) >= k and min_gap > best[-1][0]:
            break

        take_left = left_gap <= right_gap
        pos_idx = left if take_left else right
        if take_left:
            left -= 1
        else:
            right += 1

        idx = sorted_ids[pos_idx]
        if predicate is not None and not predicate(idx):
            continue
        node_lat, node_lon = node_coords[idx]
        dist = haversine_m(lat, lon, node_lat, node_lon)
        best.append((dist, idx))
        best.sort(key=lambda row: (row[0], row[1]))
        if len(best) > k:
            del best[k:]

    return best


def merge_seed_candidates(
    base_candidates: Sequence[tuple[int, int]],
    forced_candidates: Sequence[tuple[int, int]],
    *,
    cap: int,
) -> list[tuple[int, int]]:
    if cap <= 0:
        return []
    if not forced_candidates:
        return sorted(base_candidates, key=lambda row: (row[1], row[0]))[:cap]

    best_cost_by_idx: dict[int, int] = {}
    for idx, cost in list(base_candidates) + list(forced_candidates):
        prev = best_cost_by_idx.get(idx)
        if prev is None or cost < prev:
            best_cost_by_idx[idx] = cost

    forced_ids = {idx for idx, _ in forced_candidates}
    forced = sorted(
        ((idx, best_cost_by_idx[idx]) for idx in forced_ids if idx in best_cost_by_idx),
        key=lambda row: (row[1], row[0]),
    )
    if len(forced) >= cap:
        return forced[:cap]

    remaining = sorted(
        ((idx, cost) for idx, cost in best_cost_by_idx.items() if idx not in forced_ids),
        key=lambda row: (row[1], row[0]),
    )
    return forced + remaining[: max(0, cap - len(forced))]


def seed_candidates_within_radius(
    *,
    lat: float,
    lon: float,
    search_radius_m: float,
    bucket_radius_m: float,
    bucket_index: Mapping[tuple[int, int], Sequence[int]],
    node_coords: Mapping[int, tuple[float, float]],
    walk_speed_mps: float,
    limit: int,
) -> list[tuple[int, int]]:
    distances = candidate_distances_within_radius(
        lat=lat,
        lon=lon,
        search_radius_m=search_radius_m,
        bucket_radius_m=bucket_radius_m,
        bucket_index=bucket_index,
        node_coords=node_coords,
    )
    return [
        (idx, int(round(dist / walk_speed_mps)))
        for dist, idx in distances[: max(0, limit)]
    ]


def nearest_k_seed_candidates(
    *,
    lat: float,
    lon: float,
    node_coords: Mapping[int, tuple[float, float]],
    walk_speed_mps: float,
    k: int,
    predicate: IdxPredicate | None = None,
    nearest_index: NearestNodeIndex | None = None,
) -> list[tuple[int, int]]:
    distances = nearest_k_candidate_distances(
        lat=lat,
        lon=lon,
        node_coords=node_coords,
        k=k,
        predicate=predicate,
        nearest_index=nearest_index,
    )
    return [(idx, int(round(dist / walk_speed_mps))) for dist, idx in distances]


def resolve_access_candidates(
    *,
    lat: float,
    lon: float,
    search_radius_m: float,
    bucket_radius_m: float,
    bucket_index: Mapping[tuple[int, int], Sequence[int]],
    node_coords: Mapping[int, tuple[float, float]],
    walk_speed_mps: float,
    limit: int,
    fallback_k: int = 0,
    allow_global_fallback: bool = False,
    force_inclusion_ids: AbstractSet[int] | None = None,
    force_inclusion_predicate: IdxPredicate | None = None,
    forced_k: int = 0,
    allow_forced_global_search: bool = True,
    nearest_index: NearestNodeIndex | None = None,
    forced_nearest_index: NearestNodeIndex | None = None,
) -> list[tuple[int, int]]:
    cap = max(0, limit)
    if cap <= 0:
        return []

    selected = seed_candidates_within_radius(
        lat=lat,
        lon=lon,
        search_radius_m=search_radius_m,
        bucket_radius_m=bucket_radius_m,
        bucket_index=bucket_index,
        node_coords=node_coords,
        walk_speed_mps=walk_speed_mps,
        limit=cap,
    )

    effective_fallback_k = max(1, fallback_k) if fallback_k > 0 else 0
    if not selected and allow_global_fallback and effective_fallback_k > 0:
        selected = nearest_k_seed_candidates(
            lat=lat,
            lon=lon,
            node_coords=node_coords,
            walk_speed_mps=walk_speed_mps,
            k=effective_fallback_k,
            nearest_index=nearest_index,
        )

    if (
        (force_inclusion_ids is None and force_inclusion_predicate is None)
        or not selected
        or any(
            (idx in force_inclusion_ids)
            if force_inclusion_ids is not None
            else bool(force_inclusion_predicate and force_inclusion_predicate(idx))
            for idx, _ in selected
        )
    ):
        return selected

    effective_forced_k = max(1, forced_k) if forced_k > 0 else effective_fallback_k
    if effective_forced_k <= 0:
        effective_forced_k = 1

    if allow_forced_global_search:
        forced_predicate = force_inclusion_predicate
        forced_index = nearest_index
        if forced_nearest_index is not None:
            forced_predicate = None
            forced_index = forced_nearest_index
        elif force_inclusion_ids is not None:
            forced_predicate = force_inclusion_ids.__contains__
        forced = nearest_k_seed_candidates(
            lat=lat,
            lon=lon,
            node_coords=node_coords,
            walk_speed_mps=walk_speed_mps,
            k=effective_forced_k,
            predicate=forced_predicate,
            nearest_index=forced_index,
        )
    else:
        selected_ids = {idx for idx, _ in selected}
        forced = [
            (idx, int(round(dist / walk_speed_mps)))
            for dist, idx in candidate_distances_within_radius(
                lat=lat,
                lon=lon,
                search_radius_m=search_radius_m,
                bucket_radius_m=bucket_radius_m,
                bucket_index=bucket_index,
                node_coords=node_coords,
            )
            if idx not in selected_ids
            and (
                (idx in force_inclusion_ids)
                if force_inclusion_ids is not None
                else bool(force_inclusion_predicate and force_inclusion_predicate(idx))
            )
        ][:effective_forced_k]
    if not forced:
        return selected
    return merge_seed_candidates(selected, forced, cap=cap)
