from __future__ import annotations

import unittest
from pathlib import Path

from helpers import make_settings_data
from transit_shared.settings import SettingsError, find_repo_root, parse_settings


class SettingsParserMultiCityTest(unittest.TestCase):
    def test_parse_two_city_catalog(self) -> None:
        data = make_settings_data(artifact_version="v1")
        data["cities"]["london"] = {
            "label": "London",
            "artifact_version": "v0",
            "paths": {"gtfs_input": "backend/offline/data/gtfs/london"},
            "scope": {
                "use_bbox": True,
                "bbox": [-0.5103, 51.2868, 0.3340, 51.6923],
                "default_view": [51.5074, -0.1278, 11],
            },
            "geocoding": {
                "country_codes": "gb",
                "viewbox": "-0.5103,51.2868,0.3340,51.6923",
                "bounded": True,
            },
            "validation": {
                "mape_threshold": 0.3,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 1500,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 51.50,
                        "from_lon": -0.12,
                        "to_lat": 51.52,
                        "to_lon": -0.10,
                        "expected_min_s": 600,
                        "expected_max_s": 2400,
                    }
                ],
            },
        }

        settings = parse_settings(data)
        self.assertEqual(sorted(settings.cities), ["london", "paris"])
        self.assertEqual(settings.cities["london"].artifact_version, "v0")

    def test_parse_three_city_catalog(self) -> None:
        data = make_settings_data(artifact_version="v1")
        data["cities"]["london"] = {
            "label": "London",
            "artifact_version": "v0",
            "paths": {"gtfs_input": "backend/offline/data/gtfs/london"},
            "scope": {
                "use_bbox": True,
                "bbox": [-0.5103, 51.2868, 0.3340, 51.6923],
                "default_view": [51.5074, -0.1278, 11],
            },
            "geocoding": {
                "country_codes": "gb",
                "viewbox": "-0.5103,51.2868,0.3340,51.6923",
                "bounded": True,
            },
            "validation": {
                "mape_threshold": 0.3,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 1500,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 51.50,
                        "from_lon": -0.12,
                        "to_lat": 51.52,
                        "to_lon": -0.10,
                        "expected_min_s": 600,
                        "expected_max_s": 2400,
                    }
                ],
            },
        }
        data["cities"]["madrid"] = {
            "label": "Madrid",
            "artifact_version": "v2",
            "paths": {"gtfs_input": "backend/offline/data/gtfs/madrid"},
            "scope": {
                "use_bbox": True,
                "bbox": [-3.9200, 40.2700, -3.5050, 40.6450],
                "default_view": [40.4168, -3.7038, 10],
            },
            "geocoding": {
                "country_codes": "es",
                "viewbox": "-3.9200,40.2700,-3.5050,40.6450",
                "bounded": True,
            },
            "validation": {
                "mape_threshold": 0.25,
                "range_tolerance_ratio": 0.30,
                "performance_p95_ms_threshold": 2000,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 40.41,
                        "from_lon": -3.70,
                        "to_lat": 40.45,
                        "to_lon": -3.69,
                        "expected_min_s": 600,
                        "expected_max_s": 2400,
                    }
                ],
            },
        }

        settings = parse_settings(data)
        self.assertEqual(sorted(settings.cities), ["london", "madrid", "paris"])
        self.assertEqual(settings.cities["madrid"].geocoding.country_codes, "es")

    def test_rejects_empty_city_catalog(self) -> None:
        data = make_settings_data(artifact_version="v1")
        data["cities"] = {}

        with self.assertRaises(SettingsError):
            parse_settings(data)

    def test_rejects_missing_required_city_keys(self) -> None:
        data = make_settings_data(artifact_version="v1")
        del data["cities"]["paris"]["geocoding"]

        with self.assertRaises(SettingsError):
            parse_settings(data)

    def test_find_repo_root_finds_backend_local_config_from_repo_or_backend_root(self) -> None:
        with self.subTest("repo root and backend root"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                backend_root = root / "backend"
                backend_config = backend_root / "config"
                backend_config.mkdir(parents=True)
                (backend_config / "settings.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

                self.assertEqual(find_repo_root(root), backend_root.resolve())
                self.assertEqual(find_repo_root(backend_root), backend_root.resolve())
