from __future__ import annotations

from dataclasses import dataclass

from transit_backend.core.artifacts import RuntimeData


@dataclass(frozen=True)
class GridTopology:
    min_lat: float
    min_lon: float
    lat_step: float
    lon_step: float


def infer_grid_topology(runtime: RuntimeData) -> GridTopology:
    if not runtime.grid_cells:
        raise ValueError("grid_cells are required to infer topology")

    lat_values = sorted({round(cell.lat, 7) for cell in runtime.grid_cells.values()})
    lon_values = sorted({round(cell.lon, 7) for cell in runtime.grid_cells.values()})

    return GridTopology(
        min_lat=lat_values[0],
        min_lon=lon_values[0],
        lat_step=_infer_step(lat_values),
        lon_step=_infer_step(lon_values),
    )


def _infer_step(values: list[float]) -> float:
    if len(values) < 2:
        raise ValueError("at least 2 distinct values are required to infer grid step")

    min_positive = float("inf")
    prev = values[0]
    for current in values[1:]:
        delta = current - prev
        if delta > 1e-9 and delta < min_positive:
            min_positive = delta
        prev = current

    if min_positive == float("inf"):
        raise ValueError("could not infer positive grid step")
    return min_positive
