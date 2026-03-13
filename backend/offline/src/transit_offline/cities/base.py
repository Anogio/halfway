from __future__ import annotations

from abc import ABC


class CityPlugin(ABC):
    city_id: str

    def filter_route_row(self, row: dict[str, str]) -> bool:
        return True

    def format_route_label(
        self,
        *,
        route_id: str,
        short_name: str,
        long_name: str,
        route_type: str,
    ) -> str:
        return ""

    def normalize_stop_name(
        self,
        *,
        stop_id: str,
        stop_name: str,
        parent_station: str,
        location_type: str,
    ) -> str:
        return stop_name.strip() or stop_id
