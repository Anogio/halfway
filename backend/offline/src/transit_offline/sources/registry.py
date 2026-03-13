from __future__ import annotations

from transit_offline.sources.base import SourceAdapter
from transit_offline.sources.direct_gtfs import DirectGtfsSourceAdapter
from transit_offline.sources.london.adapter import LondonSourceAdapter
from transit_offline.sources.madrid.adapter import MadridSourceAdapter


def get_source_adapter(city_id: str) -> SourceAdapter:
    adapters: dict[str, SourceAdapter] = {
        "london": LondonSourceAdapter(),
        "madrid": MadridSourceAdapter(),
        "paris": DirectGtfsSourceAdapter(),
    }
    adapter = adapters.get(city_id)
    if adapter is None:
        known = ", ".join(sorted(adapters))
        raise ValueError(f"No source adapter registered for '{city_id}'. Registered cities: {known}")
    return adapter
