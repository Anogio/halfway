from __future__ import annotations

import unittest

from transit_backend.api.contracts import (
    MAX_MULTI_ORIGINS,
    InvalidIsochroneRequest,
    parse_multi_isochrones_request,
)


class ApiContractIsochronesTest(unittest.TestCase):
    def test_parse_multi_isochrones_request_valid(self) -> None:
        city, origins, debug = parse_multi_isochrones_request(
            {
                "city": "paris_fr",
                "origins": [
                    {"id": "origin-1", "lat": 48.8, "lon": 2.3},
                    {"id": "origin-2", "lat": 48.81, "lon": 2.31},
                ],
            }
        )
        self.assertEqual(city, "paris_fr")
        self.assertEqual(len(origins), 2)
        self.assertEqual(origins[0]["id"], "origin-1")
        self.assertEqual(debug, False)

    def test_parse_multi_isochrones_request_accepts_debug_flag(self) -> None:
        city, origins, debug = parse_multi_isochrones_request(
            {
                "city": "paris_fr",
                "origins": [{"id": "origin-1", "lat": 48.8, "lon": 2.3}],
                "debug": True,
            }
        )
        self.assertEqual(city, "paris_fr")
        self.assertEqual(len(origins), 1)
        self.assertEqual(debug, True)

    def test_parse_multi_isochrones_request_invalid(self) -> None:
        with self.assertRaises(InvalidIsochroneRequest):
            parse_multi_isochrones_request({"origins": []})

        with self.assertRaises(InvalidIsochroneRequest):
            parse_multi_isochrones_request(
                {
                    "city": "paris_fr",
                    "origins": [
                        {"id": f"o-{idx}", "lat": 48.8, "lon": 2.3}
                        for idx in range(MAX_MULTI_ORIGINS + 1)
                    ],
                }
            )

        with self.assertRaises(InvalidIsochroneRequest):
            parse_multi_isochrones_request(
                {
                    "city": "paris_fr",
                    "origins": [
                        {"id": "same", "lat": 48.8, "lon": 2.3},
                        {"id": "same", "lat": 48.9, "lon": 2.4},
                    ],
                }
            )

        with self.assertRaises(InvalidIsochroneRequest):
            parse_multi_isochrones_request(
                {
                    "city": "paris_fr",
                    "origins": [{"id": "a", "lat": 48.8, "lon": 2.3}],
                    "render_max_time_s": 3600,
                }
            )

        with self.assertRaises(InvalidIsochroneRequest):
            parse_multi_isochrones_request(
                {
                    "city": "paris_fr",
                    "origins": [{"id": "a", "lat": 48.8, "lon": 2.3}],
                    "debug": "yes",
                }
            )
