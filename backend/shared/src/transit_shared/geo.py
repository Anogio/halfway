from __future__ import annotations

import math
from typing import Iterator

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


def bucket_key(lat: float, lon: float, bucket_m: float) -> tuple[int, int]:
    lat_m = lat * 111_320.0
    lon_m = lon * 111_320.0 * max(math.cos(math.radians(lat)), 0.1)
    return int(lat_m // bucket_m), int(lon_m // bucket_m)


def neighbor_bucket_keys(key: tuple[int, int], rings: int = 1) -> Iterator[tuple[int, int]]:
    x, y = key
    for dx in range(-rings, rings + 1):
        for dy in range(-rings, rings + 1):
            yield x + dx, y + dy

