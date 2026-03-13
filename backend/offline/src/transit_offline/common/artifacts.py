from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Iterable

GRAPH_ARTIFACT_PATTERNS = (
    "graph_*_weekday.json",
    "nodes_*.csv",
    "graph_report_*.json",
)

GRID_ARTIFACT_PATTERNS = (
    "grid_cells_*.csv",
    "grid_links_*.csv",
    "grid_report_*.json",
)

VALIDATION_ARTIFACT_PATTERNS = ("validation_*.json",)
EXPORT_ARTIFACT_PATTERNS = ("manifest_*.json",)


def archive_existing_artifacts(artifacts_dir: Path, *, patterns: Iterable[str]) -> list[Path]:
    matches: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(artifacts_dir.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            matches.append(path)

    if not matches:
        return []

    old_dir = artifacts_dir / "old"
    old_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    archived: list[Path] = []
    for path in matches:
        destination = old_dir / f"{stamp}_{path.name}"
        suffix = 1
        while destination.exists():
            destination = old_dir / f"{stamp}_{suffix}_{path.name}"
            suffix += 1
        shutil.move(str(path), str(destination))
        archived.append(destination)

    return archived
