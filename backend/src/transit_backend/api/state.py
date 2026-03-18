from __future__ import annotations

import gc
import os
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import Condition, Event, Lock, RLock, Thread
from time import monotonic
from typing import Any

from transit_backend.api.cities import build_public_city_id, get_city_country_code
from transit_backend.config.settings import get_city_artifacts_dir, load_backend_config
from transit_backend.core.artifacts import RuntimeData, load_runtime_data
from transit_backend.core.isochrones import GridTopology, infer_grid_topology
from transit_backend.core.routing import SpatialIndex, build_spatial_index
from transit_shared.settings import AppSettings

SERVER_TIME_CAP_S = 3600
ORIGIN_GRID_CACHE_MAX_ENTRIES = 128
CITY_RUNTIME_IDLE_TTL_S = 600.0
CITY_RUNTIME_REAPER_INTERVAL_S = 60.0

AppState = dict[str, object]
RuntimeLoader = Callable[[str], "CityRuntimeState"]


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

    def snapshot_stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._rows),
                "max_entries": self.max_entries,
            }


@dataclass(frozen=True)
class CityRuntimeState:
    city_id: str
    label: str
    runtime: RuntimeData
    spatial: SpatialIndex
    topology: GridTopology
    origin_grid_cache: OriginGridCache


@dataclass
class ManagedCityEntry:
    city_id: str
    label: str
    loaded_state: CityRuntimeState | None = None
    last_active_at: float | None = None
    inflight_requests: int = 0
    loading: bool = False


@dataclass
class CityRuntimeManager:
    settings: AppSettings
    runtime_loader: RuntimeLoader
    idle_ttl_s: float = CITY_RUNTIME_IDLE_TTL_S
    reaper_interval_s: float = CITY_RUNTIME_REAPER_INTERVAL_S
    _entries: dict[str, ManagedCityEntry] = field(init=False)
    _lock: RLock = field(default_factory=RLock, init=False)
    _condition: Condition = field(init=False)
    _stop_event: Event = field(default_factory=Event, init=False)
    _reaper_thread: Thread | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._entries = {
            city_id: ManagedCityEntry(city_id=city_id, label=city.label)
            for city_id, city in sorted(self.settings.cities.items())
        }
        self._condition = Condition(self._lock)

    @contextmanager
    def use_city(self, city_id: str) -> Iterator[CityRuntimeState]:
        city_state = self._acquire_city(city_id)
        try:
            yield city_state
        finally:
            self._release_city(city_id)

    def get_loaded_city_state(self, city_id: str) -> CityRuntimeState | None:
        with self._condition:
            entry = self._entries.get(city_id)
            return None if entry is None else entry.loaded_state

    def snapshot_loaded_city_ids(self) -> list[str]:
        with self._condition:
            return sorted(
                city_id
                for city_id, entry in self._entries.items()
                if entry.loaded_state is not None
            )

    def snapshot_debug_info(self, *, now: float | None = None) -> dict[str, object]:
        current = monotonic() if now is None else float(now)
        with self._condition:
            cities: list[dict[str, object]] = []
            loaded_city_ids: list[str] = []
            for city_id, entry in sorted(self._entries.items()):
                last_active_at = None if entry.last_active_at is None else float(entry.last_active_at)
                idle_for_s = None
                if last_active_at is not None:
                    idle_for_s = round(max(0.0, current - last_active_at), 3)
                runtime_snapshot = None
                if entry.loaded_state is not None:
                    loaded_city_ids.append(city_id)
                    runtime_snapshot = _snapshot_city_runtime_state(entry.loaded_state)
                cities.append(
                    {
                        "city_id": city_id,
                        "label": entry.label,
                        "loaded": entry.loaded_state is not None,
                        "loading": entry.loading,
                        "inflight_requests": entry.inflight_requests,
                        "last_active_at": last_active_at,
                        "idle_for_s": idle_for_s,
                        "runtime": runtime_snapshot,
                    }
                )

        return {
            "snapshot_at_monotonic_s": round(current, 6),
            "known_city_count": len(cities),
            "loaded_city_count": len(loaded_city_ids),
            "loaded_city_ids": loaded_city_ids,
            "idle_ttl_s": self.idle_ttl_s,
            "reaper_interval_s": self.reaper_interval_s,
            "cities": cities,
        }

    def unload_idle_cities(self, *, now: float | None = None) -> list[str]:
        unloaded: list[str] = []
        current = monotonic() if now is None else float(now)
        with self._condition:
            for city_id, entry in self._entries.items():
                if entry.loaded_state is None or entry.loading or entry.inflight_requests > 0:
                    continue
                if entry.last_active_at is None:
                    continue
                if current - entry.last_active_at < self.idle_ttl_s:
                    continue
                entry.loaded_state = None
                entry.last_active_at = None
                unloaded.append(city_id)
            if unloaded:
                self._condition.notify_all()
        if unloaded:
            gc.collect()
        return unloaded

    def start_reaper(self) -> None:
        with self._condition:
            if self._reaper_thread is not None and self._reaper_thread.is_alive():
                return
            self._stop_event.clear()
            self._reaper_thread = Thread(
                target=self._reaper_loop,
                name="city-runtime-reaper",
                daemon=True,
            )
            self._reaper_thread.start()

    def stop_reaper(self) -> None:
        thread: Thread | None
        with self._condition:
            thread = self._reaper_thread
            self._reaper_thread = None
            self._stop_event.set()
            self._condition.notify_all()
        if thread is not None:
            thread.join(timeout=max(1.0, self.reaper_interval_s + 1.0))
        self.unload_all()

    def unload_all(self) -> None:
        with self._condition:
            for entry in self._entries.values():
                entry.loaded_state = None
                entry.last_active_at = None
                entry.loading = False
            self._condition.notify_all()
        gc.collect()

    def trigger_wakeup(self, city_id: str) -> None:
        should_load = False
        with self._condition:
            entry = self._entries.get(city_id)
            if entry is None:
                raise KeyError(city_id)
            entry.last_active_at = monotonic()
            if entry.loaded_state is None and not entry.loading:
                entry.loading = True
                should_load = True
        if should_load:
            Thread(
                target=self._load_in_background,
                args=(city_id,),
                name=f"city-runtime-wakeup-{city_id}",
                daemon=True,
            ).start()

    def _acquire_city(self, city_id: str) -> CityRuntimeState:
        while True:
            with self._condition:
                entry = self._entries.get(city_id)
                if entry is None:
                    raise KeyError(city_id)
                if entry.loaded_state is not None:
                    entry.inflight_requests += 1
                    entry.last_active_at = monotonic()
                    return entry.loaded_state
                if entry.loading:
                    self._condition.wait()
                    continue
                entry.loading = True

            try:
                loaded_state = self.runtime_loader(city_id)
            except Exception:
                with self._condition:
                    entry = self._entries[city_id]
                    entry.loading = False
                    self._condition.notify_all()
                raise

            with self._condition:
                entry = self._entries[city_id]
                entry.loaded_state = loaded_state
                entry.loading = False
                entry.inflight_requests += 1
                entry.last_active_at = monotonic()
                self._condition.notify_all()
                return loaded_state

    def _release_city(self, city_id: str) -> None:
        with self._condition:
            entry = self._entries.get(city_id)
            if entry is None:
                return
            if entry.inflight_requests > 0:
                entry.inflight_requests -= 1
            self._condition.notify_all()

    def _reaper_loop(self) -> None:
        while not self._stop_event.wait(self.reaper_interval_s):
            self.unload_idle_cities()

    def _load_in_background(self, city_id: str) -> None:
        try:
            loaded_state = self.runtime_loader(city_id)
        except Exception:
            with self._condition:
                entry = self._entries.get(city_id)
                if entry is not None:
                    entry.loading = False
                    self._condition.notify_all()
            return

        with self._condition:
            entry = self._entries.get(city_id)
            if entry is None:
                return
            entry.loaded_state = loaded_state
            entry.loading = False
            entry.last_active_at = monotonic()
            self._condition.notify_all()


