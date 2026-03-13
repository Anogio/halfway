from __future__ import annotations

import unittest

from transit_backend.core.isochrone_polygons import (
    _container_polygon_index,
    _extract_loops,
    _point_in_ring,
    _select_next_vertex,
    dissolve_cells_to_multipolygon,
)
from transit_backend.core.isochrone_topology import GridTopology


class IsochronePolygonsTest(unittest.TestCase):
    def test_dissolve_empty_cells_returns_empty(self) -> None:
        topology = GridTopology(min_lat=0.0, min_lon=0.0, lat_step=1.0, lon_step=1.0)
        self.assertEqual(dissolve_cells_to_multipolygon(set(), topology), [])

    def test_dissolve_disconnected_cells_returns_multiple_polygons(self) -> None:
        topology = GridTopology(min_lat=0.0, min_lon=0.0, lat_step=1.0, lon_step=1.0)
        polygons = dissolve_cells_to_multipolygon({(0, 0), (3, 3)}, topology)
        self.assertEqual(len(polygons), 2)

    def test_select_next_vertex_raises_on_invalid_direction(self) -> None:
        with self.assertRaises(ValueError):
            _select_next_vertex((0, 0), (1, 1), {(2, 1)})

    def test_select_next_vertex_raises_on_missing_continuation(self) -> None:
        with self.assertRaises(ValueError):
            _select_next_vertex((0, 0), (1, 0), {(3, 0)})

    def test_extract_loops_raises_on_dangling_edge(self) -> None:
        with self.assertRaises(ValueError):
            _extract_loops({((0, 0), (1, 0))})

    def test_container_polygon_index_and_point_in_ring(self) -> None:
        outer = [(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]
        polygons = [[outer]]
        self.assertEqual(_container_polygon_index(polygons, (1, 1)), 0)
        self.assertEqual(_container_polygon_index(polygons, (3, 3)), None)
        self.assertEqual(_point_in_ring((1, 1), outer), True)
        self.assertEqual(_point_in_ring((3, 3), outer), False)
