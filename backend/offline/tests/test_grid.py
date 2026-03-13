from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.grid.pipeline import run_build_grid
from transit_shared.geo import bucket_key
from transit_shared.seed_selection import resolve_access_candidates
from transit_shared.settings import parse_settings
from helpers import make_settings_data


class GridPipelineTest(unittest.TestCase):
    def test_build_grid_ignores_onboard_nodes_in_v2_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "v2"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "node_idx",
                        "node_kind",
                        "node_key",
                        "stop_id",
                        "stop_name",
                        "parent_station",
                        "lat",
                        "lon",
                        "location_type",
                        "is_rail_like",
                        "physical_node_idx",
                        "route_id",
                        "direction_id",
                    ]
                )
                writer.writerow([0, "physical", "A", "A", "A", "", "48.8", "2.3", "0", "0", "", "", ""])
                writer.writerow([1, "onboard", "A::R1::0", "A", "A", "", "48.8", "2.3", "0", "0", "0", "R1", "0"])

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 4}
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.299, 48.799, 2.301, 48.801],
                "default_view": [48.8566, 2.3522, 10],
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

            report = run_build_grid(config=cfg)

            self.assertGreater(report["links"], 0)
            with (artifacts / f"grid_links_{version}.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertTrue(rows)
            self.assertEqual({row["node_idx"] for row in rows}, {"0"})

    def test_build_grid_exports_csv(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vgrid"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"])
                writer.writerow([0, "A", "A", "PS", "48.8", "2.3", "0", "0"])
                writer.writerow([1, "B", "B", "PS", "48.81", "2.31", "0", "0"])

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 4}
            data["search"]["grid_candidate_radius_m"] = 1000
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.29, 48.79, 2.32, 48.82],
                "default_view": [48.8566, 2.3522, 10],
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

            report = run_build_grid(config=cfg)
            self.assertGreater(report["cells"], 0)
            self.assertGreater(report["links"], 0)
            self.assertTrue((artifacts / f"grid_cells_{version}.csv").exists())
            self.assertTrue((artifacts / f"grid_links_{version}.csv").exists())

    def test_build_grid_keeps_nearest_rail_candidate_when_bus_nodes_crowd_cap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vgrid"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"])
                writer.writerow([0, "490000001A", "Bus A", "", "48.8000", "2.3000", "0", "0"])
                writer.writerow([1, "490000001B", "Bus B", "", "48.8004", "2.3004", "0", "0"])
                writer.writerow([2, "9400ZZLUTST1", "Rail", "", "48.8010", "2.3010", "0", "1"])

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 2}
            data["search"]["grid_candidate_radius_m"] = 1000
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.299, 48.799, 2.301, 48.801],
                "default_view": [48.8566, 2.3522, 10],
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

            run_build_grid(config=cfg)

            with (artifacts / f"grid_links_{version}.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            self.assertTrue(rows)
            first_cell_links = [row for row in rows if row["cell_id"] == "0"]
            linked_node_ids = {row["node_idx"] for row in first_cell_links}
            self.assertIn("2", linked_node_ids)

    def test_build_grid_archives_previous_grid_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vgrid"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"])
                writer.writerow([0, "A", "A", "PS", "48.8", "2.3", "0", "0"])

            (artifacts / "grid_cells_v0.csv").write_text("cell_id\n", encoding="utf-8")
            (artifacts / "grid_links_v0.csv").write_text("cell_id,node_idx,walk_seconds\n", encoding="utf-8")
            (artifacts / "grid_report_v0.json").write_text("{}", encoding="utf-8")

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 4}
            data["search"]["grid_candidate_radius_m"] = 1000
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.29, 48.79, 2.32, 48.82],
                "default_view": [48.8566, 2.3522, 10],
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

            run_build_grid(config=cfg)

            archived = list((artifacts / "old").glob("*_grid_cells_v0.csv"))
            self.assertEqual(len(archived), 1)
            self.assertTrue((artifacts / f"grid_cells_{version}.csv").exists())

    def test_build_grid_selection_matches_shared_selector_under_runtime_policy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vgrid"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"])
                writer.writerow([0, "490000001A", "Bus A", "", "48.8000", "2.3000", "0", "0"])
                writer.writerow([1, "490000001B", "Bus B", "", "48.8004", "2.3004", "0", "0"])
                writer.writerow([2, "9400ZZLUTST1", "Rail", "", "48.8010", "2.3010", "0", "1"])

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 1}
            data["search"]["grid_candidate_radius_m"] = 100
            data["search"]["first_mile_radius_m"] = 1000
            data["search"]["first_mile_fallback_k"] = 1
            data["runtime"]["max_seed_nodes"] = 2
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.299, 48.799, 2.301, 48.801],
                "default_view": [48.8566, 2.3522, 10],
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

            run_build_grid(config=cfg)

            node_coords = {
                0: (48.8000, 2.3000),
                1: (48.8004, 2.3004),
                2: (48.8010, 2.3010),
            }
            bucket_index: dict[tuple[int, int], list[int]] = {}
            for idx, (lat, lon) in node_coords.items():
                bucket_index.setdefault(bucket_key(lat, lon, 1000), []).append(idx)
            expected = resolve_access_candidates(
                lat=48.7990,
                lon=2.2990,
                search_radius_m=1000,
                bucket_radius_m=1000,
                bucket_index=bucket_index,
                node_coords=node_coords,
                walk_speed_mps=1.2,
                limit=2,
                fallback_k=1,
                allow_global_fallback=True,
                force_inclusion_ids=frozenset({2}),
                forced_k=1,
                forced_nearest_index=None,
            )

            with (artifacts / f"grid_links_{version}.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            first_cell_links = [
                (int(row["node_idx"]), int(row["walk_seconds"]))
                for row in rows
                if row["cell_id"] == "0"
            ]
            self.assertEqual(first_cell_links, expected)

    def test_build_grid_marks_fallback_only_cells_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            version = "vgrid"

            nodes_path = artifacts / f"nodes_{version}.csv"
            with nodes_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    ["node_idx", "stop_id", "stop_name", "parent_station", "lat", "lon", "location_type", "is_rail_like"]
                )
                writer.writerow([0, "A", "A", "", "48.8000", "2.3000", "0", "0"])

            data = make_settings_data(artifact_version=version)
            data["grid"] = {"cell_size_m": 500, "max_candidates_per_cell": 1}
            data["search"]["first_mile_radius_m"] = 100
            data["search"]["first_mile_fallback_k"] = 1
            data["runtime"]["max_seed_nodes"] = 1
            data["cities"]["paris"]["scope"] = {
                "use_bbox": True,
                "bbox": [2.5, 49.0, 2.5, 49.0],
                "default_view": [48.8566, 2.3522, 10],
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

            report = run_build_grid(config=cfg)
            self.assertEqual(report["linked_cells"], 1)
            self.assertEqual(report["in_scope_cells"], 0)

            with (artifacts / f"grid_cells_{version}.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["in_scope"], "0")
