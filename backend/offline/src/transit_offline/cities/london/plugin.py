from __future__ import annotations

import re

from transit_offline.cities.base import CityPlugin

_NIGHT_BUS_RE = re.compile(r"^N", re.IGNORECASE)
_REPLACEMENT_BUS_RE = re.compile(r"^UL", re.IGNORECASE)

KNOWN_LINE_PREFIXES = {
    "Bakerloo",
    "Central",
    "Circle",
    "District",
    "DLR",
    "Elizabeth line",
    "Hammersmith & City",
    "Jubilee",
    "Lioness",
    "Liberty",
    "Metropolitan",
    "Mildmay",
    "Northern",
    "Piccadilly",
    "Suffragette",
    "Victoria",
    "Waterloo & City",
    "Weaver",
    "Windrush",
}

BUS_ROUTE_TYPES = {
    "3",
    "700",
    "701",
    "702",
    "703",
    "704",
    "705",
    "706",
    "707",
    "708",
    "709",
    "710",
    "711",
    "712",
    "713",
    "714",
    "715",
    "716",
}

STOP_SUFFIXES = (
    " Underground Station",
    " Rail Station",
    " DLR Station",
    " Overground Station",
)


def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def _bus_label(value: str) -> str:
    normalized = _collapse_ws(value)
    if not normalized:
        return normalized
    if normalized.lower().endswith(" bus"):
        return normalized
    return f"{normalized} bus"


def _clean_stop_name(value: str) -> str:
    cleaned = _collapse_ws(value)
    for suffix in STOP_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            break
    return _collapse_ws(cleaned)


class LondonCityPlugin(CityPlugin):
    city_id = "london"

    def filter_route_row(self, row: dict[str, str]) -> bool:
        route_type = (row.get("route_type") or "").strip()
        short_name = (row.get("route_short_name") or "").strip()
        long_name = (row.get("route_long_name") or "").strip()
        if route_type != "3":
            return True
        if _NIGHT_BUS_RE.match(short_name) or _NIGHT_BUS_RE.match(long_name):
            return False
        if _REPLACEMENT_BUS_RE.match(short_name) or _REPLACEMENT_BUS_RE.match(long_name):
            return False
        return True

    def format_route_label(
        self,
        *,
        route_id: str,
        short_name: str,
        long_name: str,
        route_type: str,
    ) -> str:
        short = _collapse_ws(short_name)
        long = _collapse_ws(long_name)

        if route_type in BUS_ROUTE_TYPES:
            if short:
                return _bus_label(short)
            if long:
                return _bus_label(long)
            return _bus_label(route_id)

        if short:
            return short

        if not long:
            return route_id

        prefix, sep, _ = long.partition(" - ")
        if sep and prefix in KNOWN_LINE_PREFIXES:
            return prefix
        return long

    def normalize_stop_name(
        self,
        *,
        stop_id: str,
        stop_name: str,
        parent_station: str,
        location_type: str,
    ) -> str:
        return _clean_stop_name(stop_name) or stop_id
