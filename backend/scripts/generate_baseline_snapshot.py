from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

from fastapi.testclient import TestClient

from transit_backend.api.server import app
from transit_backend.config.settings import get_city_artifacts_dir, load_backend_config


def percentile(values: list[float], p: float) -> float:
    idx = max(0, min(len(values) - 1, round((p / 100.0) * (len(values) - 1))))
    return values[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate API/artifact baseline snapshot.")
    parser.add_argument("--city", required=True, help="City id configured in backend/config/settings.toml")
    parser.add_argument(
        "--output-dir",
        default="../docs/debug/baseline-2026-03-09",
        help="Output folder for baseline files (default: %(default)s)",
    )
    args = parser.parse_args()

    city = args.city.strip()
    if not city:
        raise SystemExit("--city must not be empty")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)

    destination = {
        "city": city,
        "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}],
        "destination": {"lat": 48.8695, "lon": 2.3470},
    }

    metadata = client.get("/metadata").json()
    isochrones = client.post(
        "/multi_isochrones",
        json={"city": city, "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
    ).json()
    path = client.post("/multi_path", json=destination).json()

    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (out_dir / "isochrones_shape.json").write_text(
        json.dumps(
            {
                "keys": sorted(list(isochrones.keys())),
                "stats": isochrones.get("stats", {}),
                "feature_count": len(isochrones.get("feature_collection", {}).get("features", [])),
                "first_feature": (isochrones.get("feature_collection", {}).get("features") or [None])[0],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    first_path = (path.get("paths") or [None])[0]
    (out_dir / "path_shape.json").write_text(
        json.dumps(
            {
                "keys": sorted(list(path.keys())),
                "first_path_keys": sorted(list(first_path.keys())) if isinstance(first_path, dict) else [],
                "first_path_reachable": first_path.get("reachable") if isinstance(first_path, dict) else None,
                "first_path_summary": first_path.get("summary", {}) if isinstance(first_path, dict) else {},
                "first_path_first_segment": (first_path.get("segments") or [None])[0]
                if isinstance(first_path, dict)
                else None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    samples_ms = []
    for _ in range(40):
        start = time.perf_counter()
        response = client.post(
            "/multi_isochrones",
            json={"city": city, "origins": [{"id": "origin-1", "lat": 48.8566, "lon": 2.3522}]},
        )
        if response.status_code != 200:
            raise RuntimeError(f"/multi_isochrones failed: HTTP {response.status_code}")
        samples_ms.append((time.perf_counter() - start) * 1000.0)
    samples_ms.sort()
    (out_dir / "isochrones_latency_sample.json").write_text(
        json.dumps(
            {
                "samples": len(samples_ms),
                "p50_ms": round(percentile(samples_ms, 50), 2),
                "p95_ms": round(percentile(samples_ms, 95), 2),
                "max_ms": round(samples_ms[-1], 2),
                "mean_ms": round(statistics.mean(samples_ms), 2),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    cfg = load_backend_config()
    city_cfg = cfg.settings.cities.get(city)
    if city_cfg is None:
        raise RuntimeError(f"Unknown city '{city}'")

    version = city_cfg.artifact_version
    artifacts = get_city_artifacts_dir(cfg, city)
    files = [
        artifacts / f"graph_{version}_weekday.json",
        artifacts / f"nodes_{version}.csv",
        artifacts / f"grid_cells_{version}.csv",
        artifacts / f"grid_links_{version}.csv",
        artifacts / f"manifest_{version}.json",
        artifacts / f"validation_{version}.json",
    ]
    rows = []
    repo_root = cfg.paths.repo_root
    for file_path in files:
        if not file_path.exists():
            try:
                display_path = file_path.relative_to(repo_root).as_posix()
            except ValueError:
                display_path = file_path.as_posix()
            rows.append(f"MISSING  {display_path}")
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        try:
            display_path = file_path.relative_to(repo_root).as_posix()
        except ValueError:
            display_path = file_path.as_posix()
        rows.append(f"{digest}  {display_path}")
    (out_dir / "artifact_hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
