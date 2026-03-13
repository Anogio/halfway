from __future__ import annotations

from dataclasses import dataclass


class SettingsError(ValueError):
    """Raised when settings.toml is invalid or incomplete."""


@dataclass(frozen=True)
class ProjectSettings:
    name: str


@dataclass(frozen=True)
class PathsSettings:
    offline_raw_dir: str
    offline_interim_dir: str
    offline_artifacts_dir: str


@dataclass(frozen=True)
class CityPathsSettings:
    gtfs_input: str


@dataclass(frozen=True)
class CityScopeSettings:
    use_bbox: bool
    bbox: tuple[float, float, float, float]
    default_view: tuple[float, float, int]


@dataclass(frozen=True)
class ServiceSettings:
    weekdays_only: bool
    exclude_holidays: bool


@dataclass(frozen=True)
class ModesSettings:
    include_route_types: tuple[str, ...]
    include_all_bus: bool


@dataclass(frozen=True)
class SearchSettings:
    first_mile_radius_m: float
    first_mile_fallback_k: int
    transfer_fallback_radius_m: float
    transfer_fallback_max_neighbors: int
    grid_candidate_radius_m: float


@dataclass(frozen=True)
class WeightSettings:
    walk_speed_mps: float
    transfer_penalty_s: int
    wait_cap_s: int


@dataclass(frozen=True)
class GridSettings:
    cell_size_m: float
    max_candidates_per_cell: int


@dataclass(frozen=True)
class RuntimeSettings:
    max_time_s: int
    max_seed_nodes: int
    isochrone_bucket_size_s: int


@dataclass(frozen=True)
class GraphSettings:
    max_interstop_ride_s: int


@dataclass(frozen=True)
class ValidationODPair:
    name: str
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    expected_min_s: int
    expected_max_s: int


@dataclass(frozen=True)
class ValidationSettings:
    mape_threshold: float
    range_tolerance_ratio: float
    performance_p95_ms_threshold: float
    od_pairs: tuple[ValidationODPair, ...]


@dataclass(frozen=True)
class CityGeocodingSettings:
    country_codes: str
    viewbox: str
    bounded: bool


@dataclass(frozen=True)
class CitySettings:
    label: str
    artifact_version: str
    paths: CityPathsSettings
    scope: CityScopeSettings
    validation: ValidationSettings
    geocoding: CityGeocodingSettings


@dataclass(frozen=True)
class AppSettings:
    project: ProjectSettings
    paths: PathsSettings
    service: ServiceSettings
    modes: ModesSettings
    search: SearchSettings
    weights: WeightSettings
    grid: GridSettings
    runtime: RuntimeSettings
    graph: GraphSettings
    cities: dict[str, CitySettings]
