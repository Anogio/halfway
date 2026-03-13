from __future__ import annotations

import unittest
from collections import defaultdict

from transit_shared.geo import bucket_key
from transit_shared.seed_selection import build_nearest_node_index, resolve_access_candidates


def _bucket_index(
    node_coords: dict[int, tuple[float, float]],
    *,
    radius_m: float,
) -> dict[tuple[int, int], list[int]]:
    index: dict[tuple[int, int], list[int]] = defaultdict(list)
    for idx, (lat, lon) in node_coords.items():
        index[bucket_key(lat, lon, radius_m)].append(idx)
    return dict(index)


class SeedSelectionTest(unittest.TestCase):
    def test_force_inclusion_can_use_global_search(self) -> None:
        node_coords = {
            0: (48.8000, 2.3000),
            1: (48.8004, 2.3004),
            2: (48.8070, 2.3070),
        }
        bucket_index = _bucket_index(node_coords, radius_m=500)

        selected = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=500,
            bucket_radius_m=500,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=1,
            allow_global_fallback=False,
            force_inclusion_predicate=lambda idx: idx == 2,
            forced_k=1,
            allow_forced_global_search=True,
        )

        self.assertEqual({idx for idx, _ in selected}, {0, 2})

    def test_force_inclusion_can_be_limited_to_in_radius_candidates(self) -> None:
        node_coords = {
            0: (48.8000, 2.3000),
            1: (48.8004, 2.3004),
            2: (48.8070, 2.3070),
        }
        bucket_index = _bucket_index(node_coords, radius_m=500)

        selected = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=500,
            bucket_radius_m=500,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=1,
            allow_global_fallback=False,
            force_inclusion_predicate=lambda idx: idx == 2,
            forced_k=1,
            allow_forced_global_search=False,
        )

        self.assertEqual({idx for idx, _ in selected}, {0, 1})

    def test_exact_index_matches_bruteforce_for_global_fallback(self) -> None:
        node_coords = {
            0: (48.7000, 2.2000),
            1: (48.7500, 2.2500),
            2: (48.8000, 2.3000),
            3: (48.8500, 2.3500),
            4: (48.9000, 2.4000),
        }
        bucket_index = _bucket_index(node_coords, radius_m=250)
        nearest_index = build_nearest_node_index(node_coords)

        brute_force = resolve_access_candidates(
            lat=48.8123,
            lon=2.2876,
            search_radius_m=50,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=3,
            fallback_k=3,
            allow_global_fallback=True,
        )
        indexed = resolve_access_candidates(
            lat=48.8123,
            lon=2.2876,
            search_radius_m=50,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=3,
            fallback_k=3,
            allow_global_fallback=True,
            nearest_index=nearest_index,
        )

        self.assertEqual(indexed, brute_force)

    def test_exact_index_matches_bruteforce_for_filtered_rail_fallback(self) -> None:
        node_coords = {
            0: (48.7000, 2.2000),
            1: (48.7500, 2.2500),
            2: (48.8000, 2.3000),
            3: (48.8500, 2.3500),
            4: (48.9000, 2.4000),
        }
        bucket_index = _bucket_index(node_coords, radius_m=250)
        nearest_index = build_nearest_node_index(node_coords)

        brute_force = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=80,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=2,
            allow_global_fallback=False,
            force_inclusion_predicate=lambda idx: idx in {3, 4},
            forced_k=1,
            allow_forced_global_search=True,
        )
        indexed = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=80,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=2,
            allow_global_fallback=False,
            force_inclusion_predicate=lambda idx: idx in {3, 4},
            forced_k=1,
            allow_forced_global_search=True,
            nearest_index=nearest_index,
        )

        self.assertEqual(indexed, brute_force)

    def test_filtered_subset_index_matches_predicate_scan(self) -> None:
        node_coords = {
            0: (48.7000, 2.2000),
            1: (48.7500, 2.2500),
            2: (48.8000, 2.3000),
            3: (48.8500, 2.3500),
            4: (48.9000, 2.4000),
        }
        bucket_index = _bucket_index(node_coords, radius_m=250)
        nearest_index = build_nearest_node_index(node_coords)
        rail_ids = frozenset({3, 4})
        rail_index = build_nearest_node_index({idx: node_coords[idx] for idx in rail_ids})

        predicate_scan = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=80,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=2,
            allow_global_fallback=False,
            force_inclusion_ids=rail_ids,
            forced_k=1,
            allow_forced_global_search=True,
            nearest_index=nearest_index,
        )
        subset_index = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=80,
            bucket_radius_m=250,
            bucket_index=bucket_index,
            node_coords=node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=2,
            allow_global_fallback=False,
            force_inclusion_ids=rail_ids,
            forced_k=1,
            allow_forced_global_search=True,
            nearest_index=nearest_index,
            forced_nearest_index=rail_index,
        )

        self.assertEqual(subset_index, predicate_scan)
