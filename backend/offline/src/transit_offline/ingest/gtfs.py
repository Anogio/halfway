from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

from transit_offline.cities.base import CityPlugin
from transit_offline.common.time import parse_gtfs_time_to_seconds

REQUIRED_FILES = [
    "agency.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "feed_info.txt",
    "pathways.txt",
    "routes.txt",
    "stop_times.txt",
    "stops.txt",
    "transfers.txt",
    "trips.txt",
]

WEEKDAY_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
ALL_DAY_COLUMNS = WEEKDAY_COLUMNS + ["saturday", "sunday"]
EXTENDED_BUS_ROUTE_TYPES = {
    "3",
    "700",
    "701",
    "702",
    "703",
    "704",
    "705",
    "706",
    "707",
    "708",
    "709",
    "710",
    "711",
    "712",
    "713",
    "714",
    "715",
    "716",
}


@dataclass(frozen=True)
class TripRecord:
    route_id: str
    direction_id: str
    service_id: str


def require_files(gtfs_dir: Path) -> None:
    missing = [name for name in REQUIRED_FILES if not (gtfs_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required GTFS files: {', '.join(missing)}")


def load_routes(
    gtfs_dir: Path,
    include_route_types: set[str],
    *,
    plugin: CityPlugin,
) -> tuple[set[str], dict[str, str], Counter]:
    route_ids: set[str] = set()
    route_to_type: dict[str, str] = {}
    mode_counter: Counter = Counter()

    with (gtfs_dir / "routes.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"route_id", "route_type"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("routes.txt missing required columns")

        for row in reader:
            route_type = (row.get("route_type") or "").strip()
            mode_counter[route_type] += 1
            if route_type in include_route_types and plugin.filter_route_row(row):
                route_id = row["route_id"].strip()
                route_ids.add(route_id)
                route_to_type[route_id] = route_type

    return route_ids, route_to_type, mode_counter


def _date_range(start_yyyymmdd: str, end_yyyymmdd: str) -> Iterable[date]:
    start = date(int(start_yyyymmdd[0:4]), int(start_yyyymmdd[4:6]), int(start_yyyymmdd[6:8]))
    end = date(int(end_yyyymmdd[0:4]), int(end_yyyymmdd[4:6]), int(end_yyyymmdd[6:8]))
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def load_weekday_service_ids(
    gtfs_dir: Path,
    weekdays_only: bool,
    exclude_holidays: bool,
) -> tuple[set[str], dict[str, int]]:
    """
    Build a weekday-only service set.

    We use calendar weekday flags, then apply calendar_dates removals (exception_type=2).
    Additions (exception_type=1) are ignored for the fixed non-holiday weekday profile.
    """
    weekday_service: set[str] = set()
    service_active_dates: dict[str, set[str]] = {}

    with (gtfs_dir / "calendar.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"service_id", *ALL_DAY_COLUMNS, "start_date", "end_date"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("calendar.txt missing required columns")

        day_columns = WEEKDAY_COLUMNS if weekdays_only else ALL_DAY_COLUMNS
        for row in reader:
            sid = row["service_id"].strip()
            active_weekdays = {idx for idx, col in enumerate(day_columns) if (row[col] or "0") == "1"}
            if not active_weekdays:
                continue

            dates = set()
            for d in _date_range(row["start_date"], row["end_date"]):
                if weekdays_only:
                    include = d.weekday() in active_weekdays
                else:
                    include = d.weekday() in {idx % 7 for idx in active_weekdays}
                if include:
                    dates.add(d.strftime("%Y%m%d"))
            if dates:
                weekday_service.add(sid)
                service_active_dates[sid] = dates

    if not exclude_holidays:
        final_all = {sid for sid, dates in service_active_dates.items() if dates}
        return final_all, {"removed_weekday_dates": 0}

    removals = 0
    with (gtfs_dir / "calendar_dates.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"service_id", "date", "exception_type"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("calendar_dates.txt missing required columns")

        for row in reader:
            sid = row["service_id"].strip()
            if sid not in service_active_dates:
                continue
            exception_type = (row.get("exception_type") or "").strip()
            date_str = (row.get("date") or "").strip()
            if exception_type == "2" and date_str in service_active_dates[sid]:
                service_active_dates[sid].remove(date_str)
                removals += 1

    final_weekday = {sid for sid, dates in service_active_dates.items() if dates}
    return final_weekday, {"removed_weekday_dates": removals}


def load_trips(
    gtfs_dir: Path, route_ids: set[str], weekday_service_ids: set[str]
) -> tuple[dict[str, TripRecord], Counter]:
    trips: dict[str, TripRecord] = {}
    direction_counter: Counter = Counter()

    with (gtfs_dir / "trips.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"trip_id", "route_id", "service_id", "direction_id"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("trips.txt missing required columns")

        for row in reader:
            route_id = row["route_id"].strip()
            service_id = row["service_id"].strip()
            if route_id not in route_ids:
                continue
            if service_id not in weekday_service_ids:
                continue
            trip_id = row["trip_id"].strip()
            direction_id = (row.get("direction_id") or "0").strip() or "0"
            direction_counter[direction_id] += 1
            trips[trip_id] = TripRecord(
                route_id=route_id,
                direction_id=direction_id,
                service_id=service_id,
            )

    return trips, direction_counter


def load_nodes(gtfs_dir: Path, *, plugin: CityPlugin) -> tuple[list[dict[str, str]], Counter]:
    nodes: list[dict[str, str]] = []
    location_counter: Counter = Counter()

    with (gtfs_dir / "stops.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {
            "stop_id",
            "stop_name",
            "stop_lat",
            "stop_lon",
            "parent_station",
            "location_type",
        }
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("stops.txt missing required columns")

        node_idx = 0
        for row in reader:
            location_type = (row.get("location_type") or "").strip()
            location_counter[location_type] += 1
            if location_type not in {"0", ""}:
                continue
            stop_id = row["stop_id"].strip()
            nodes.append(
                {
                    "node_idx": str(node_idx),
                    "stop_id": stop_id,
                    "stop_name": plugin.normalize_stop_name(
                        stop_id=stop_id,
                        stop_name=(row.get("stop_name") or "").strip(),
                        parent_station=(row.get("parent_station") or "").strip(),
                        location_type=location_type,
                    ),
                    "parent_station": (row.get("parent_station") or "").strip(),
                    "lat": row["stop_lat"].strip(),
                    "lon": row["stop_lon"].strip(),
                    "location_type": location_type,
                }
            )
            node_idx += 1

    return nodes, location_counter


def scan_stop_times(gtfs_dir: Path, trips: dict[str, TripRecord], node_ids: set[str]) -> dict[str, int]:
    rows = 0
    used_trip_ids: set[str] = set()
    used_stop_ids: set[str] = set()
    min_hour = 99
    max_hour = 0

    with (gtfs_dir / "stop_times.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        required = {"trip_id", "stop_id", "arrival_time", "departure_time", "stop_sequence"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("stop_times.txt missing required columns")

        for row in reader:
            trip_id = row["trip_id"].strip()
            if trip_id not in trips:
                continue
            stop_id = row["stop_id"].strip()
            if stop_id not in node_ids:
                continue

            rows += 1
            used_trip_ids.add(trip_id)
            used_stop_ids.add(stop_id)

            arrival = row.get("arrival_time") or ""
            if arrival:
                hour = int(arrival.split(":", 1)[0])
                min_hour = min(min_hour, hour)
                max_hour = max(max_hour, hour)

            # Validate parser on active rows
            parse_gtfs_time_to_seconds(row["arrival_time"].strip())
            parse_gtfs_time_to_seconds(row["departure_time"].strip())

    return {
        "filtered_stop_times_rows": rows,
        "filtered_stop_times_trip_ids": len(used_trip_ids),
        "filtered_stop_times_stop_ids": len(used_stop_ids),
        "min_hour": min_hour if rows else 0,
        "max_hour": max_hour if rows else 0,
    }


def load_feed_info(gtfs_dir: Path) -> dict[str, str]:
    with (gtfs_dir / "feed_info.txt").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        row = next(reader, None)
        return row or {}


def write_csv(path: Path, rows: Iterable[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
