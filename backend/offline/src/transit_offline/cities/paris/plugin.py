from __future__ import annotations

import re

from transit_offline.cities.base import CityPlugin

_NOCTILIEN_RE = re.compile(r"^N\d*$", re.IGNORECASE)


class ParisCityPlugin(CityPlugin):
    city_id = "paris"

    def filter_route_row(self, row: dict[str, str]) -> bool:
        route_type = (row.get("route_type") or "").strip()
        short_name = (row.get("route_short_name") or "").strip()
        long_name = (row.get("route_long_name") or "").strip()
        if route_type != "3":
            return True
        if _NOCTILIEN_RE.match(short_name) or _NOCTILIEN_RE.match(long_name):
            return False
        return True
