from __future__ import annotations

from typing import Any, Mapping, Sequence

from transit_shared.settings_coercion import (
    as_bool as _as_bool,
    as_float as _as_float,
    as_float_tuple as _as_float_tuple,
    as_int as _as_int,
    as_str as _as_str,
    get_required as _get_required,
    get_section as _get_section,
)
from transit_shared.settings_schema import (
    AppSettings,
    CityGeocodingSettings,
    CityPathsSettings,
    CityScopeSettings,
    CitySettings,
    GraphSettings,
    GridSettings,
    ModesSettings,
    PathsSettings,
    ProjectSettings,
    RuntimeSettings,
    SearchSettings,
    ServiceSettings,
    SettingsError,
    ValidationODPair,
    ValidationSettings,
    WeightSettings,
)


def _parse_validation_settings(
    validation: Mapping[str, Any],
    *,
    prefix: str,
) -> ValidationSettings:
    od_pairs_raw = _get_required(validation, "od_pairs")
    if not isinstance(od_pairs_raw, Sequence):
        raise SettingsError(f"{prefix}.od_pairs must be an array")

    od_pairs = []
    for idx, row in enumerate(od_pairs_raw):
        if not isinstance(row, Mapping):
            raise SettingsError(f"{prefix}.od_pairs[{idx}] must be an object")
        od_pairs.append(
            ValidationODPair(
                name=_as_str(_get_required(row, "name"), f"{prefix}.od_pairs[{idx}].name"),
                from_lat=_as_float(_get_required(row, "from_lat"), f"{prefix}.od_pairs[{idx}].from_lat"),
                from_lon=_as_float(_get_required(row, "from_lon"), f"{prefix}.od_pairs[{idx}].from_lon"),
                to_lat=_as_float(_get_required(row, "to_lat"), f"{prefix}.od_pairs[{idx}].to_lat"),
                to_lon=_as_float(_get_required(row, "to_lon"), f"{prefix}.od_pairs[{idx}].to_lon"),
                expected_min_s=_as_int(
                    _get_required(row, "expected_min_s"),
                    f"{prefix}.od_pairs[{idx}].expected_min_s",
                ),
                expected_max_s=_as_int(
                    _get_required(row, "expected_max_s"),
                    f"{prefix}.od_pairs[{idx}].expected_max_s",
                ),
            )
        )

    return ValidationSettings(
        mape_threshold=_as_float(
            _get_required(validation, "mape_threshold"),
            f"{prefix}.mape_threshold",
        ),
        range_tolerance_ratio=_as_float(
            _get_required(validation, "range_tolerance_ratio"),
            f"{prefix}.range_tolerance_ratio",
        ),
        performance_p95_ms_threshold=_as_float(
            _get_required(validation, "performance_p95_ms_threshold"),
            f"{prefix}.performance_p95_ms_threshold",
        ),
        od_pairs=tuple(od_pairs),
    )


