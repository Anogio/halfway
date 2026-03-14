from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from transit_backend.api.cities import resolve_internal_city_id

router = APIRouter()

GEOCODE_MAX_RESULTS = 8
GEOCODE_PROVIDER_TIMEOUT_S = 4.0
GEOCODE_PROVIDER_URL = os.environ.get(
    "GEOCODE_PROVIDER_URL",
    "https://nominatim.openstreetmap.org/search",
)
REVERSE_GEOCODE_PROVIDER_URL = os.environ.get(
    "REVERSE_GEOCODE_PROVIDER_URL",
    "https://nominatim.openstreetmap.org/reverse",
)
GEOCODE_USER_AGENT = os.environ.get("GEOCODE_USER_AGENT", "commute-app/1.0")
GEOCODE_ACCEPT_LANGUAGE = os.environ.get("GEOCODE_ACCEPT_LANGUAGE", "en")


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _format_geocode_label(raw_item: dict[str, object], display_name: str) -> str:
    display_parts = [part.strip() for part in display_name.split(",") if part.strip()]
    address_raw = raw_item.get("address")
    if isinstance(address_raw, dict):
        house_number = _first_non_empty(address_raw.get("house_number"))
        road = _first_non_empty(
            address_raw.get("road"),
            address_raw.get("pedestrian"),
            address_raw.get("footway"),
            address_raw.get("street"),
            address_raw.get("residential"),
            address_raw.get("path"),
            address_raw.get("cycleway"),
        )
        if house_number and not road and len(display_parts) >= 2:
            if display_parts[0] == house_number:
                road = display_parts[1]
        street = ""
        if house_number and road:
            street = f"{house_number} {road}"
        elif road:
            street = road
        elif house_number:
            street = house_number

        city = _first_non_empty(
            address_raw.get("city"),
            address_raw.get("town"),
            address_raw.get("village"),
            address_raw.get("municipality"),
            address_raw.get("hamlet"),
        )
        if street and city and street != city:
            return f"{street}, {city}"
        if street:
            return street
        if city:
            return city

    if not display_parts:
        return display_name
    if len(display_parts) >= 2:
        first_part = display_parts[0]
        second_part = display_parts[1]
        if first_part.replace(" ", "").isalnum() and any(ch.isdigit() for ch in first_part):
            return f"{first_part} {second_part}".strip()
        return f"{first_part}, {second_part}"
    if len(display_parts) == 1:
        return display_parts[0]
    return display_parts[0]


async def _fetch_geocode_payload(provider_url: str, provider_params: dict[str, object]) -> object:
    try:
        async with httpx.AsyncClient(timeout=GEOCODE_PROVIDER_TIMEOUT_S) as client:
            response = await client.get(
                provider_url,
                params=provider_params,
                headers={
                    "User-Agent": GEOCODE_USER_AGENT,
                    "Accept-Language": GEOCODE_ACCEPT_LANGUAGE,
                },
            )
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="geocoding provider unavailable") from exc


def _resolve_city_settings(request: Request, city: str) -> tuple[str, object]:
    request_city_id = city.strip()
    if not request_city_id:
        raise HTTPException(status_code=400, detail="city is required")

    app_state = getattr(request.app.state, "app_state", None)
    if not isinstance(app_state, dict):
        raise HTTPException(status_code=500, detail="invalid server state")

    cfg = app_state.get("config")
    if cfg is None or not hasattr(cfg, "settings"):
        raise HTTPException(status_code=500, detail="invalid server state")

    city_id = resolve_internal_city_id(cfg.settings, request_city_id)
    if city_id is None:
        raise HTTPException(status_code=400, detail="unknown city")

    city_cfg = cfg.settings.cities.get(city_id)
    if city_cfg is None:
        raise HTTPException(status_code=400, detail="unknown city")

    return city_id, city_cfg


@router.get("/geocode")
async def get_geocode(
    request: Request,
    city: str = Query(..., min_length=1, max_length=64),
    q: str = Query("", max_length=200),
) -> dict[str, object]:
    _, city_cfg = _resolve_city_settings(request, city)

    query = q.strip()
    if len(query) < 3:
        return {"results": []}

    provider_params: dict[str, object] = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": GEOCODE_MAX_RESULTS,
        "countrycodes": city_cfg.geocoding.country_codes,
        "viewbox": city_cfg.geocoding.viewbox,
        "bounded": "1" if city_cfg.geocoding.bounded else "0",
    }

    payload = await _fetch_geocode_payload(GEOCODE_PROVIDER_URL, provider_params)
    if not isinstance(payload, list):
        raise HTTPException(status_code=502, detail="geocoding provider unavailable")

    results: list[dict[str, object]] = []
    for raw_item in payload:
        if not isinstance(raw_item, dict):
            continue
        display_name = str(raw_item.get("display_name", "")).strip()
        if not display_name:
            continue
        label = _format_geocode_label(raw_item, display_name)
        try:
            lat = round(float(raw_item.get("lat")), 5)
            lon = round(float(raw_item.get("lon")), 5)
        except (TypeError, ValueError):
            continue
        place_id = str(raw_item.get("place_id", "")).strip()
        osm_type = str(raw_item.get("osm_type", "")).strip()
        osm_id = str(raw_item.get("osm_id", "")).strip()
        result_id = place_id or f"{osm_type}:{osm_id}"
        if not result_id:
            result_id = f"{lat}:{lon}:{len(results)}"
        results.append(
            {
                "id": result_id,
                "label": label,
                "lat": lat,
                "lon": lon,
            }
        )
        if len(results) >= GEOCODE_MAX_RESULTS:
            break

    return {"results": results}


@router.get("/reverse_geocode")
async def get_reverse_geocode(
    request: Request,
    city: str = Query(..., min_length=1, max_length=64),
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
) -> dict[str, object]:
    _resolve_city_settings(request, city)

    payload = await _fetch_geocode_payload(
        REVERSE_GEOCODE_PROVIDER_URL,
        {
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "format": "jsonv2",
            "addressdetails": 1,
        },
    )
    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="geocoding provider unavailable")

    display_name = str(payload.get("display_name", "")).strip()
    if not display_name:
        raise HTTPException(status_code=404, detail="address not found")

    label = _format_geocode_label(payload, display_name).strip()
    if not label:
        raise HTTPException(status_code=404, detail="address not found")

    return {"label": label}