def load_app_state() -> AppState:
    cfg = load_backend_config()
    return build_app_state(cfg)


def build_app_state(
    config: Any,
    *,
    runtime_loader: RuntimeLoader | None = None,
    idle_ttl_s: float = CITY_RUNTIME_IDLE_TTL_S,
    reaper_interval_s: float = CITY_RUNTIME_REAPER_INTERVAL_S,
) -> AppState:
    if config is None or not hasattr(config, "settings"):
        raise ValueError("config with settings is required")

    settings = config.settings
    first_mile_radius = settings.search.first_mile_radius_m
    first_mile_fallback_k = settings.search.first_mile_fallback_k
    max_seed_nodes = settings.runtime.max_seed_nodes
    walk_speed_mps = settings.weights.walk_speed_mps

    loader = runtime_loader or _build_runtime_loader(config, radius_m=first_mile_radius)
    return {
        "config": config,
        "params": {
            "first_mile_radius_m": first_mile_radius,
            "first_mile_fallback_k": first_mile_fallback_k,
            "max_time_s": SERVER_TIME_CAP_S,
            "max_seed_nodes": max_seed_nodes,
            "walk_speed_mps": walk_speed_mps,
            "isochrone_render_max_time_s": SERVER_TIME_CAP_S,
        },
        "city_runtime_manager": CityRuntimeManager(
            settings=settings,
            runtime_loader=loader,
            idle_ttl_s=idle_ttl_s,
            reaper_interval_s=reaper_interval_s,
        ),
    }


def start_app_runtime(app_state: AppState) -> None:
    get_city_runtime_manager(app_state).start_reaper()


def stop_app_runtime(app_state: AppState) -> None:
    get_city_runtime_manager(app_state).stop_reaper()


def get_city_runtime_manager(app_state: AppState) -> CityRuntimeManager:
    manager = app_state.get("city_runtime_manager")
    if not isinstance(manager, CityRuntimeManager):
        raise RuntimeError("invalid server state")
    return manager