def parse_settings(data: Mapping[str, Any]) -> AppSettings:
    project = _get_section(data, "project")
    paths = _get_section(data, "paths")
    service = _get_section(data, "service")
    modes = _get_section(data, "modes")
    search = _get_section(data, "search")
    weights = _get_section(data, "weights")
    grid = _get_section(data, "grid")
    runtime = _get_section(data, "runtime")
    graph = _get_section(data, "graph")
    cities_raw = _get_required(data, "cities")

    if not isinstance(cities_raw, Mapping):
        raise SettingsError("cities must be an object")
    if not cities_raw:
        raise SettingsError("cities must contain at least one city")

    include_route_types_raw = _get_required(modes, "include_route_types")
    if not isinstance(include_route_types_raw, Sequence):
        raise SettingsError("modes.include_route_types must be an array")
    include_route_types = tuple(str(v).strip() for v in include_route_types_raw if str(v).strip())
    if not include_route_types:
        raise SettingsError("modes.include_route_types must not be empty")

    cities: dict[str, CitySettings] = {}
    for city_id_raw, city_data in cities_raw.items():
        city_id = str(city_id_raw).strip()
        if not city_id:
            raise SettingsError("cities contains an empty city id")
        if city_id in cities:
            raise SettingsError(f"duplicate city id: {city_id}")
        if not isinstance(city_data, Mapping):
            raise SettingsError(f"cities.{city_id} must be an object")

        city_paths = _get_section(city_data, "paths")
        city_scope = _get_section(city_data, "scope")
        city_validation = _get_section(city_data, "validation")
        city_geocoding = _get_section(city_data, "geocoding")

        bbox = _as_float_tuple(_get_required(city_scope, "bbox"), name=f"cities.{city_id}.scope.bbox", size=4)
        view = _as_float_tuple(
            _get_required(city_scope, "default_view"),
            name=f"cities.{city_id}.scope.default_view",
            size=3,
        )

        cities[city_id] = CitySettings(
            label=_as_str(_get_required(city_data, "label"), f"cities.{city_id}.label"),
            artifact_version=_as_str(
                _get_required(city_data, "artifact_version"),
                f"cities.{city_id}.artifact_version",
            ),
            paths=CityPathsSettings(
                gtfs_input=_as_str(_get_required(city_paths, "gtfs_input"), f"cities.{city_id}.paths.gtfs_input"),
            ),
            scope=CityScopeSettings(
                use_bbox=_as_bool(_get_required(city_scope, "use_bbox"), f"cities.{city_id}.scope.use_bbox"),
                bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                default_view=(view[0], view[1], int(round(view[2]))),
            ),
            validation=_parse_validation_settings(
                city_validation,
                prefix=f"cities.{city_id}.validation",
            ),
            geocoding=CityGeocodingSettings(
                country_codes=_as_str(
                    _get_required(city_geocoding, "country_codes"),
                    f"cities.{city_id}.geocoding.country_codes",
                ),
                viewbox=_as_str(
                    _get_required(city_geocoding, "viewbox"),
                    f"cities.{city_id}.geocoding.viewbox",
                ),
                bounded=_as_bool(
                    _get_required(city_geocoding, "bounded"),
                    f"cities.{city_id}.geocoding.bounded",
                ),
            ),
        )

    return AppSettings(
        project=ProjectSettings(
            name=_as_str(_get_required(project, "name"), "project.name"),
        ),
        paths=PathsSettings(
            offline_raw_dir=_as_str(_get_required(paths, "offline_raw_dir"), "paths.offline_raw_dir"),
            offline_interim_dir=_as_str(
                _get_required(paths, "offline_interim_dir"),
                "paths.offline_interim_dir",
            ),
            offline_artifacts_dir=_as_str(
                _get_required(paths, "offline_artifacts_dir"),
                "paths.offline_artifacts_dir",
            ),
        ),
        service=ServiceSettings(
            weekdays_only=_as_bool(_get_required(service, "weekdays_only"), "service.weekdays_only"),
            exclude_holidays=_as_bool(_get_required(service, "exclude_holidays"), "service.exclude_holidays"),
        ),
        modes=ModesSettings(
            include_route_types=include_route_types,
            include_all_bus=_as_bool(_get_required(modes, "include_all_bus"), "modes.include_all_bus"),
        ),
        search=SearchSettings(
            first_mile_radius_m=_as_float(
                _get_required(search, "first_mile_radius_m"),
                "search.first_mile_radius_m",
            ),
            first_mile_fallback_k=_as_int(
                _get_required(search, "first_mile_fallback_k"),
                "search.first_mile_fallback_k",
            ),
            transfer_fallback_radius_m=_as_float(
                _get_required(search, "transfer_fallback_radius_m"),
                "search.transfer_fallback_radius_m",
            ),
            transfer_fallback_max_neighbors=_as_int(
                _get_required(search, "transfer_fallback_max_neighbors"),
                "search.transfer_fallback_max_neighbors",
            ),
            grid_candidate_radius_m=_as_float(
                _get_required(search, "grid_candidate_radius_m"),
                "search.grid_candidate_radius_m",
            ),
        ),
        weights=WeightSettings(
            walk_speed_mps=_as_float(_get_required(weights, "walk_speed_mps"), "weights.walk_speed_mps"),
            transfer_penalty_s=_as_int(
                _get_required(weights, "transfer_penalty_s"),
                "weights.transfer_penalty_s",
            ),
            wait_cap_s=_as_int(_get_required(weights, "wait_cap_s"), "weights.wait_cap_s"),
        ),
        grid=GridSettings(
            cell_size_m=_as_float(_get_required(grid, "cell_size_m"), "grid.cell_size_m"),
            max_candidates_per_cell=_as_int(
                _get_required(grid, "max_candidates_per_cell"),
                "grid.max_candidates_per_cell",
            ),
        ),
        runtime=RuntimeSettings(
            max_time_s=_as_int(_get_required(runtime, "max_time_s"), "runtime.max_time_s"),
            max_seed_nodes=_as_int(_get_required(runtime, "max_seed_nodes"), "runtime.max_seed_nodes"),
            isochrone_bucket_size_s=_as_int(
                _get_required(runtime, "isochrone_bucket_size_s"),
                "runtime.isochrone_bucket_size_s",
            ),
        ),
        graph=GraphSettings(
            max_interstop_ride_s=_as_int(
                _get_required(graph, "max_interstop_ride_s"),
                "graph.max_interstop_ride_s",
            )
        ),
        cities=cities,
    )
