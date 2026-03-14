from __future__ import annotations

from typing import Any

from transit_shared.settings import AppSettings

from transit_backend.api.cities import build_public_city_id, get_city_country_code


class InvalidCityRequest(ValueError):
    """Raised when request city is missing or invalid."""


class InvalidPathRequest(ValueError):
    """Raised when request payload is invalid for /multi_path."""


class InvalidIsochroneRequest(ValueError):
    """Raised when request payload is invalid for /multi_isochrones."""


class InvalidWakeupRequest(ValueError):
    """Raised when request payload is invalid for /wakeup."""


MAX_MULTI_ORIGINS = 10


def build_health_payload(settings: AppSettings) -> dict[str, Any]:
    public_city_ids = sorted(
        build_public_city_id(city_id, city)
        for city_id, city in settings.cities.items()
    )
    return {
        "ok": True,
        "cities": public_city_ids,
        "cities_count": len(public_city_ids),
    }


def build_metadata_payload(settings: AppSettings) -> dict[str, Any]:
    return {
        "cities": [
            {
                "id": build_public_city_id(city_id, city),
                "country_code": get_city_country_code(city),
                "default_view": list(city.scope.default_view),
                "bbox": list(city.scope.bbox),
            }
            for city_id, city in sorted(settings.cities.items())
        ],
    }


def _parse_city(
    payload: dict[str, Any],
    error_type: type[ValueError],
) -> str:
    city_raw = payload.get("city")
    if not isinstance(city_raw, str):
        raise error_type("city is required")
    city = city_raw.strip()
    if not city:
        raise error_type("city is required")
    return city


def _parse_point(
    payload: dict[str, Any],
    *,
    lat_key: str,
    lon_key: str,
    error_type: type[ValueError],
) -> tuple[float, float]:
    try:
        lat = float(payload[lat_key])
        lon = float(payload[lon_key])
    except Exception as exc:  # noqa: BLE001
        raise error_type(f"{lat_key} and {lon_key} are required") from exc

    if not (-90.0 <= lat <= 90.0):
        raise error_type(f"{lat_key} out of range")
    if not (-180.0 <= lon <= 180.0):
        raise error_type(f"{lon_key} out of range")
    return lat, lon


def _reject_client_time_fields(
    payload: dict[str, Any],
    error_type: type[ValueError],
    *,
    endpoint_name: str,
) -> None:
    forbidden = {"max_time_s", "compute_max_time_s", "render_max_time_s"}
    for key in forbidden:
        if key in payload:
            raise error_type(f"{key} is not supported for {endpoint_name}; server uses a fixed 1h cap")


def _parse_debug(
    payload: dict[str, Any],
    error_type: type[ValueError],
) -> bool:
    debug_raw = payload.get("debug", False)
    if isinstance(debug_raw, bool):
        return debug_raw
    raise error_type("debug must be a boolean")


def _parse_origins(
    payload: dict[str, Any],
    error_type: type[ValueError],
    *,
    max_origins: int,
) -> list[dict[str, object]]:
    origins_raw = payload.get("origins")
    if not isinstance(origins_raw, list):
        raise error_type("origins must be an array")
    if len(origins_raw) == 0:
        raise error_type("origins must contain at least one origin")
    if len(origins_raw) > max_origins:
        raise error_type(f"origins must contain at most {max_origins} origins")

    origins: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for item in origins_raw:
        if not isinstance(item, dict):
            raise error_type("each origin must be an object")
        origin_id = item.get("id")
        if not isinstance(origin_id, str) or not origin_id.strip():
            raise error_type("each origin must include a non-empty id")
        if origin_id in seen_ids:
            raise error_type("origin ids must be unique")
        seen_ids.add(origin_id)
        lat, lon = _parse_point(
            item,
            lat_key="lat",
            lon_key="lon",
            error_type=error_type,
        )
        origins.append({"id": origin_id, "lat": lat, "lon": lon})
    return origins


def parse_multi_isochrones_request(
    payload: dict[str, Any],
    *,
    max_origins: int = MAX_MULTI_ORIGINS,
) -> tuple[str, list[dict[str, object]], bool]:
    city = _parse_city(payload, InvalidIsochroneRequest)
    _reject_client_time_fields(payload, InvalidIsochroneRequest, endpoint_name="/multi_isochrones")
    debug = _parse_debug(payload, InvalidIsochroneRequest)
    return city, _parse_origins(payload, InvalidIsochroneRequest, max_origins=max_origins), debug


def parse_multi_path_request(
    payload: dict[str, Any],
    *,
    max_origins: int = MAX_MULTI_ORIGINS,
) -> tuple[str, list[dict[str, object]], float, float, bool]:
    city = _parse_city(payload, InvalidPathRequest)
    _reject_client_time_fields(payload, InvalidPathRequest, endpoint_name="/multi_path")
    debug = _parse_debug(payload, InvalidPathRequest)
    origins = _parse_origins(payload, InvalidPathRequest, max_origins=max_origins)

    destination = payload.get("destination")
    if not isinstance(destination, dict):
        raise InvalidPathRequest("destination must be an object with lat and lon")
    destination_lat, destination_lon = _parse_point(
        destination,
        lat_key="lat",
        lon_key="lon",
        error_type=InvalidPathRequest,
    )
    return city, origins, destination_lat, destination_lon, debug


def parse_wakeup_request(payload: dict[str, Any]) -> str:
    return _parse_city(payload, InvalidWakeupRequest)
