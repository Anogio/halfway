from __future__ import annotations

import csv
from pathlib import Path

from transit_offline.ingest.gtfs import REQUIRED_FILES


def find_missing_required_gtfs_files(gtfs_dir: Path) -> list[str]:
    return [name for name in REQUIRED_FILES if not (gtfs_dir / name).exists()]


def read_feed_info_first_row(gtfs_dir: Path) -> dict[str, str]:
    path = gtfs_dir / "feed_info.txt"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        row = next(reader, None)
    return row or {}
