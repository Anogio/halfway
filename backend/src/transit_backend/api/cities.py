from __future__ import annotations

from transit_shared.settings import AppSettings, CitySettings

_CITY_ID_SUFFIX_OVERRIDES = {
    "gb": "uk",
}


def get_city_country_code(city: CitySettings) -> str:
    raw_value = city.geocoding.country_codes.split(",", 1)[0]
    return raw_value.strip().lower()


def build_public_city_id(city_id: str, city: CitySettings) -> str:
    country_code = get_city_country_code(city)
    suffix = _CITY_ID_SUFFIX_OVERRIDES.get(country_code, country_code)
    if city_id.endswith(f"_{suffix}"):
        return city_id
    return f"{city_id}_{suffix}"


def resolve_internal_city_id(settings: AppSettings, request_city_id: str) -> str | None:
    normalized_request_city_id = request_city_id.strip().lower()
    if not normalized_request_city_id:
        return None

    for internal_city_id, city in settings.cities.items():
        public_city_id = build_public_city_id(internal_city_id, city)
        if public_city_id == normalized_request_city_id:
            return internal_city_id

    return None
