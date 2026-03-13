from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from transit_offline.common.artifacts import EXPORT_ARTIFACT_PATTERNS, archive_existing_artifacts
from transit_offline.common.config import AppConfig, ensure_dirs, load_config


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _config_hash(config_path: Path) -> str:
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def run_export(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    ensure_dirs(cfg)

    version = cfg.city.artifact_version
    artifacts_dir = cfg.paths.offline_artifacts_dir

    artifact_candidates = [
        artifacts_dir / f"graph_{version}_weekday.json",
        artifacts_dir / f"nodes_{version}.csv",
        artifacts_dir / f"grid_cells_{version}.csv",
        artifacts_dir / f"grid_links_{version}.csv",
        artifacts_dir / f"validation_{version}.json",
    ]

    artifacts = []
    for path in artifact_candidates:
        if path.exists():
            artifacts.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )

    ingest_report_path = cfg.paths.offline_interim_dir / "ingest_report.json"
    ingest_report = {}
    if ingest_report_path.exists():
        ingest_report = json.loads(ingest_report_path.read_text(encoding="utf-8"))

    graph_report_path = artifacts_dir / f"graph_report_{version}.json"
    graph_report = {}
    if graph_report_path.exists():
        graph_report = json.loads(graph_report_path.read_text(encoding="utf-8"))

    manifest = {
        "city": cfg.city_id,
        "version": version,
        "profile": "weekday_non_holiday",
        "build_timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
        "config_hash": _config_hash(cfg.paths.repo_root / "config" / "settings.toml"),
        "feed_info": ingest_report.get("feed_info", {}),
        "counts": {
            "nodes": graph_report.get("nodes", 0),
            "edges": graph_report.get("graph_edges", 0),
        },
        "artifacts": artifacts,
    }

    archive_existing_artifacts(artifacts_dir, patterns=EXPORT_ARTIFACT_PATTERNS)

    manifest_path = artifacts_dir / f"manifest_{version}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest
