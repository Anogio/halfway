from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

from helpers import make_settings
from transit_backend.api import server
from transit_backend.api.state import CityRuntimeState, OriginGridCache
from transit_backend.core.artifacts import GridCell, Node, RuntimeData
from transit_backend.core.isochrones import infer_grid_topology
from transit_backend.core.routing import build_spatial_index


class ApiIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_state = server.APP_STATE

        runtime = RuntimeData(
            version="vtest",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8566, lon=2.3522),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8600, lon=2.3600),
            ],
            offsets=[0, 1, 1],
            targets=[1],
            weights=[420],
            edge_kinds=[0],
            edge_kind_legend={0: "ride"},
            edge_route_ids=["M1"],
            route_labels={"M1": "M1"},
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8566, lon=2.3522, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8600, lon=2.3600, in_scope=True),
            },
            grid_links={
                0: [(0, 0)],
                1: [(1, 0)],
            },
            metadata={"manifest_key": "value"},
        )
        params = {
            "first_mile_radius_m": 800.0,
            "first_mile_fallback_k": 3,
            "max_time_s": 3600,
            "isochrone_render_max_time_s": 3600,
            "max_seed_nodes": 24,
            "walk_speed_mps": 1.2,
            "isochrone_bucket_size_s": 300,
        }
        city_state = CityRuntimeState(
            city_id="paris",
            label="Paris",
            runtime=runtime,
            spatial=build_spatial_index(runtime, radius_m=params["first_mile_radius_m"]),
            topology=infer_grid_topology(runtime),
            origin_grid_cache=OriginGridCache(max_entries=128),
        )
        server.APP_STATE = {
            "config": SimpleNamespace(settings=make_settings()),
            "cities_by_id": {"paris": city_state},
            "params": params,
        }
        server.app.state.app_state = server.APP_STATE
        self.client = TestClient(server.app)

    def tearDown(self) -> None:
        server.APP_STATE = self._previous_state
        server.app.state.app_state = server.APP_STATE
