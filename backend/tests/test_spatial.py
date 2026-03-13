from __future__ import annotations

import unittest

from transit_backend.core.artifacts import Node, RuntimeData
from transit_backend.core.spatial import (
    build_spatial_index,
    nearest_k,
    resolve_seeds,
)
from transit_shared.seed_selection import resolve_access_candidates


def _runtime() -> RuntimeData:
    return RuntimeData(
        version="vtest",
        profile="weekday_non_holiday",
        nodes=[
            Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000),
            Node(idx=1, stop_id="B", name="Bravo", lat=48.8010, lon=2.3010),
        ],
        offsets=[0, 0, 0],
        targets=[],
        weights=[],
        grid_cells={},
        grid_links={},
        metadata={},
    )


class SpatialHelpersTest(unittest.TestCase):
    def test_resolve_seeds_uses_radius_matches_when_available(self) -> None:
        runtime = _runtime()
        spatial = build_spatial_index(runtime, radius_m=250)

        seeds = resolve_seeds(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=250,
            first_mile_fallback_k=1,
            max_seed_nodes=2,
            walk_speed_mps=1.2,
        )

        self.assertGreaterEqual(len(seeds), 1)
        self.assertEqual(seeds[0][0], 0)

    def test_resolve_seeds_falls_back_to_nearest_k(self) -> None:
        runtime = _runtime()
        spatial = build_spatial_index(runtime, radius_m=10)

        seeds = resolve_seeds(
            runtime,
            spatial,
            origin_lat=49.0,
            origin_lon=3.0,
            first_mile_radius_m=10,
            first_mile_fallback_k=1,
            max_seed_nodes=2,
            walk_speed_mps=1.2,
        )

        self.assertEqual(len(seeds), 1)
        self.assertIn(seeds[0][0], {0, 1})

    def test_nearest_k_returns_empty_when_runtime_has_no_nodes(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[],
            offsets=[0],
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )

        self.assertEqual(nearest_k(runtime, lat=48.8, lon=2.3, walk_speed_mps=1.2, k=3), [])

    def test_resolve_seeds_includes_rail_candidate_when_radius_seeds_are_bus_only(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="490000001A", name="Bus 1", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="490000001B", name="Bus 2", lat=48.8004, lon=2.3004),
                Node(idx=2, stop_id="490000001C", name="Bus 3", lat=48.8008, lon=2.3008),
                Node(idx=3, stop_id="9400ZZLUTST1", name="Rail 1", lat=48.8070, lon=2.3070, is_rail_like=True),
                Node(idx=4, stop_id="9400ZZLUTST2", name="Rail 2", lat=48.8090, lon=2.3090, is_rail_like=True),
            ],
            offsets=[0, 0, 0, 0, 0, 0],
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=500)

        seeds = resolve_seeds(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=500,
            first_mile_fallback_k=2,
            max_seed_nodes=3,
            walk_speed_mps=1.2,
        )

        self.assertEqual(len(seeds), 3)
        self.assertTrue(any(runtime.nodes[idx].is_rail_like for idx, _ in seeds))

    def test_resolve_seeds_matches_shared_selector(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="490000001A", name="Bus 1", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="490000001B", name="Bus 2", lat=48.8004, lon=2.3004),
                Node(idx=2, stop_id="9400ZZLUTST1", name="Rail 1", lat=48.8070, lon=2.3070, is_rail_like=True),
            ],
            offsets=[0, 0, 0, 0],
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=500)

        expected = resolve_access_candidates(
            lat=48.8000,
            lon=2.3000,
            search_radius_m=500,
            bucket_radius_m=500,
            bucket_index=spatial.bucket,
            node_coords=spatial.node_coords,
            walk_speed_mps=1.2,
            limit=2,
            fallback_k=1,
            allow_global_fallback=True,
            force_inclusion_ids=frozenset({2}),
            forced_k=1,
            forced_nearest_index=spatial.rail_nearest_index,
        )

        actual = resolve_seeds(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=500,
            first_mile_fallback_k=1,
            max_seed_nodes=2,
            walk_speed_mps=1.2,
        )

        self.assertEqual(actual, expected)

    def test_build_spatial_index_ignores_onboard_nodes_for_access(self) -> None:
        runtime = RuntimeData(
            version="v2",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000, node_kind="physical"),
                Node(
                    idx=1,
                    stop_id="A",
                    name="Alpha",
                    lat=48.8000,
                    lon=2.3000,
                    node_kind="onboard",
                    physical_node_idx=0,
                    route_id="R1",
                    direction_id="0",
                ),
            ],
            offsets=[0, 0, 0],
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=100)

        seeds = resolve_seeds(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=100,
            first_mile_fallback_k=1,
            max_seed_nodes=5,
            walk_speed_mps=1.2,
        )

        self.assertEqual(seeds, [(0, 0)])
