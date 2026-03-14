from __future__ import annotations

from types import SimpleNamespace

from transit_backend.api import server
from transit_backend.api.state import CityRuntimeState, OriginGridCache, build_app_state
from transit_backend.core.artifacts import GridCell, Node, RuntimeData
from transit_backend.core.isochrones import infer_grid_topology
from transit_backend.core.routing import build_spatial_index

from api_integration_base import ApiIntegrationTestCase
from helpers import make_settings


class ApiRoutesIntegrationTest(ApiIntegrationTestCase):
    def test_health_and_metadata(self) -> None:
        self.assertEqual(server.APP_STATE["city_runtime_manager"].snapshot_loaded_city_ids(), [])
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["ok"], True)
        self.assertEqual(health.json()["cities"], ["paris_fr"])
        self.assertEqual(self.load_calls, [])

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
        self.assertEqual(self.load_calls, [])

    def test_debug_assets_is_read_only_for_unloaded_city(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        response = self.client.get("/debug/assets")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(sorted(payload.keys()), ["cities", "manager", "process"])
        self.assertEqual(payload["manager"]["known_city_count"], 1)
        self.assertEqual(payload["manager"]["loaded_city_count"], 0)
        self.assertEqual(payload["manager"]["loaded_city_ids"], [])
        self.assertEqual(payload["process"]["pid"] > 0, True)
        self.assertIn("current_rss_bytes", payload["process"])
        self.assertEqual(len(payload["cities"]), 1)
        self.assertEqual(payload["cities"][0]["city_id"], "paris")
        self.assertEqual(payload["cities"][0]["public_city_id"], "paris_fr")
        self.assertEqual(payload["cities"][0]["configured_artifact_version"], "vtest")
        self.assertEqual(payload["cities"][0]["loaded"], False)
        self.assertEqual(payload["cities"][0]["loading"], False)
        self.assertEqual(payload["cities"][0]["inflight_requests"], 0)
        self.assertIsNone(payload["cities"][0]["last_active_at"])
        self.assertIsNone(payload["cities"][0]["idle_for_s"])
        self.assertIsNone(payload["cities"][0]["runtime"])
        self.assertEqual(manager._entries["paris"].last_active_at, None)
        self.assertEqual(self.load_calls, [])

    def test_debug_assets_reports_loaded_runtime_without_refreshing_last_active(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        warm = self.client.post(
            "/multi_isochrones",
            json={"city": "paris_fr", "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
        )
        self.assertEqual(warm.status_code, 200)
        loaded_state = manager.get_loaded_city_state("paris")
        self.assertIsNotNone(loaded_state)
        cache_entries_before = loaded_state.origin_grid_cache.snapshot_stats()["entries"]
        loaded_state.origin_grid_cache.put(("cache",), {1: 120}, 2)
        cache_entries_after = loaded_state.origin_grid_cache.snapshot_stats()["entries"]
        before_last_active_at = manager._entries["paris"].last_active_at

        response = self.client.get("/debug/assets")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        city = payload["cities"][0]
        runtime = city["runtime"]

        self.assertEqual(manager._entries["paris"].last_active_at, before_last_active_at)
        self.assertEqual(payload["manager"]["loaded_city_count"], 1)
        self.assertEqual(payload["manager"]["loaded_city_ids"], ["paris"])
        self.assertEqual(city["loaded"], True)
        self.assertEqual(city["loading"], False)
        self.assertEqual(city["inflight_requests"], 0)
        self.assertEqual(city["last_active_at"], before_last_active_at)
        self.assertIsInstance(city["idle_for_s"], float)
        self.assertEqual(runtime["runtime_version"], "vtest")
        self.assertEqual(runtime["profile"], "weekday_non_holiday")
        self.assertEqual(runtime["node_count"], 2)
        self.assertEqual(runtime["edge_count"], 1)
        self.assertEqual(runtime["grid_cell_count"], 2)
        self.assertEqual(runtime["grid_link_cell_count"], 2)
        self.assertEqual(runtime["grid_link_count"], 2)
        self.assertEqual(runtime["route_count"], 1)
        self.assertEqual(runtime["origin_grid_cache_entries"], cache_entries_after)
        self.assertGreaterEqual(cache_entries_after, cache_entries_before)
        self.assertEqual(runtime["origin_grid_cache_max_entries"], 128)
        self.assertEqual(runtime["manifest"]["artifact_count"], 0)
        self.assertEqual(self.load_calls, ["paris"])

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
        self.assertEqual(self.load_calls, ["paris"])

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
        self.assertEqual(self.load_calls, ["paris"])

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
        server.APP_STATE = build_app_state(
            SimpleNamespace(settings=make_settings()),
            runtime_loader=lambda _city_id: city_state,
        )
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

    def test_wakeup_loads_city_without_blocking_followup_compute(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        response = self.client.post("/wakeup", json={"city": "paris_fr"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        self.assertTrue(self.wait_until(lambda: manager.get_loaded_city_state("paris") is not None))
        self.assertEqual(self.load_calls, ["paris"])

        compute = self.client.post(
            "/multi_isochrones",
            json={"city": "paris_fr", "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
        )
        self.assertEqual(compute.status_code, 200)
        self.assertEqual(self.load_calls, ["paris"])

    def test_wakeup_is_idempotent_for_loaded_or_loading_city(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        first = self.client.post("/wakeup", json={"city": "paris_fr"})
        self.assertEqual(first.status_code, 200)
        self.assertTrue(self.wait_until(lambda: manager.get_loaded_city_state("paris") is not None))
        self.assertEqual(self.load_calls, ["paris"])

        second = self.client.post("/wakeup", json={"city": "paris_fr"})
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.load_calls, ["paris"])

    def test_runtime_manager_reaps_idle_city_and_reloads_it(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        first = self.client.post(
            "/multi_isochrones",
            json={"city": "paris_fr", "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.load_calls, ["paris"])
        self.assertEqual(manager.snapshot_loaded_city_ids(), ["paris"])
        loaded_state = manager.get_loaded_city_state("paris")
        self.assertIsNotNone(loaded_state)
        loaded_state.origin_grid_cache.put(("cache",), {1: 120}, 2)
        last_active_at = manager._entries["paris"].last_active_at
        self.assertIsNotNone(last_active_at)
        self.assertEqual(manager.unload_idle_cities(now=float(last_active_at) + 599.0), [])
        self.assertEqual(manager.unload_idle_cities(now=float(last_active_at) + 601.0), ["paris"])
        self.assertEqual(manager.snapshot_loaded_city_ids(), [])

        second = self.client.post(
            "/multi_isochrones",
            json={"city": "paris_fr", "origins": [{"id": "origin-2", "lat": 48.86, "lon": 2.36}]},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.load_calls, ["paris", "paris"])
        reloaded_state = manager.get_loaded_city_state("paris")
        self.assertIsNotNone(reloaded_state)
        self.assertIsNone(reloaded_state.origin_grid_cache.get(("cache",)))

    def test_wakeup_refreshes_idle_ttl(self) -> None:
        manager = server.APP_STATE["city_runtime_manager"]

        first = self.client.post(
            "/multi_isochrones",
            json={"city": "paris_fr", "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
        )
        self.assertEqual(first.status_code, 200)
        initial_active_at = manager._entries["paris"].last_active_at
        self.assertIsNotNone(initial_active_at)

        wakeup = self.client.post("/wakeup", json={"city": "paris_fr"})
        self.assertEqual(wakeup.status_code, 200)
        refreshed_active_at = manager._entries["paris"].last_active_at
        self.assertIsNotNone(refreshed_active_at)
        self.assertGreaterEqual(float(refreshed_active_at), float(initial_active_at))

        self.assertEqual(manager.unload_idle_cities(now=float(refreshed_active_at) + 599.0), [])
        self.assertEqual(manager.unload_idle_cities(now=float(refreshed_active_at) + 601.0), ["paris"])
        self.assertEqual(manager.snapshot_loaded_city_ids(), [])

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

        wakeup_missing = self.client.post("/wakeup", json={})
        self.assertEqual(wakeup_missing.status_code, 400)

        wakeup_unknown = self.client.post("/wakeup", json={"city": "unknown"})
        self.assertEqual(wakeup_unknown.status_code, 400)

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
