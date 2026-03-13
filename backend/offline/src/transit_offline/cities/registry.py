from __future__ import annotations

from transit_offline.cities.base import CityPlugin
from transit_offline.cities.london.plugin import LondonCityPlugin
from transit_offline.cities.madrid.plugin import MadridCityPlugin
from transit_offline.cities.paris.plugin import ParisCityPlugin

_CITY_PLUGINS: dict[str, CityPlugin] = {
    "london": LondonCityPlugin(),
    "madrid": MadridCityPlugin(),
    "paris": ParisCityPlugin(),
}


def get_city_plugin(city_id: str) -> CityPlugin:
    plugin = _CITY_PLUGINS.get(city_id)
    if plugin is None:
        known = ", ".join(sorted(_CITY_PLUGINS))
        raise ValueError(f"No city plugin registered for '{city_id}'. Registered cities: {known}")
    return plugin
