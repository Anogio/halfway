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
class BackendPaths:
    repo_root: Path
    artifacts_root: Path


@dataclass(frozen=True)
class BackendConfig:
    settings: AppSettings
    data: dict[str, Any]
    paths: BackendPaths


def load_backend_config() -> BackendConfig:
    repo_root = find_repo_root(Path.cwd())
    data = load_raw_settings(repo_root)
    settings = parse_settings(data)
    artifacts_root = (repo_root / settings.paths.offline_artifacts_dir).resolve()

    return BackendConfig(
        settings=settings,
        data=data,
        paths=BackendPaths(repo_root=repo_root, artifacts_root=artifacts_root),
    )


def get_city_settings(cfg: BackendConfig, city_id: str) -> CitySettings:
    city = cfg.settings.cities.get(city_id)
    if city is None:
        known = ", ".join(sorted(cfg.settings.cities))
        raise ValueError(f"Unknown city '{city_id}'. Known cities: {known}")
    return city


def get_city_artifacts_dir(cfg: BackendConfig, city_id: str) -> Path:
    return (cfg.paths.artifacts_root / city_id).resolve()
