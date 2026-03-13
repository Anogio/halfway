from __future__ import annotations

from pathlib import Path
from typing import Any

import tomllib

from transit_shared.settings_parser import parse_settings
from transit_shared.settings_schema import (
    AppSettings,
    CityGeocodingSettings,
    CityPathsSettings,
    CityScopeSettings,
    CitySettings,
    GraphSettings,
    GridSettings,
    ModesSettings,
    PathsSettings,
    ProjectSettings,
    RuntimeSettings,
    SearchSettings,
    ServiceSettings,
    SettingsError,
    ValidationODPair,
    ValidationSettings,
    WeightSettings,
)

__all__ = [
    "SettingsError",
    "ProjectSettings",
    "PathsSettings",
    "CityPathsSettings",
    "CityScopeSettings",
    "ServiceSettings",
    "ModesSettings",
    "SearchSettings",
    "WeightSettings",
    "GridSettings",
    "RuntimeSettings",
    "GraphSettings",
    "CityGeocodingSettings",
    "CitySettings",
    "ValidationODPair",
    "ValidationSettings",
    "AppSettings",
    "find_repo_root",
    "load_raw_settings",
    "parse_settings",
]


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        direct_settings_path = candidate / "config" / "settings.toml"
        if direct_settings_path.exists():
            return direct_settings_path.resolve().parent.parent
        backend_settings_path = candidate / "backend" / "config" / "settings.toml"
        if backend_settings_path.exists():
            return backend_settings_path.resolve().parent.parent
    raise FileNotFoundError("Could not locate backend/config/settings.toml from current path")


def load_raw_settings(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "config" / "settings.toml"
    with path.open("rb") as fh:
        return tomllib.load(fh)
