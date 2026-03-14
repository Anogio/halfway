from __future__ import annotations

import unittest

from helpers import make_settings, make_settings_data
from transit_backend.api.contracts import build_health_payload, build_metadata_payload


def make_settings_with_london():
    data = make_settings_data()
    data["cities"]["london"] = {
        "label": "London",
        "artifact_version": "v0",
        "paths": {"gtfs_input": "backend/offline/data/gtfs/london"},
        "scope": {
            "use_bbox": False,
            "bbox": [-1.0, 51.0, 1.0, 52.0],
            "default_view": [51.5074, -0.1278, 11],
        },
        "geocoding": {
            "country_codes": "gb",
            "viewbox": "-0.5,51.2,0.3,51.7",
            "bounded": True,
        },
        "validation": {
            "mape_threshold": 0.25,
            "range_tolerance_ratio": 0.3,
            "performance_p95_ms_threshold": 2000,
            "od_pairs": [
                {
                    "name": "pair",
                    "from_lat": 51.5,
                    "from_lon": -0.12,
                    "to_lat": 51.51,
                    "to_lon": -0.1,
                    "expected_min_s": 600,
                    "expected_max_s": 1800,
                }
            ],
        },
    }
    from transit_shared.settings import parse_settings

    return parse_settings(data)


def make_settings_with_madrid():
    data = make_settings_data()
    data["cities"]["madrid"] = {
        "label": "Madrid",
        "artifact_version": "v0",
        "paths": {"gtfs_input": "backend/offline/data/gtfs/madrid"},
        "scope": {
            "use_bbox": False,
            "bbox": [-3.92, 40.27, -3.50, 40.65],
            "default_view": [40.4168, -3.7038, 10],
        },
        "geocoding": {
            "country_codes": "es",
            "viewbox": "-3.92,40.27,-3.50,40.65",
            "bounded": True,
        },
        "validation": {
            "mape_threshold": 0.25,
            "range_tolerance_ratio": 0.3,
            "performance_p95_ms_threshold": 2000,
            "od_pairs": [
                {
                    "name": "pair",
                    "from_lat": 40.41,
                    "from_lon": -3.70,
                    "to_lat": 40.45,
                    "to_lon": -3.69,
                    "expected_min_s": 600,
                    "expected_max_s": 1800,
                }
            ],
        },
    }
    from transit_shared.settings import parse_settings

    return parse_settings(data)


class ApiContractHealthMetadataTest(unittest.TestCase):
    def test_health_payload_schema(self) -> None:
        payload = build_health_payload(make_settings())
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["cities"], ["paris_fr"])
        self.assertEqual(payload["cities_count"], 1)

        payload = build_health_payload(make_settings_with_london())
        self.assertEqual(payload["cities"], ["london_uk", "paris_fr"])
        self.assertEqual(payload["cities_count"], 2)

    def test_metadata_payload_schema(self) -> None:
        payload = build_metadata_payload(make_settings())

        self.assertEqual(sorted(payload.keys()), ["cities"])
        self.assertGreaterEqual(len(payload["cities"]), 1)

        first_city = payload["cities"][0]
        self.assertEqual(sorted(first_city.keys()), ["bbox", "country_code", "default_view", "id"])
        self.assertEqual(first_city["id"], "paris_fr")
        self.assertEqual(first_city["country_code"], "fr")
        self.assertEqual(first_city["default_view"], [48.8566, 2.3522, 10])
        self.assertEqual(first_city["bbox"], [1.0, 48.0, 3.0, 49.0])
        self.assertEqual(len(first_city["default_view"]), 3)
        self.assertEqual(len(first_city["bbox"]), 4)

    def test_health_payload_uses_spanish_public_city_suffix(self) -> None:
        payload = build_health_payload(make_settings_with_madrid())
        self.assertEqual(payload["cities"], ["madrid_es", "paris_fr"])
        self.assertEqual(payload["cities_count"], 2)
