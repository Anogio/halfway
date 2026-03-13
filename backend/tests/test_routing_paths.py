from __future__ import annotations

import unittest

from transit_backend.core.artifacts import Node, RuntimeData
from transit_backend.core.routing import build_spatial_index, compute_multi_path, compute_path


class RoutingPathsTest(unittest.TestCase):
    def test_compute_path_returns_edge_sequence_with_route_info(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8009, lon=2.3009),
                Node(idx=2, stop_id="C", name="Charlie", lat=48.8018, lon=2.3018),
            ],
            offsets=[0, 1, 2, 2],
            targets=[1, 2],
            weights=[60, 70],
            edge_kinds=[0, 0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["M1", "M1"],
            route_labels={"M1": "M1 - Metro"},
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=80)

        result = compute_path(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            destination_lat=48.8018,
            destination_lon=2.3018,
            first_mile_radius_m=80,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )

        self.assertEqual(result["reachable"], True)
        self.assertEqual(result["stats"]["node_count"], 3)
        self.assertGreaterEqual(result["summary"]["total_time_s"], 120)
        segments = result["segments"]
        self.assertGreaterEqual(len(segments), 2)
        edge_segments = [segment for segment in segments if segment["type"] == "graph_edge"]
        self.assertEqual(len(edge_segments), 2)
        self.assertEqual(edge_segments[0]["route_id"], "M1")
        self.assertEqual(edge_segments[0]["route_label"], "M1 - Metro")

    def test_max_seed_nodes_caps_path_seed_count(self) -> None:
        nodes = [
            Node(idx=i, stop_id=f"S{i}", name=f"S{i}", lat=48.8 + i * 0.0001, lon=2.3 + i * 0.0001)
            for i in range(6)
        ]
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=nodes,
            offsets=[0] * (len(nodes) + 1),
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=1200)

        result = compute_path(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            destination_lat=48.8005,
            destination_lon=2.3005,
            first_mile_radius_m=1200,
            first_mile_fallback_k=1,
            max_seed_nodes=2,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )
        self.assertEqual(result["stats"]["seed_count"], 2)

    def test_compute_multi_path_returns_one_path_per_origin(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8009, lon=2.3009),
                Node(idx=2, stop_id="C", name="Charlie", lat=48.8018, lon=2.3018),
            ],
            offsets=[0, 1, 2, 2],
            targets=[1, 2],
            weights=[360, 420],
            edge_kinds=[0, 0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["M1", "M1"],
            route_labels={"M1": "M1 - Metro"},
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=100)

        result = compute_multi_path(
            runtime,
            spatial,
            origins=[
                {"id": "origin-1", "lat": 48.8000, "lon": 2.3000},
                {"id": "origin-2", "lat": 48.8009, "lon": 2.3009},
            ],
            destination_lat=48.8018,
            destination_lon=2.3018,
            first_mile_radius_m=100,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )

        self.assertEqual(result["profile"], "weekday_non_holiday")
        self.assertEqual(len(result["paths"]), 2)
        self.assertEqual(result["paths"][0]["origin_id"], "origin-1")
        self.assertEqual(result["paths"][1]["origin_id"], "origin-2")

    def test_compute_multi_path_matches_single_origin_paths(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8009, lon=2.3009),
                Node(idx=2, stop_id="C", name="Charlie", lat=48.8018, lon=2.3018),
            ],
            offsets=[0, 1, 2, 2],
            targets=[1, 2],
            weights=[360, 420],
            edge_kinds=[0, 0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["M1", "M1"],
            route_labels={"M1": "M1 - Metro"},
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=100)
        origins = [
            {"id": "origin-1", "lat": 48.8000, "lon": 2.3000},
            {"id": "origin-2", "lat": 48.8009, "lon": 2.3009},
        ]

        multi = compute_multi_path(
            runtime,
            spatial,
            origins=origins,
            destination_lat=48.8018,
            destination_lon=2.3018,
            first_mile_radius_m=100,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )
        single_by_origin = {
            origin["id"]: compute_path(
                runtime,
                spatial,
                origin_lat=float(origin["lat"]),
                origin_lon=float(origin["lon"]),
                destination_lat=48.8018,
                destination_lon=2.3018,
                first_mile_radius_m=100,
                first_mile_fallback_k=1,
                max_seed_nodes=24,
                walk_speed_mps=1.2,
                max_time_s=3600,
            )
            for origin in origins
        }

        for path in multi["paths"]:
            expected = single_by_origin[path["origin_id"]]
            self.assertEqual(path["reachable"], expected["reachable"])
            self.assertEqual(path["summary"]["total_time_s"], expected["summary"]["total_time_s"])
            self.assertEqual(path["segments"], expected["segments"])
            self.assertEqual(path["nodes"], expected["nodes"])

    def test_compute_path_returns_single_direct_walk_when_faster_than_graph(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8010, lon=2.3010),
            ],
            offsets=[0, 1, 1],
            targets=[1],
            weights=[2400],
            edge_kinds=[0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["R1"],
            route_labels={"R1": "R1"},
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=1000)

        result = compute_path(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            destination_lat=48.8010,
            destination_lon=2.3010,
            first_mile_radius_m=1000,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )

        self.assertEqual(result["reachable"], True)
        self.assertEqual(result["stats"]["node_count"], 0)
        self.assertEqual(result["stats"]["segment_count"], 1)
        self.assertEqual(result["segments"][0]["type"], "walk_origin")
        self.assertEqual(result["segments"][0]["to_label"], "destination")

    def test_compute_path_destination_candidates_use_same_rail_aware_selector(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="490000001A", name="Bus A", lat=48.8000, lon=2.3000),
                Node(idx=1, stop_id="490000001B", name="Bus B", lat=48.8004, lon=2.3004),
                Node(idx=2, stop_id="9400ZZLUTST1", name="Rail Dest", lat=48.8060, lon=2.3060, is_rail_like=True),
                Node(idx=3, stop_id="9400ZZLUTST2", name="Rail Origin", lat=48.8500, lon=2.3500, is_rail_like=True),
            ],
            offsets=[0, 0, 0, 0, 1],
            targets=[2],
            weights=[60],
            edge_kinds=[0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["R1"],
            route_labels={"R1": "R1"},
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=100)

        result = compute_path(
            runtime,
            spatial,
            origin_lat=48.8500,
            origin_lon=2.3500,
            destination_lat=48.8000,
            destination_lon=2.3000,
            first_mile_radius_m=100,
            first_mile_fallback_k=1,
            max_seed_nodes=2,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )

        self.assertTrue(result["reachable"])
        self.assertEqual(result["stats"]["destination_candidate_count"], 2)
        self.assertEqual(result["nodes"][-1]["stop_id"], "9400ZZLUTST1")

    def test_v2_path_groups_boarding_and_alight_into_visible_segments(self) -> None:
        runtime = RuntimeData(
            version="v2",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8000, lon=2.3000, node_kind="physical", node_key="A"),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8009, lon=2.3009, node_kind="physical", node_key="B"),
                Node(idx=2, stop_id="C", name="Charlie", lat=48.8018, lon=2.3018, node_kind="physical", node_key="C"),
                Node(idx=3, stop_id="D", name="Delta", lat=48.8027, lon=2.3027, node_kind="physical", node_key="D"),
                Node(
                    idx=4,
                    stop_id="A",
                    name="Alpha",
                    lat=48.8000,
                    lon=2.3000,
                    node_kind="onboard",
                    node_key="A::R1::0",
                    physical_node_idx=0,
                    route_id="R1",
                    direction_id="0",
                ),
                Node(
                    idx=5,
                    stop_id="B",
                    name="Bravo",
                    lat=48.8009,
                    lon=2.3009,
                    node_kind="onboard",
                    node_key="B::R1::0",
                    physical_node_idx=1,
                    route_id="R1",
                    direction_id="0",
                ),
                Node(
                    idx=6,
                    stop_id="C",
                    name="Charlie",
                    lat=48.8018,
                    lon=2.3018,
                    node_kind="onboard",
                    node_key="C::R2::0",
                    physical_node_idx=2,
                    route_id="R2",
                    direction_id="0",
                ),
                Node(
                    idx=7,
                    stop_id="D",
                    name="Delta",
                    lat=48.8027,
                    lon=2.3027,
                    node_kind="onboard",
                    node_key="D::R2::0",
                    physical_node_idx=3,
                    route_id="R2",
                    direction_id="0",
                ),
            ],
            offsets=[0, 1, 2, 3, 3, 4, 5, 6, 7],
            targets=[4, 2, 6, 5, 1, 7, 3],
            weights=[20, 120, 60, 60, 0, 30, 0],
            edge_kinds=[1, 3, 1, 0, 2, 0, 2],
            edge_kind_legend={0: "ride", 1: "boarding", 2: "alight", 3: "transfer_pathway"},
            edge_route_ids=["R1", "", "R2", "R1", "R1", "R2", "R2"],
            route_labels={"R1": "Line 1", "R2": "Line 2"},
            node_key_index={
                "A": 0,
                "B": 1,
                "C": 2,
                "D": 3,
                "A::R1::0": 4,
                "B::R1::0": 5,
                "C::R2::0": 6,
                "D::R2::0": 7,
            },
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=100)

        result = compute_path(
            runtime,
            spatial,
            origin_lat=48.8000,
            origin_lon=2.3000,
            destination_lat=48.8027,
            destination_lon=2.3027,
            first_mile_radius_m=100,
            first_mile_fallback_k=1,
            max_seed_nodes=24,
            walk_speed_mps=1.2,
            max_time_s=3600,
        )

        self.assertTrue(result["reachable"])
        self.assertEqual([node["stop_id"] for node in result["nodes"]], ["A", "B", "C", "D"])
        self.assertEqual(result["stats"]["boarding_wait_s"], 80)
        self.assertEqual(result["stats"]["transfer_s"], 120)
        graph_segments = [segment for segment in result["segments"] if segment["type"] == "graph_edge"]
        self.assertEqual([segment["kind"] for segment in graph_segments], ["ride", "transfer_pathway", "ride"])
        self.assertEqual(graph_segments[0]["seconds"], 80)
        self.assertEqual(graph_segments[0]["route_label"], "Line 1")
        self.assertEqual(graph_segments[2]["seconds"], 90)
        self.assertEqual(graph_segments[2]["route_label"], "Line 2")
