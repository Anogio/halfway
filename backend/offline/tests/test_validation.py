from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.validation.pipeline import run_validate
from transit_shared.settings import parse_settings
from helpers import make_settings_data


class ValidationPipelineTest(unittest.TestCase):
    def test_validation_passes_small_graph(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vval"

            with (artifacts / f"nodes_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type"])
                writer.writerow([0, "A", "A", "PS", "48.8", "2.3", "0"])
                writer.writerow([1, "B", "B", "PS", "48.81", "2.31", "0"])

            graph = {
                "adj_offsets": [0, 1, 1],
                "adj_targets": [1],
                "adj_weights_s": [900],
                "edge_kind": [0],
            }
            (artifacts / f"graph_{version}_weekday.json").write_text(
                json.dumps(graph),
                encoding="utf-8",
            )

            with (artifacts / f"grid_links_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["cell_id", "node_idx", "walk_seconds"])
                writer.writerow([0, 0, 0])

            data = make_settings_data(artifact_version=version)
            data["search"]["first_mile_radius_m"] = 2000
            data["search"]["first_mile_fallback_k"] = 1
            data["runtime"]["max_time_s"] = 4000
            data["cities"]["paris"]["scope"]["default_view"] = [48.8, 2.3, 10]
            data["cities"]["paris"]["validation"] = {
                "mape_threshold": 0.5,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 2000,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 48.8,
                        "from_lon": 2.3,
                        "to_lat": 48.81,
                        "to_lon": 2.31,
                        "expected_min_s": 600,
                        "expected_max_s": 1800,
                    }
                ],
            }
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="paris",
                city=settings.cities["paris"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="paris",
                    gtfs_input=root / "gtfs",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=root / "raw",
                    offline_interim_dir=root / "interim",
                    offline_artifacts_dir=artifacts,
                ),
            )

            report = run_validate(config=cfg)
            self.assertTrue(report["ok"])
            self.assertLessEqual(report["metrics"]["mape"], 0.5)
            self.assertIn("performance_p95_ms", report["metrics"])

    def test_validation_archives_previous_reports(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vval"

            with (artifacts / f"nodes_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type"])
                writer.writerow([0, "A", "A", "PS", "48.8", "2.3", "0"])
                writer.writerow([1, "B", "B", "PS", "48.81", "2.31", "0"])

            graph = {
                "adj_offsets": [0, 1, 1],
                "adj_targets": [1],
                "adj_weights_s": [900],
                "edge_kind": [0],
            }
            (artifacts / f"graph_{version}_weekday.json").write_text(json.dumps(graph), encoding="utf-8")

            with (artifacts / f"grid_links_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["cell_id", "node_idx", "walk_seconds"])
                writer.writerow([0, 0, 0])

            (artifacts / "validation_v0.json").write_text("{}", encoding="utf-8")

            data = make_settings_data(artifact_version=version)
            data["search"]["first_mile_radius_m"] = 2000
            data["search"]["first_mile_fallback_k"] = 1
            data["runtime"]["max_time_s"] = 4000
            data["cities"]["paris"]["scope"]["default_view"] = [48.8, 2.3, 10]
            data["cities"]["paris"]["validation"] = {
                "mape_threshold": 0.5,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 2000,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 48.8,
                        "from_lon": 2.3,
                        "to_lat": 48.81,
                        "to_lon": 2.31,
                        "expected_min_s": 600,
                        "expected_max_s": 1800,
                    }
                ],
            }
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="paris",
                city=settings.cities["paris"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="paris",
                    gtfs_input=root / "gtfs",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=root / "raw",
                    offline_interim_dir=root / "interim",
                    offline_artifacts_dir=artifacts,
                ),
            )

            run_validate(config=cfg)

            archived = list((artifacts / "old").glob("*_validation_v0.json"))
            self.assertEqual(len(archived), 1)
            self.assertTrue((artifacts / f"validation_{version}.json").exists())

    def test_validation_reachability_uses_in_scope_cells_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vval"

            with (artifacts / f"nodes_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    ["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"]
                )
                writer.writerow([0, "A", "A", "PS", "48.8", "2.3", "0", "0"])
                writer.writerow([1, "B", "B", "PS", "48.81", "2.31", "0", "0"])

            graph = {
                "adj_offsets": [0, 1, 1],
                "adj_targets": [1],
                "adj_weights_s": [900],
                "edge_kind": [0],
            }
            (artifacts / f"graph_{version}_weekday.json").write_text(
                json.dumps(graph),
                encoding="utf-8",
            )

            with (artifacts / f"grid_cells_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["cell_id", "cell_lat", "cell_lon", "in_scope"])
                writer.writerow([0, "48.8000", "2.3000", "1"])
                writer.writerow([1, "49.5000", "3.5000", "0"])

            with (artifacts / f"grid_links_{version}.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["cell_id", "node_idx", "walk_seconds"])
                writer.writerow([0, 0, 0])
                writer.writerow([1, 0, 100000])

            data = make_settings_data(artifact_version=version)
            data["search"]["first_mile_radius_m"] = 2000
            data["search"]["first_mile_fallback_k"] = 1
            data["runtime"]["max_time_s"] = 4000
            data["cities"]["paris"]["scope"]["default_view"] = [48.8, 2.3, 10]
            data["cities"]["paris"]["validation"] = {
                "mape_threshold": 0.5,
                "range_tolerance_ratio": 0.25,
                "performance_p95_ms_threshold": 2000,
                "od_pairs": [
                    {
                        "name": "A-B",
                        "from_lat": 48.8,
                        "from_lon": 2.3,
                        "to_lat": 48.81,
                        "to_lon": 2.31,
                        "expected_min_s": 600,
                        "expected_max_s": 1800,
                    }
                ],
            }
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="paris",
                city=settings.cities["paris"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="paris",
                    gtfs_input=root / "gtfs",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=root / "raw",
                    offline_interim_dir=root / "interim",
                    offline_artifacts_dir=artifacts,
                ),
            )

            report = run_validate(config=cfg)
            self.assertTrue(report["ok"])
            self.assertEqual(report["metrics"]["grid_linked_cells"], 2)
            self.assertEqual(report["metrics"]["grid_in_scope_cells"], 1)
            self.assertEqual(report["metrics"]["grid_reachability_ratio_from_city_center"], 1.0)
