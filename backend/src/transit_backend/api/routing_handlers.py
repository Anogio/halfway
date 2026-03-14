from __future__ import annotations

from fastapi import HTTPException

from transit_backend.api.cities import resolve_internal_city_id
from transit_backend.api.contracts import (
    InvalidIsochroneRequest,
    InvalidPathRequest,
    InvalidWakeupRequest,
    parse_multi_isochrones_request,
    parse_multi_path_request,
    parse_wakeup_request,
)
from transit_backend.api.state import (
    CityRuntimeState,
    get_city_runtime_manager,
    origin_cache_key,
)
from transit_backend.core.routing import (
    compute_multi_isochrones,
    compute_multi_path,
    compute_origin_cell_times,
)

AppState = dict[str, object]


def _resolve_internal_city_id(app_state: AppState, request_city_id: str) -> str:
    cfg = app_state.get("config")
    if cfg is None or not hasattr(cfg, "settings"):
        raise HTTPException(status_code=500, detail="invalid server state")

    city_id = resolve_internal_city_id(cfg.settings, request_city_id)
    if city_id is None:
        raise HTTPException(status_code=400, detail="unknown city")
    return city_id


def build_multi_isochrones_response(
    app_state: AppState,
    payload: dict[str, object],
) -> dict[str, object]:
    try:
        city_id, origins, debug = parse_multi_isochrones_request(payload)
    except InvalidIsochroneRequest as exc:
        raise HTTPException(status_code=400, detail="invalid request body") from exc

    city_id = _resolve_internal_city_id(app_state, city_id)
    manager = get_city_runtime_manager(app_state)
    with manager.use_city(city_id) as city_state:
        return compute_multi_isochrones_response(app_state, city_state, origins, include_stats=debug)


def build_multi_path_response(app_state: AppState, payload: dict[str, object]) -> dict[str, object]:
    params = app_state["params"]
    try:
        city_id, origins, destination_lat, destination_lon, debug = parse_multi_path_request(payload)
    except InvalidPathRequest as exc:
        raise HTTPException(status_code=400, detail="invalid request body") from exc

    city_id = _resolve_internal_city_id(app_state, city_id)
    manager = get_city_runtime_manager(app_state)
    with manager.use_city(city_id) as city_state:
        return compute_multi_path(
            city_state.runtime,
            city_state.spatial,
            origins=origins,
            destination_lat=destination_lat,
            destination_lon=destination_lon,
            first_mile_radius_m=params["first_mile_radius_m"],
            first_mile_fallback_k=params["first_mile_fallback_k"],
            max_seed_nodes=params["max_seed_nodes"],
            walk_speed_mps=params["walk_speed_mps"],
            max_time_s=int(params["max_time_s"]),
            include_stats=debug,
        )


def build_wakeup_response(app_state: AppState, payload: dict[str, object]) -> dict[str, object]:
    try:
        city_id = parse_wakeup_request(payload)
    except InvalidWakeupRequest as exc:
        raise HTTPException(status_code=400, detail="invalid request body") from exc

    city_id = _resolve_internal_city_id(app_state, city_id)
    manager = get_city_runtime_manager(app_state)
    manager.trigger_wakeup(city_id)
    return {"ok": True}


def compute_multi_isochrones_response(
    app_state: AppState,
    city_state: CityRuntimeState,
    origins: list[dict[str, object]],
    *,
    include_stats: bool,
) -> dict[str, object]:
    params = app_state["params"]
    runtime = city_state.runtime
    cache = city_state.origin_grid_cache
    max_time_s = int(params["max_time_s"])

    cached_origin_cells: dict[str, dict[int, int]] = {}
    cached_seed_counts: dict[str, int] | None = {} if include_stats else None
    for origin in origins:
        origin_id = str(origin["id"])
        origin_lat = float(origin["lat"])
        origin_lon = float(origin["lon"])
        cache_key = origin_cache_key(
            runtime,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            max_time_s=max_time_s,
        )
        cache_row = cache.get(cache_key)
        if cache_row is None:
            origin_grid = compute_origin_cell_times(
                runtime,
                city_state.spatial,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                first_mile_radius_m=params["first_mile_radius_m"],
                first_mile_fallback_k=params["first_mile_fallback_k"],
                max_seed_nodes=params["max_seed_nodes"],
                walk_speed_mps=params["walk_speed_mps"],
                max_time_s=max_time_s,
            )
            cell_times = dict(origin_grid["cell_times"])
            seed_count = int(origin_grid["seed_count"])
            cache.put(cache_key, cell_times=cell_times, seed_count=seed_count)
        else:
            cell_times, seed_count = cache_row

        cached_origin_cells[origin_id] = dict(cell_times)
        if cached_seed_counts is not None:
            cached_seed_counts[origin_id] = int(seed_count)

    return compute_multi_isochrones(
        runtime,
        city_state.spatial,
        city_state.topology,
        origins=origins,
        first_mile_radius_m=params["first_mile_radius_m"],
        first_mile_fallback_k=params["first_mile_fallback_k"],
        max_seed_nodes=params["max_seed_nodes"],
        walk_speed_mps=params["walk_speed_mps"],
        max_time_s=max_time_s,
        bucket_size_s=int(params["isochrone_bucket_size_s"]),
        cached_origin_cells=cached_origin_cells,
        cached_seed_counts=cached_seed_counts,
        include_stats=include_stats,
    )
