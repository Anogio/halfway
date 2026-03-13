from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from transit_backend.config.settings import (
    get_city_artifacts_dir,
    load_backend_config,
)
from transit_backend.core.artifacts import RuntimeData, load_runtime_data
from transit_backend.core.isochrones import GridTopology, infer_grid_topology
from transit_backend.core.routing import SpatialIndex, build_spatial_index

SERVER_TIME_CAP_S = 3600
ORIGIN_GRID_CACHE_MAX_ENTRIES = 128


class OriginGridCache:
    def __init__(self, max_entries: int) -> None:
        self.max_entries = max(1, int(max_entries))
        self._rows: OrderedDict[tuple[object, ...], tuple[dict[int, int], int]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple[object, ...]) -> tuple[dict[int, int], int] | None:
        with self._lock:
            row = self._rows.get(key)
            if row is None:
                return None
            self._rows.move_to_end(key)
            cell_times, seed_count = row
            return dict(cell_times), int(seed_count)

    def put(self, key: tuple[object, ...], cell_times: dict[int, int], seed_count: int) -> None:
        with self._lock:
            self._rows[key] = (dict(cell_times), int(seed_count))
            self._rows.move_to_end(key)
            while len(self._rows) > self.max_entries:
                self._rows.popitem(last=False)


@dataclass(frozen=True)
class CityRuntimeState:
    city_id: str
    label: str
    runtime: RuntimeData
    spatial: SpatialIndex
    topology: GridTopology
    origin_grid_cache: OriginGridCache


def load_app_state() -> dict[str, object]:
    cfg = load_backend_config()

    first_mile_radius = cfg.settings.search.first_mile_radius_m
    first_mile_fallback_k = cfg.settings.search.first_mile_fallback_k
    max_seed_nodes = cfg.settings.runtime.max_seed_nodes
    walk_speed_mps = cfg.settings.weights.walk_speed_mps
    isochrone_bucket_size_s = cfg.settings.runtime.isochrone_bucket_size_s

    cities_by_id: dict[str, CityRuntimeState] = {}
    for city_id, city in sorted(cfg.settings.cities.items()):
        artifacts_dir = get_city_artifacts_dir(cfg, city_id)
        runtime = load_runtime_data(artifacts_dir, version=city.artifact_version)
        spatial = build_spatial_index(runtime, radius_m=first_mile_radius)
        topology = infer_grid_topology(runtime)

        cities_by_id[city_id] = CityRuntimeState(
            city_id=city_id,
            label=city.label,
            runtime=runtime,
            spatial=spatial,
            topology=topology,
            origin_grid_cache=OriginGridCache(max_entries=ORIGIN_GRID_CACHE_MAX_ENTRIES),
        )

    return {
        "config": cfg,
        "cities_by_id": cities_by_id,
        "params": {
            "first_mile_radius_m": first_mile_radius,
            "first_mile_fallback_k": first_mile_fallback_k,
            "max_time_s": SERVER_TIME_CAP_S,
            "max_seed_nodes": max_seed_nodes,
            "walk_speed_mps": walk_speed_mps,
            "isochrone_bucket_size_s": isochrone_bucket_size_s,
            "isochrone_render_max_time_s": SERVER_TIME_CAP_S,
        },
    }


def get_city_runtime_state(app_state: dict[str, object], city_id: str) -> CityRuntimeState | None:
    city_map = app_state.get("cities_by_id")
    if not isinstance(city_map, dict):
        return None
    row = city_map.get(city_id)
    if isinstance(row, CityRuntimeState):
        return row
    return None


def origin_cache_key(
    runtime: RuntimeData,
    *,
    origin_lat: float,
    origin_lon: float,
    max_time_s: int,
) -> tuple[object, ...]:
    return (
        runtime.version,
        runtime.profile,
        round(origin_lat, 5),
        round(origin_lon, 5),
        int(max_time_s),
    )
