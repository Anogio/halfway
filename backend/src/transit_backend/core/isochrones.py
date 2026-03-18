from __future__ import annotations

from transit_backend.core.isochrone_topology import GridTopology, infer_grid_topology

__all__ = [
    "GridTopology",
    "infer_grid_topology",
    "build_isochrone_scalar_grid",
]


def build_isochrone_scalar_grid(
    *,
    cells: list[dict[str, object]],
    topology: GridTopology,
    max_time_s: int,
) -> dict[str, object] | None:
    values_by_cell: dict[tuple[int, int], int] = {}
    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        time_s = int(cell["time_s"])
        if time_s > max_time_s:
            continue

        row = int(round((lat - topology.min_lat) / topology.lat_step))
        col = int(round((lon - topology.min_lon) / topology.lon_step))
        values_by_cell[(row, col)] = time_s

    if not values_by_cell:
        return None

    rows = [row for row, _ in values_by_cell]
    cols = [col for _, col in values_by_cell]
    min_row = min(rows)
    max_row = max(rows)
    min_col = min(cols)
    max_col = max(cols)
    row_count = max_row - min_row + 1
    col_count = max_col - min_col + 1

    values: list[int | None] = [None] * (row_count * col_count)
    for (row, col), time_s in values_by_cell.items():
        row_idx = row - min_row
        col_idx = col - min_col
        values[row_idx * col_count + col_idx] = time_s

    west = round(topology.min_lon + (min_col - 0.5) * topology.lon_step, 7)
    south = round(topology.min_lat + (min_row - 0.5) * topology.lat_step, 7)
    east = round(topology.min_lon + (max_col + 0.5) * topology.lon_step, 7)
    north = round(topology.min_lat + (max_row + 0.5) * topology.lat_step, 7)

    return {
        "topology": {
            "min_lat": topology.min_lat,
            "min_lon": topology.min_lon,
            "lat_step": topology.lat_step,
            "lon_step": topology.lon_step,
        },
        "grid": {
            "min_row": min_row,
            "min_col": min_col,
            "row_count": row_count,
            "col_count": col_count,
            "values": values,
        },
        "bounds": {
            "west": west,
            "south": south,
            "east": east,
            "north": north,
        },
        "max_time_s": max_time_s,
    }
