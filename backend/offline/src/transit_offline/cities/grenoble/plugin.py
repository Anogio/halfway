from __future__ import annotations

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


def _collapse_ws(value: str) -> str:
    return " ".join(value.split())


def _bus_label(value: str) -> str:
    normalized = _collapse_ws(value)
    if not normalized:
        return normalized
    if normalized.lower().endswith(" bus"):
        return normalized
    return f"{normalized} bus"


class GrenobleCityPlugin(CityPlugin):
    city_id = "grenoble"

    def filter_route_row(self, row: dict[str, str]) -> bool:
        route_type = (row.get("route_type") or "").strip()
        if route_type not in BUS_ROUTE_TYPES:
            return True

        short_name = _collapse_ws(row.get("route_short_name") or "").upper()
        long_name = _collapse_ws(row.get("route_long_name") or "").upper()

        # Grenoble's GTFS mixes in night bus service (N62) and temporary
        # tram-replacement shuttles (NAVA/NAVB/NAVC/NAVE) in the weekday feed.
        if short_name.startswith("N"):
            return False
        if long_name.startswith("NAVETTE"):
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

        if route_type == "0" and short:
            return f"Tram {short}"
        if route_type in BUS_ROUTE_TYPES:
            if short:
                return _bus_label(short)
            if long:
                return _bus_label(long)
            return _bus_label(route_id)
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
