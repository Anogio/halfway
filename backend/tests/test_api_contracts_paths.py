from __future__ import annotations

import unittest

from transit_backend.api.contracts import (
    InvalidPathRequest,
    parse_multi_path_request,
)


class ApiContractPathsTest(unittest.TestCase):
    def test_parse_multi_path_request_valid(self) -> None:
        city, origins, destination_lat, destination_lon, debug = parse_multi_path_request(
            {
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8, "lon": 2.3},
                    {"id": "origin-2", "lat": 48.81, "lon": 2.31},
                ],
                "destination": {"lat": 48.82, "lon": 2.35},
            }
        )
        self.assertEqual(city, "paris_fr")
        self.assertEqual(len(origins), 2)
        self.assertAlmostEqual(destination_lat, 48.82)
        self.assertAlmostEqual(destination_lon, 2.35)
        self.assertEqual(debug, False)

    def test_parse_multi_path_request_accepts_debug_flag(self) -> None:
        city, origins, destination_lat, destination_lon, debug = parse_multi_path_request(
            {
                "city": "paris_fr",
                "origins": [{"id": "origin-1", "lat": 48.8, "lon": 2.3}],
                "destination": {"lat": 48.82, "lon": 2.35},
                "debug": True,
            }
        )
        self.assertEqual(city, "paris_fr")
        self.assertEqual(len(origins), 1)
        self.assertAlmostEqual(destination_lat, 48.82)
        self.assertAlmostEqual(destination_lon, 2.35)
        self.assertEqual(debug, True)

    def test_parse_multi_path_request_invalid(self) -> None:
        with self.assertRaises(InvalidPathRequest):
            parse_multi_path_request({"origins": [], "destination": {"lat": 48.82, "lon": 2.35}})

        with self.assertRaises(InvalidPathRequest):
            parse_multi_path_request(
                {"city": "paris_fr", "origins": [{"id": "o-1", "lat": 48.8, "lon": 2.3}]}
            )

        with self.assertRaises(InvalidPathRequest):
            parse_multi_path_request(
                {
                    "city": "paris_fr",
                    "origins": [{"id": "o-1", "lat": 48.8, "lon": 2.3}],
                    "destination": {"lat": 48.82, "lon": 2.35},
                    "max_time_s": 3600,
                }
            )

        with self.assertRaises(InvalidPathRequest):
            parse_multi_path_request(
                {
                    "city": "paris_fr",
                    "origins": [{"id": "o-1", "lat": 48.8, "lon": 2.3}],
                    "destination": {"lat": 48.82, "lon": 2.35},
                    "debug": "yes",
                }
            )
