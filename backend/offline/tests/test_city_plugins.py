from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from transit_offline.cities import get_city_plugin
from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.ingest.gtfs import load_nodes, load_routes
from transit_offline.sources.pipeline import run_prepare_data
from transit_shared.settings import parse_settings
from helpers import make_settings_data, write_csv


class CityPluginsTest(unittest.TestCase):
    def test_london_route_label_formatting_is_city_plugin_owned(self) -> None:
        plugin = get_city_plugin("london")

        self.assertEqual(
            plugin.format_route_label(
                route_id="route-jubilee",
                short_name="Jubilee",
                long_name="Jubilee - Stanmore - Waterloo - Stratford",
                route_type="1",
            ),
            "Jubilee",
        )
        self.assertEqual(
            plugin.format_route_label(
                route_id="route-109",
                short_name="109",
                long_name="Croydon - Brixton",
                route_type="3",
            ),
            "109 bus",
        )

    def test_london_plugin_excludes_night_bus_routes_during_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["DAY", "A1", "133", "133", "3"],
                    ["NIGHT", "A1", "N133", "N133", "3"],
                    ["TUBE", "A1", "Northern", "Northern line", "1"],
                ],
            )

            plugin = get_city_plugin("london")
            routes, route_to_type, _ = load_routes(gtfs, {"1", "3"}, plugin=plugin)

            self.assertEqual(routes, {"DAY", "TUBE"})
            self.assertEqual(route_to_type, {"DAY": "3", "TUBE": "1"})

    def test_london_plugin_excludes_replacement_bus_routes_during_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["DAY", "A1", "14", "14", "3"],
                    ["REPLACE_SHORT", "A1", "UL64", "UL64", "3"],
                    ["REPLACE_LONG", "A1", "", "UL95 replacement bus", "3"],
                    ["TUBE", "A1", "District", "District line", "1"],
                ],
            )

            plugin = get_city_plugin("london")
            routes, route_to_type, _ = load_routes(gtfs, {"1", "3"}, plugin=plugin)

            self.assertEqual(routes, {"DAY", "TUBE"})
            self.assertEqual(route_to_type, {"DAY": "3", "TUBE": "1"})

    def test_london_stop_name_normalization_is_city_plugin_owned(self) -> None:
        plugin = get_city_plugin("london")
        self.assertEqual(
            plugin.normalize_stop_name(
                stop_id="9400ZZLUODS",
                stop_name="Oxford Circus Underground Station",
                parent_station="",
                location_type="0",
            ),
            "Oxford Circus",
        )

    def test_paris_plugin_excludes_noctilien_routes_during_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["DAY", "A1", "42", "42", "3"],
                    ["NIGHT", "A1", "", "N02", "3"],
                    ["METRO", "A1", "4", "4", "1"],
                ],
            )

            plugin = get_city_plugin("paris")
            routes, route_to_type, _ = load_routes(gtfs, {"1", "3"}, plugin=plugin)

            self.assertEqual(routes, {"DAY", "METRO"})
            self.assertEqual(route_to_type, {"DAY": "3", "METRO": "1"})

    def test_madrid_plugin_excludes_night_bus_routes_during_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["DAY", "A1", "27", "27", "3"],
                    ["NIGHT", "A1", "N6", "N6", "3"],
                    ["NIGHT_CIRC", "A1", "NC1", "NC1", "3"],
                    ["METRO", "A1", "1", "Linea 1", "1"],
                ],
            )

            plugin = get_city_plugin("madrid")
            routes, route_to_type, _ = load_routes(gtfs, {"1", "3"}, plugin=plugin)

            self.assertEqual(routes, {"DAY", "METRO"})
            self.assertEqual(route_to_type, {"DAY": "3", "METRO": "1"})

    def test_madrid_route_label_formatting_is_city_plugin_owned(self) -> None:
        plugin = get_city_plugin("madrid")

        self.assertEqual(
            plugin.format_route_label(
                route_id="route-1",
                short_name="1",
                long_name="Pinar de Chamartin-Valdecarros",
                route_type="1",
            ),
            "Metro 1",
        )
        self.assertEqual(
            plugin.format_route_label(
                route_id="route-27",
                short_name="27",
                long_name="Embajadores - Plaza de Castilla",
                route_type="3",
            ),
            "27 bus",
        )

    def test_ingest_applies_london_stop_name_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            write_csv(
                gtfs / "stops.txt",
                [
                    "stop_id",
                    "stop_code",
                    "stop_name",
                    "stop_lat",
                    "stop_lon",
                    "wheelchair_boarding",
                    "stop_timezone",
                    "location_type",
                    "parent_station",
                    "level_id",
                ],
                [["A", "", "Paddington Underground Station", "51.5154", "-0.1755", "1", "", "0", "", ""]],
            )

            rows, _ = load_nodes(gtfs, plugin=get_city_plugin("london"))
            self.assertEqual(rows[0]["stop_name"], "Paddington")

    def test_prepare_data_fails_for_city_without_registered_source_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = make_settings_data(artifact_version="v1")
            data["cities"]["lyon"] = {
                "label": "Lyon",
                "artifact_version": "v1",
                "paths": {"gtfs_input": "backend/offline/data/gtfs/lyon"},
                "scope": {"use_bbox": False, "bbox": [4.7, 45.6, 5.0, 45.9], "default_view": [45.75, 4.85, 11]},
                "geocoding": {"country_codes": "fr", "viewbox": "4.7,45.6,5.0,45.9", "bounded": True},
                "validation": {
                    "mape_threshold": 0.2,
                    "range_tolerance_ratio": 0.25,
                    "performance_p95_ms_threshold": 1500,
                    "od_pairs": [],
                },
            }
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="lyon",
                city=settings.cities["lyon"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="lyon",
                    gtfs_input=root / "gtfs" / "lyon",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=root / "raw" / "lyon",
                    offline_interim_dir=root / "interim" / "lyon",
                    offline_artifacts_dir=root / "artifacts" / "lyon",
                ),
            )

            with self.assertRaisesRegex(ValueError, "No source adapter registered"):
                run_prepare_data(config=cfg)


if __name__ == "__main__":
    unittest.main()
