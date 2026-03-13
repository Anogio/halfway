from __future__ import annotations

import unittest

from transit_backend.core.isochrones import GridTopology, build_isochrone_feature_collection


class IsochroneDissolveTest(unittest.TestCase):
    def test_same_bucket_cells_are_dissolved_into_single_polygon(self) -> None:
        topology = GridTopology(min_lat=0.0, min_lon=0.0, lat_step=1.0, lon_step=1.0)
        # L-shape in one 5-minute bucket. A rectangle-only merge would split this.
        cells = [
            {"cell_id": 1, "lat": 0.0, "lon": 0.0, "time_s": 120},
            {"cell_id": 2, "lat": 0.0, "lon": 1.0, "time_s": 150},
            {"cell_id": 3, "lat": 1.0, "lon": 0.0, "time_s": 210},
        ]

        collection = build_isochrone_feature_collection(
            cells,
            topology=topology,
            bucket_size_s=300,
            max_time_s=1800,
        )

        self.assertEqual(collection["type"], "FeatureCollection")
        self.assertEqual(len(collection["features"]), 1)

        feature = collection["features"][0]
        self.assertEqual(feature["properties"]["bucket_index"], 0)
        self.assertEqual(feature["properties"]["polygon_count"], 1)

        coordinates = feature["geometry"]["coordinates"]
        self.assertEqual(len(coordinates), 1)
        self.assertEqual(len(coordinates[0]), 1)
        outer_ring = coordinates[0][0]
        self.assertGreaterEqual(len(outer_ring), 7)

