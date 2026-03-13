from __future__ import annotations

import re

from transit_offline.cities.base import CityPlugin

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

_NIGHT_BUS_RE = re.compile(r"^N(?:C)?\d+[A-Z]?$", re.IGNORECASE)


def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def _bus_label(value: str) -> str:
    normalized = _collapse_ws(value)
    if not normalized:
        return normalized
    if normalized.lower().endswith(" bus"):
        return normalized
    return f"{normalized} bus"


class MadridCityPlugin(CityPlugin):
    city_id = "madrid"

    def filter_route_row(self, row: dict[str, str]) -> bool:
        route_type = (row.get("route_type") or "").strip()
        if route_type not in BUS_ROUTE_TYPES:
            return True
        short_name = _collapse_ws(row.get("route_short_name") or "")
        long_name = _collapse_ws(row.get("route_long_name") or "")
        if _NIGHT_BUS_RE.match(short_name):
            return False
        if _NIGHT_BUS_RE.match(long_name):
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
        if route_type == "1" and short:
            return f"Metro {short}"
        if short:
            return short
        return long

    def normalize_stop_name(
        self,
        *,
        stop_id: str,
        stop_name: str,
        parent_station: str,
        location_type: str,
    ) -> str:
        return _collapse_ws(stop_name) or stop_id
