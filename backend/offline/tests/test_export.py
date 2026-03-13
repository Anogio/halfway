from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.export.pipeline import run_export
from transit_shared.settings import parse_settings
from helpers import make_settings_data


class ExportPipelineTest(unittest.TestCase):
    def test_manifest_written(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            interim = root / "interim"
            artifacts.mkdir(parents=True, exist_ok=True)
            interim.mkdir(parents=True, exist_ok=True)

            (artifacts / "graph_vx_weekday.json").write_text("{}", encoding="utf-8")
            (artifacts / "nodes_vx.csv").write_text("node_idx,stop_id\n", encoding="utf-8")
            (interim / "ingest_report.json").write_text(
                json.dumps({"feed_info": {"feed_version": "v1"}}),
                encoding="utf-8",
            )
            (artifacts / "graph_report_vx.json").write_text(
                json.dumps({"nodes": 1, "graph_edges": 2}), encoding="utf-8"
            )
            cfg_path = root / "config"
            cfg_path.mkdir(parents=True, exist_ok=True)
            (cfg_path / "settings.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

            data = make_settings_data(artifact_version="vx")
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
                    offline_interim_root=interim,
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=root / "raw",
                    offline_interim_dir=interim,
                    offline_artifacts_dir=artifacts,
                ),
            )

            out = run_export(config=cfg)
            self.assertEqual(out["version"], "vx")
            manifest_path = artifacts / "manifest_vx.json"
            self.assertTrue(manifest_path.exists())

    def test_export_archives_existing_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            artifacts = root / "artifacts"
            interim = root / "interim"
            artifacts.mkdir(parents=True, exist_ok=True)
            interim.mkdir(parents=True, exist_ok=True)

            (artifacts / "graph_vx_weekday.json").write_text("{}", encoding="utf-8")
            (artifacts / "nodes_vx.csv").write_text("node_idx,stop_id\n", encoding="utf-8")
            (artifacts / "manifest_v0.json").write_text("{}", encoding="utf-8")
            (interim / "ingest_report.json").write_text("{}", encoding="utf-8")
            (artifacts / "graph_report_vx.json").write_text(
                json.dumps({"nodes": 1, "graph_edges": 2}), encoding="utf-8"
            )
            cfg_path = root / "config"
            cfg_path.mkdir(parents=True, exist_ok=True)
            (cfg_path / "settings.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

            data = make_settings_data(artifact_version="vx")
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
                    offline_interim_root=interim,
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=root / "raw",
                    offline_interim_dir=interim,
                    offline_artifacts_dir=artifacts,
                ),
            )

            run_export(config=cfg)

            archived = list((artifacts / "old").glob("*_manifest_v0.json"))
            self.assertEqual(len(archived), 1)
            self.assertTrue((artifacts / "manifest_vx.json").exists())
