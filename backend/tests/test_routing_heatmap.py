from __future__ import annotations

import unittest

from transit_backend.core.artifacts import Node, RuntimeData
from transit_backend.core.routing import build_spatial_index, nearby_nodes


class RoutingHeatmapTest(unittest.TestCase):
    def test_nearby_nodes_walk_speed_changes_seed_cost(self) -> None:
        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[Node(idx=0, stop_id="A", name="A", lat=48.8000, lon=2.3000)],
            offsets=[0, 0],
            targets=[],
            weights=[],
            grid_cells={},
            grid_links={},
            metadata={},
        )
        spatial = build_spatial_index(runtime, radius_m=500)

        slow = nearby_nodes(
            runtime,
            spatial,
            lat=48.8000,
            lon=2.3010,
            radius_m=500,
            walk_speed_mps=1.0,
            limit=5,
        )
        fast = nearby_nodes(
            runtime,
            spatial,
            lat=48.8000,
            lon=2.3010,
            radius_m=500,
            walk_speed_mps=2.0,
            limit=5,
        )
        self.assertEqual(slow[0][0], 0)
        self.assertEqual(fast[0][0], 0)
        self.assertGreater(slow[0][1], fast[0][1])