def get_city_runtime_state(app_state: AppState, city_id: str) -> CityRuntimeState | None:
    return get_city_runtime_manager(app_state).get_loaded_city_state(city_id)


def build_runtime_debug_snapshot(app_state: AppState) -> dict[str, object]:
    config = app_state.get("config")
    if config is None or not hasattr(config, "settings"):
        raise RuntimeError("invalid server state")

    settings = config.settings
    manager_snapshot = get_city_runtime_manager(app_state).snapshot_debug_info()
    cities_payload: list[dict[str, object]] = []
    for city_snapshot in manager_snapshot["cities"]:
        if not isinstance(city_snapshot, dict):
            continue
        city_id = city_snapshot.get("city_id")
        if not isinstance(city_id, str):
            continue
        city_settings = settings.cities[city_id]
        city_payload = dict(city_snapshot)
        city_payload["public_city_id"] = build_public_city_id(city_id, city_settings)
        city_payload["country_code"] = get_city_country_code(city_settings)
        city_payload["configured_artifact_version"] = city_settings.artifact_version
        city_payload["artifact_dir"] = _safe_city_artifacts_dir(config, city_id)
        cities_payload.append(city_payload)

    return {
        "manager": {
            key: value
            for key, value in manager_snapshot.items()
            if key != "cities"
        },
        "process": _snapshot_process_info(),
        "cities": cities_payload,
    }


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


def _build_runtime_loader(config: Any, *, radius_m: float) -> RuntimeLoader:
    def _load(city_id: str) -> CityRuntimeState:
        city = config.settings.cities[city_id]
        artifacts_dir = get_city_artifacts_dir(config, city_id)
        runtime = load_runtime_data(artifacts_dir, version=city.artifact_version)
        spatial = build_spatial_index(runtime, radius_m=radius_m)
        topology = infer_grid_topology(runtime)
        return CityRuntimeState(
            city_id=city_id,
            label=city.label,
            runtime=runtime,
            spatial=spatial,
            topology=topology,
            origin_grid_cache=OriginGridCache(max_entries=ORIGIN_GRID_CACHE_MAX_ENTRIES),
        )

    return _load


def _snapshot_city_runtime_state(city_state: CityRuntimeState) -> dict[str, object]:
    runtime = city_state.runtime
    cache_stats = city_state.origin_grid_cache.snapshot_stats()
    return {
        "runtime_version": runtime.version,
        "profile": runtime.profile,
        "node_count": len(runtime.nodes),
        "edge_count": len(runtime.targets),
        "grid_cell_count": len(runtime.grid_cells),
        "grid_link_cell_count": len(runtime.grid_links),
        "grid_link_count": sum(len(links) for links in runtime.grid_links.values()),
        "route_count": len(runtime.route_labels),
        "origin_grid_cache_entries": cache_stats["entries"],
        "origin_grid_cache_max_entries": cache_stats["max_entries"],
        "manifest": _summarize_runtime_manifest(runtime.metadata),
    }


def _summarize_runtime_manifest(metadata: dict[str, object]) -> dict[str, object] | None:
    if not metadata:
        return None

    artifacts = metadata.get("artifacts")
    artifact_count = 0
    artifact_total_size_bytes = 0
    if isinstance(artifacts, list):
        artifact_count = len(artifacts)
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            size_bytes = artifact.get("size_bytes")
            if isinstance(size_bytes, int):
                artifact_total_size_bytes += size_bytes

    counts = metadata.get("counts")
    counts_payload = None
    if isinstance(counts, dict):
        counts_payload = {
            str(key): int(value)
            for key, value in counts.items()
            if isinstance(value, int)
        }

    return {
        "version": metadata.get("version"),
        "profile": metadata.get("profile"),
        "build_timestamp_utc": metadata.get("build_timestamp_utc"),
        "config_hash": metadata.get("config_hash"),
        "city": metadata.get("city"),
        "artifact_count": artifact_count,
        "artifact_total_size_bytes": artifact_total_size_bytes,
        "counts": counts_payload,
    }


def _safe_city_artifacts_dir(config: Any, city_id: str) -> str | None:
    if not hasattr(config, "paths"):
        return None
    try:
        return str(get_city_artifacts_dir(config, city_id))
    except Exception:
        return None


def _snapshot_process_info() -> dict[str, object]:
    rss_bytes, rss_source = _read_process_rss_bytes()
    return {
        "pid": os.getpid(),
        "current_rss_bytes": rss_bytes,
        "current_rss_source": rss_source,
    }


def _read_process_rss_bytes() -> tuple[int | None, str | None]:
    status_path = Path("/proc/self/status")
    if not status_path.exists():
        return None, None

    try:
        for line in status_path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("VmRSS:"):
                continue
            parts = line.split()
            if len(parts) < 2:
                return None, None
            return int(parts[1]) * 1024, "procfs_status"
    except (OSError, ValueError):
        return None, None

    return None, None
