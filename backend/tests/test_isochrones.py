from __future__ import annotations

import unittest

from transit_backend.core.isochrones import (
    GridTopology,
    build_isochrone_scalar_grid,
)


class IsochroneDissolveTest(unittest.TestCase):
    def test_scalar_grid_captures_sparse_values_and_bounds(self) -> None:
        topology = GridTopology(min_lat=0.0, min_lon=0.0, lat_step=1.0, lon_step=1.0)
        cells = [
            {"cell_id": 1, "lat": 0.0, "lon": 0.0, "time_s": 120},
            {"cell_id": 2, "lat": 1.0, "lon": 1.0, "time_s": 420},
        ]

        grid = build_isochrone_scalar_grid(
            cells=cells,
            topology=topology,
            max_time_s=1800,
        )

        self.assertIsNotNone(grid)
        assert grid is not None
        self.assertEqual(grid["grid"]["min_row"], 0)
        self.assertEqual(grid["grid"]["min_col"], 0)
        self.assertEqual(grid["grid"]["row_count"], 2)
        self.assertEqual(grid["grid"]["col_count"], 2)
        self.assertEqual(grid["grid"]["values"], [120, None, None, 420])
        self.assertEqual(
            grid["bounds"],
            {"west": -0.5, "south": -0.5, "east": 1.5, "north": 1.5},
        )
