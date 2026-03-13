from __future__ import annotations

import unittest

from transit_backend.core.artifacts import Node, RuntimeData
from transit_backend.core.path_payloads import (
    build_reachable_path_payload,
    build_unreachable_path_payload,
)


def _runtime() -> RuntimeData:
    return RuntimeData(
        version="vtest",
        profile="weekday_non_holiday",
        nodes=[
            Node(idx=0, stop_id="A", name="Alpha", lat=48.8, lon=2.3),
            Node(idx=1, stop_id="B", name="Bravo", lat=48.801, lon=2.301),
            Node(idx=2, stop_id="C", name="Charlie", lat=48.802, lon=2.302),
        ],
        offsets=[0, 1, 1, 1],
        targets=[1],
        weights=[120],
        grid_cells={},
        grid_links={},
        metadata={},
    )


class PathPayloadsTest(unittest.TestCase):
    def test_build_reachable_payload_includes_walk_and_graph_segments(self) -> None:
        payload = build_reachable_path_payload(
            _runtime(),
            origin_lat=48.8,
            origin_lon=2.3,
            destination_lat=48.802,
            destination_lon=2.302,
            seeds=[(0, 10)],
            destination_candidates=[(2, 20)],
            node_path=[0, 1, 2],
            prev_edge=[-1, 0, -1],
            graph_time_s=140,
            best_node=2,
            destination_walk_s=20,
            best_total=170,
            max_time_s=3600,
        )

        self.assertEqual(payload["reachable"], True)
        self.assertEqual(payload["stats"]["seed_count"], 1)
        self.assertEqual(payload["stats"]["destination_candidate_count"], 1)
        self.assertEqual(payload["stats"]["node_count"], 3)
        self.assertEqual(payload["stats"]["segment_count"], 3)
        segments = payload["segments"]
        self.assertEqual(segments[0]["type"], "walk_origin")
        self.assertEqual(segments[1]["type"], "graph_edge")
        self.assertEqual(segments[1]["kind"], "ride")
        self.assertEqual(segments[1]["route_id"], "")
        self.assertEqual(segments[2]["type"], "walk_destination")

    def test_build_reachable_payload_skips_walk_segments_when_zero(self) -> None:
        payload = build_reachable_path_payload(
            _runtime(),
            origin_lat=48.8,
            origin_lon=2.3,
            destination_lat=48.801,
            destination_lon=2.301,
            seeds=[(0, 0)],
            destination_candidates=[(1, 0)],
            node_path=[0, 1],
            prev_edge=[-1, 0],
            graph_time_s=120,
            best_node=1,
            destination_walk_s=0,
            best_total=120,
            max_time_s=3600,
        )

        self.assertEqual(payload["stats"]["origin_walk_s"], 0)
        self.assertEqual(payload["stats"]["destination_walk_s"], 0)
        self.assertEqual(len(payload["segments"]), 1)
        self.assertEqual(payload["segments"][0]["type"], "graph_edge")

    def test_build_unreachable_payload(self) -> None:
        payload = build_unreachable_path_payload(
            _runtime(),
            origin_lat=48.8,
            origin_lon=2.3,
            destination_lat=48.9,
            destination_lon=2.4,
            seed_count=2,
            destination_candidate_count=0,
            max_time_s=1800,
        )
        self.assertEqual(payload["reachable"], False)
        self.assertEqual(payload["stats"]["seed_count"], 2)
        self.assertEqual(payload["stats"]["destination_candidate_count"], 0)
        self.assertEqual(payload["summary"]["max_time_s"], 1800)
        self.assertEqual(payload["segments"], [])
        self.assertEqual(payload["nodes"], [])
