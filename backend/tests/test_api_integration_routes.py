from __future__ import annotations

from transit_backend.api import server
from transit_backend.api.state import CityRuntimeState, OriginGridCache
from transit_backend.core.artifacts import GridCell, Node, RuntimeData
from transit_backend.core.isochrones import infer_grid_topology
from transit_backend.core.routing import build_spatial_index

from api_integration_base import ApiIntegrationTestCase


class ApiRoutesIntegrationTest(ApiIntegrationTestCase):
    def test_health_and_metadata(self) -> None:
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["ok"], True)
        self.assertEqual(health.json()["cities"], ["paris_fr"])

        metadata = self.client.get("/metadata")
        self.assertEqual(metadata.status_code, 200)
        payload = metadata.json()
        self.assertEqual(sorted(payload.keys()), ["cities"])
        self.assertGreaterEqual(len(payload["cities"]), 1)

        city = payload["cities"][0]
        self.assertEqual(sorted(city.keys()), ["bbox", "country_code", "default_view", "id"])
        self.assertEqual(city["id"], "paris_fr")
        self.assertEqual(city["country_code"], "fr")
        self.assertEqual(len(city["default_view"]), 3)
        self.assertEqual(len(city["bbox"]), 4)

    def test_multi_isochrones_and_multi_path(self) -> None:
        multi_isochrones = self.client.post(
            "/multi_isochrones",
            json={
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8566, "lon": 2.3522},
                    {"id": "origin-2", "lat": 48.86, "lon": 2.36},
                ],
            },
        )
        self.assertEqual(multi_isochrones.status_code, 200)
        multi_iso_payload = multi_isochrones.json()
        self.assertNotIn("stats", multi_iso_payload)
        self.assertEqual(multi_iso_payload["feature_collection"]["type"], "FeatureCollection")

        multi_path = self.client.post(
            "/multi_path",
            json={
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8566, "lon": 2.3522},
                    {"id": "origin-2", "lat": 48.86, "lon": 2.36},
                ],
                "destination": {"lat": 48.86, "lon": 2.36},
            },
        )
        self.assertEqual(multi_path.status_code, 200)
        multi_path_payload = multi_path.json()
        self.assertEqual(len(multi_path_payload["paths"]), 2)
        self.assertEqual(multi_path_payload["paths"][0]["origin_id"], "origin-1")
        self.assertNotIn("stats", multi_path_payload["paths"][0])

    def test_multi_routes_include_stats_when_debug_enabled(self) -> None:
        multi_isochrones = self.client.post(
            "/multi_isochrones",
            json={
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8566, "lon": 2.3522},
                    {"id": "origin-2", "lat": 48.86, "lon": 2.36},
                ],
                "debug": True,
            },
        )
        self.assertEqual(multi_isochrones.status_code, 200)
        multi_iso_payload = multi_isochrones.json()
        self.assertEqual(multi_iso_payload["stats"]["origin_count"], 2)

        multi_path = self.client.post(
            "/multi_path",
            json={
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8566, "lon": 2.3522},
                    {"id": "origin-2", "lat": 48.86, "lon": 2.36},
                ],
                "destination": {"lat": 48.86, "lon": 2.36},
                "debug": True,
            },
        )
        self.assertEqual(multi_path.status_code, 200)
        multi_path_payload = multi_path.json()
        self.assertIn("stats", multi_path_payload["paths"][0])

    def test_multi_path_uses_single_runtime(self) -> None:
        runtime = RuntimeData(
            version="v2",
            profile="weekday_non_holiday",
            nodes=[
                Node(idx=0, stop_id="A", name="Alpha", lat=48.8566, lon=2.3522, node_kind="physical", node_key="A"),
                Node(idx=1, stop_id="B", name="Bravo", lat=48.8600, lon=2.3600, node_kind="physical", node_key="B"),
                Node(
                    idx=2,
                    stop_id="A",
                    name="Alpha",
                    lat=48.8566,
                    lon=2.3522,
                    node_kind="onboard",
                    node_key="A::R1::0",
                    physical_node_idx=0,
                    route_id="R1",
                    direction_id="0",
                ),
                Node(
                    idx=3,
                    stop_id="B",
                    name="Bravo",
                    lat=48.8600,
                    lon=2.3600,
                    node_kind="onboard",
                    node_key="B::R1::0",
                    physical_node_idx=1,
                    route_id="R1",
                    direction_id="0",
                ),
            ],
            offsets=[0, 1, 1, 2, 3],
            targets=[2, 3, 1],
            weights=[30, 60, 0],
            edge_kinds=[1, 0, 2],
            edge_kind_legend={0: "ride", 1: "boarding", 2: "alight"},
            edge_route_ids=["R1", "R1", "R1"],
            route_labels={"R1": "Path Runtime"},
            node_key_index={"A": 0, "B": 1, "A::R1::0": 2, "B::R1::0": 3},
            grid_cells={
                0: GridCell(cell_id=0, lat=48.8566, lon=2.3522, in_scope=True),
                1: GridCell(cell_id=1, lat=48.8600, lon=2.3600, in_scope=True),
            },
            grid_links={0: [(0, 0)], 1: [(1, 0)]},
            metadata={},
        )
        city_state = CityRuntimeState(
            city_id="paris",
            label="Paris",
            runtime=runtime,
            spatial=build_spatial_index(runtime, radius_m=800.0),
            topology=infer_grid_topology(runtime),
            origin_grid_cache=OriginGridCache(max_entries=128),
        )
        server.APP_STATE["cities_by_id"]["paris"] = city_state
        server.app.state.app_state = server.APP_STATE

        response = self.client.post(
            "/multi_path",
            json={
                "city": "paris_fr",
                "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}],
                "destination": {"lat": 48.8600, "lon": 2.3600},
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        graph_segments = [segment for segment in payload["paths"][0]["segments"] if segment["type"] == "graph_edge"]
        self.assertEqual(len(graph_segments), 1)
        self.assertEqual(graph_segments[0]["route_label"], "Path Runtime")

    def test_server_rejects_missing_or_unknown_city(self) -> None:
        response_missing = self.client.post(
            "/multi_isochrones",
            json={"origins": [{"id": "a", "lat": 48.8, "lon": 2.3}]},
        )
        self.assertEqual(response_missing.status_code, 400)

        response_unknown = self.client.post(
            "/multi_isochrones",
            json={"city": "unknown", "origins": [{"id": "a", "lat": 48.8, "lon": 2.3}]},
        )
        self.assertEqual(response_unknown.status_code, 400)

    def test_removed_single_origin_endpoints_return_404(self) -> None:
        response_heatmap = self.client.post(
            "/heatmap",
            json={"city": "paris_fr", "origin_lat": 48.8566, "origin_lon": 2.3522},
        )
        self.assertEqual(response_heatmap.status_code, 404)

        response_iso = self.client.post(
            "/isochrones",
            json={"city": "paris_fr", "origin_lat": 48.8566, "origin_lon": 2.3522},
        )
        self.assertEqual(response_iso.status_code, 404)

        response_path = self.client.post(
            "/path",
            json={
                "city": "paris_fr",
                "origin_lat": 48.8566,
                "origin_lon": 2.3522,
                "destination_lat": 48.86,
                "destination_lon": 2.36,
            },
        )
        self.assertEqual(response_path.status_code, 404)

    def test_malformed_payload_shape(self) -> None:
        malformed = self.client.post("/multi_isochrones", json=["not", "an", "object"])
        self.assertEqual(malformed.status_code, 400)
