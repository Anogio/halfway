from __future__ import annotations

from collections import defaultdict

from transit_backend.core.isochrone_polygons import dissolve_cells_to_multipolygon
from transit_backend.core.isochrone_topology import GridTopology, infer_grid_topology

__all__ = ["GridTopology", "infer_grid_topology", "build_isochrone_feature_collection"]


def build_isochrone_feature_collection(
    cells: list[dict[str, object]],
    topology: GridTopology,
    bucket_size_s: int,
    max_time_s: int,
) -> dict[str, object]:
    if bucket_size_s <= 0:
        raise ValueError("bucket_size_s must be > 0")

    cells_by_bucket: dict[int, set[tuple[int, int]]] = defaultdict(set)
    cell_counts: dict[int, int] = defaultdict(int)

    for cell in cells:
        lat = float(cell["lat"])
        lon = float(cell["lon"])
        time_s = int(cell["time_s"])
        if time_s > max_time_s:
            continue

        row = int(round((lat - topology.min_lat) / topology.lat_step))
        col = int(round((lon - topology.min_lon) / topology.lon_step))
        bucket_index = max(0, time_s // bucket_size_s)

        cells_by_bucket[bucket_index].add((row, col))
        cell_counts[bucket_index] += 1

    features: list[dict[str, object]] = []
    for bucket_index in sorted(cells_by_bucket):
        min_time_s = bucket_index * bucket_size_s
        max_time_bound_s = min((bucket_index + 1) * bucket_size_s, max_time_s)
        if min_time_s > max_time_s:
            continue

        multipolygon_coords = dissolve_cells_to_multipolygon(
            cells_by_bucket[bucket_index],
            topology=topology,
        )
        if not multipolygon_coords:
            continue

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "bucket_index": bucket_index,
                    "bucket_size_s": bucket_size_s,
                    "min_time_s": min_time_s,
                    "max_time_s": max_time_bound_s,
                    "cell_count": cell_counts[bucket_index],
                    "polygon_count": len(multipolygon_coords),
                },
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": multipolygon_coords,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
