from __future__ import annotations

import csv
from pathlib import Path

from transit_offline.sources.validators import read_feed_info_first_row


def build_london_identity_warnings(gtfs_dir: Path, bbox: tuple[float, float, float, float]) -> list[str]:
    warnings: list[str] = []
    feed_info = read_feed_info_first_row(gtfs_dir)
    publisher_url = (feed_info.get("feed_publisher_url") or "").strip().lower()
    publisher_name = (feed_info.get("feed_publisher_name") or "").strip()

    if feed_info and publisher_url and ".ca" in publisher_url:
        warnings.append(
            f"feed_info publisher_url looks non-UK ('{publisher_url}'). "
            "Verify this is London, UK data."
        )
    if feed_info and publisher_url and "tfl" not in publisher_url:
        warnings.append(
            "feed_info publisher_url does not mention TfL. "
            f"Current value: '{publisher_url}' ({publisher_name})"
        )

    stops_path = gtfs_dir / "stops.txt"
    if not stops_path.exists():
        return warnings

    min_lon, min_lat, max_lon, max_lat = bbox
    total = 0
    in_bbox = 0
    with stops_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            lat_raw = (row.get("stop_lat") or "").strip()
            lon_raw = (row.get("stop_lon") or "").strip()
            if not lat_raw or not lon_raw:
                continue
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
            except ValueError:
                continue
            total += 1
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                in_bbox += 1

    if total and in_bbox == 0:
        warnings.append(
            "No stops found inside configured London bbox. "
            "This feed likely does not represent London, UK."
        )

    return warnings
