from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from transit_shared.settings import (
    AppSettings,
    CitySettings,
    find_repo_root,
    load_raw_settings,
    parse_settings,
)


@dataclass(frozen=True)
class AppPaths:
    repo_root: Path
    city_id: str
    gtfs_input: Path
    offline_raw_root: Path
    offline_interim_root: Path
    offline_artifacts_root: Path
    offline_raw_dir: Path
    offline_interim_dir: Path
    offline_artifacts_dir: Path


@dataclass(frozen=True)
class AppConfig:
    settings: AppSettings
    city_id: str
    city: CitySettings
    data: dict[str, Any]
    paths: AppPaths


def load_config(city_id: str) -> AppConfig:
    repo_root = find_repo_root(Path.cwd())
    data = load_raw_settings(repo_root)
    settings = parse_settings(data)

    city = settings.cities.get(city_id)
    if city is None:
        known = ", ".join(sorted(settings.cities))
        raise ValueError(f"Unknown city '{city_id}'. Known cities: {known}")

    gtfs_input = (repo_root / city.paths.gtfs_input).resolve()
    offline_raw_root = (repo_root / settings.paths.offline_raw_dir).resolve()
    offline_interim_root = (repo_root / settings.paths.offline_interim_dir).resolve()
    offline_artifacts_root = (repo_root / settings.paths.offline_artifacts_dir).resolve()
    offline_raw_dir = (offline_raw_root / city_id).resolve()
    offline_interim_dir = (offline_interim_root / city_id).resolve()
    offline_artifacts_dir = (offline_artifacts_root / city_id).resolve()

    return AppConfig(
        settings=settings,
        city_id=city_id,
        city=city,
        data=data,
        paths=AppPaths(
            repo_root=repo_root,
            city_id=city_id,
            gtfs_input=gtfs_input,
            offline_raw_root=offline_raw_root,
            offline_interim_root=offline_interim_root,
            offline_artifacts_root=offline_artifacts_root,
            offline_raw_dir=offline_raw_dir,
            offline_interim_dir=offline_interim_dir,
            offline_artifacts_dir=offline_artifacts_dir,
        ),
    )


def ensure_dirs(config: AppConfig) -> None:
    config.paths.offline_raw_root.mkdir(parents=True, exist_ok=True)
    config.paths.offline_interim_root.mkdir(parents=True, exist_ok=True)
    config.paths.offline_artifacts_root.mkdir(parents=True, exist_ok=True)
    config.paths.offline_raw_dir.mkdir(parents=True, exist_ok=True)
    config.paths.offline_interim_dir.mkdir(parents=True, exist_ok=True)
    config.paths.offline_artifacts_dir.mkdir(parents=True, exist_ok=True)
