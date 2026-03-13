from __future__ import annotations

from copy import deepcopy

from transit_shared.settings import AppSettings, parse_settings

_BASE_SETTINGS_DATA = {
    "project": {"name": "transportation-heatmap"},
    "paths": {
        "offline_raw_dir": "backend/offline/data/raw",
        "offline_interim_dir": "backend/offline/data/interim",
        "offline_artifacts_dir": "backend/offline/data/artifacts",
    },
    "service": {"weekdays_only": True, "exclude_holidays": True},
    "modes": {"include_route_types": [0, 1, 2, 3, 6, 7], "include_all_bus": True},
    "search": {
        "first_mile_radius_m": 800,
        "first_mile_fallback_k": 3,
        "transfer_fallback_radius_m": 250,
        "transfer_fallback_max_neighbors": 8,
        "grid_candidate_radius_m": 500,
    },
    "weights": {"walk_speed_mps": 1.2, "transfer_penalty_s": 180, "wait_cap_s": 600},
    "grid": {"cell_size_m": 250, "max_candidates_per_cell": 12},
    "runtime": {"max_time_s": 3600, "max_seed_nodes": 24, "isochrone_bucket_size_s": 300},
    "graph": {"max_interstop_ride_s": 10800},
    "cities": {
        "paris": {
            "label": "Paris",
            "artifact_version": "vtest",
            "paths": {
                "gtfs_input": "backend/offline/data/gtfs/paris",
            },
            "scope": {
                "use_bbox": False,
                "bbox": [1.0, 48.0, 3.0, 49.0],
                "default_view": [48.8566, 2.3522, 10],
            },
            "geocoding": {
                "country_codes": "fr",
                "viewbox": "1.4472,48.1201,3.5590,49.2415",
                "bounded": True,
            },
            "validation": {
                "mape_threshold": 0.2,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 1500,
                "od_pairs": [
                    {
                        "name": "pair",
                        "from_lat": 48.85,
                        "from_lon": 2.35,
                        "to_lat": 48.86,
                        "to_lon": 2.36,
                        "expected_min_s": 600,
                        "expected_max_s": 1800,
                    }
                ],
            },
        },
    },
}


def make_settings_data(*, artifact_version: str = "vtest") -> dict[str, object]:
    data = deepcopy(_BASE_SETTINGS_DATA)
    data["cities"]["paris"]["artifact_version"] = artifact_version
    return data


def make_settings(*, artifact_version: str = "vtest") -> AppSettings:
    return parse_settings(make_settings_data(artifact_version=artifact_version))
