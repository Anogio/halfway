from __future__ import annotations

import unittest

from transit_backend.core.artifacts import GridCell, Node, RuntimeData
from transit_backend.core.isochrones import infer_grid_topology
from transit_backend.core.routing import build_spatial_index, compute_isochrones, compute_multi_isochrones


class RoutingIsochronesIntegrationTest(unittest.TestCase):
    def test_compute_isochrones_returns_geojson_buckets(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="A", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="B", lat=48.8009, lon=2.3009),
            ],
            offsets=[0, 1, 1],
            targets=[1],
            weights=[300],
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8000, lon=2.3000, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8000, lon=2.3020, in_scope=True),
                2: GridCell(cell_id=2, lat=48.8020, lon=2.3000, in_scope=True),
                3: GridCell(cell_id=3, lat=48.8020, lon=2.3020, in_scope=True),
            },
            grid_links={
                0: [(0, 0)],
                1: [(1, 0)],
                2: [(0, 120)],
                3: [(1, 120)],
            },
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=800)
        topology = infer_grid_topology(runtime)

        result = compute_isochrones(
            runtime,
            spatial,
            topology=topology,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=800,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            compute_max_time_s=1800,
            render_max_time_s=1800,
            bucket_size_s=300,
        )

        self.assertGreaterEqual(result["stats"]["reachable_cells"], 2)
        self.assertEqual(result["stats"]["bucket_size_s"], 300)
        self.assertEqual(result["feature_collection"]["type"], "FeatureCollection")
        self.assertGreaterEqual(len(result["feature_collection"]["features"]), 1)

        first_feature = result["feature_collection"]["features"][0]
        self.assertEqual(first_feature["type"], "Feature")
        self.assertEqual(first_feature["geometry"]["type"], "MultiPolygon")
        self.assertIn("min_time_s", first_feature["properties"])
        self.assertIn("max_time_s", first_feature["properties"])

    def test_compute_isochrones_decouples_compute_and_render_horizons(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="A", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="B", lat=48.8009, lon=2.3009),
            ],
            offsets=[0, 1, 1],
            targets=[1],
            weights=[300],
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8000, lon=2.3000, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8000, lon=2.3020, in_scope=True),
                2: GridCell(cell_id=2, lat=48.8020, lon=2.3000, in_scope=True),
                3: GridCell(cell_id=3, lat=48.8020, lon=2.3020, in_scope=True),
            },
            grid_links={
                0: [(0, 0)],
                1: [(1, 0)],
                2: [(0, 120)],
                3: [(1, 900)],
            },
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=800)
        topology = infer_grid_topology(runtime)

        result = compute_isochrones(
            runtime,
            spatial,
            topology=topology,
            origin_lat=48.8000,
            origin_lon=2.3000,
            first_mile_radius_m=800,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            compute_max_time_s=1800,
            render_max_time_s=600,
            bucket_size_s=300,
        )

        stats = result["stats"]
        self.assertEqual(stats["compute_max_time_s"], 1800)
        self.assertEqual(stats["render_max_time_s"], 600)
        self.assertGreater(stats["reachable_cells_compute_horizon"], stats["reachable_cells_render_horizon"])
        for feature in result["feature_collection"]["features"]:
            self.assertLessEqual(feature["properties"]["max_time_s"], 600)

    def test_compute_multi_isochrones_reconciles_with_max_and_intersection(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="A", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="B", lat=48.8010, lon=2.3010),
            ],
            offsets=[0, 1, 1],
            targets=[1],
            weights=[300],
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8000, lon=2.3000, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8010, lon=2.3010, in_scope=True),
                2: GridCell(cell_id=2, lat=48.8015, lon=2.3015, in_scope=True),
            },
            grid_links={
                0: [(0, 0)],
                1: [(1, 0)],
                2: [(0, 600), (1, 600)],
            },
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=120)
        topology = infer_grid_topology(runtime)

        result = compute_multi_isochrones(
            runtime,
            spatial,
            topology=topology,
            origins=[
                {"id": "origin-1", "lat": 48.8000, "lon": 2.3000},
                {"id": "origin-2", "lat": 48.8010, "lon": 2.3010},
            ],
            first_mile_radius_m=120,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
            bucket_size_s=300,
        )

        self.assertEqual(result["stats"]["origin_count"], 2)
        self.assertEqual(result["stats"]["reachable_cells_compute_horizon"], 2)
        self.assertEqual(result["feature_collection"]["type"], "FeatureCollection")

    def test_compute_multi_isochrones_empty_intersection_returns_empty_features(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="A", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="B", lat=48.8020, lon=2.3020),
            ],
            offsets=[0, 0, 0],
            targets=[],
            weights=[],
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8000, lon=2.3000, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8020, lon=2.3020, in_scope=True),
            },
            grid_links={
                0: [(0, 0)],
                1: [(1, 0)],
            },
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=120)
        topology = infer_grid_topology(runtime)

        result = compute_multi_isochrones(
            runtime,
            spatial,
            topology=topology,
            origins=[
                {"id": "origin-1", "lat": 48.8000, "lon": 2.3000},
                {"id": "origin-2", "lat": 48.8020, "lon": 2.3020},
            ],
            first_mile_radius_m=120,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
            bucket_size_s=300,
        )

        self.assertEqual(result["stats"]["reachable_cells_compute_horizon"], 0)
        self.assertEqual(result["stats"]["reachable_cells"], 0)
        self.assertEqual(result["feature_collection"]["features"], [])
