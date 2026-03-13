from __future__ import annotations

import csv
from pathlib import Path

from transit_offline.sources.models import (
    NormalizedDataset,
)


def _write_table(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_normalized_dataset(dataset: NormalizedDataset, out_dir: Path) -> list[Path]:
    """
    Write a normalized dataset to the GTFS files expected by the ingest pipeline.

    This is scaffold-level functionality: city adapters own parsing/mapping into
    `NormalizedDataset`; this writer only serializes deterministic CSV outputs.
    """

    written: list[Path] = []

    agency_path = out_dir / "agency.txt"
    _write_table(
        agency_path,
        ["agency_id", "agency_name", "agency_url", "agency_timezone"],
        [
            {
                "agency_id": row.agency_id,
                "agency_name": row.agency_name,
                "agency_url": row.agency_url,
                "agency_timezone": row.agency_timezone,
            }
            for row in dataset.agencies
        ],
    )
    written.append(agency_path)

    stops_path = out_dir / "stops.txt"
    _write_table(
        stops_path,
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
        [
            {
                "stop_id": row.stop_id,
                "stop_name": row.stop_name,
                "stop_lat": row.stop_lat,
                "stop_lon": row.stop_lon,
                "location_type": row.location_type,
                "parent_station": row.parent_station,
            }
            for row in dataset.stops
        ],
    )
    written.append(stops_path)

    routes_path = out_dir / "routes.txt"
    _write_table(
        routes_path,
        ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
        [
            {
                "route_id": row.route_id,
                "agency_id": row.agency_id,
                "route_short_name": row.route_short_name,
                "route_long_name": row.route_long_name,
                "route_type": row.route_type,
            }
            for row in dataset.routes
        ],
    )
    written.append(routes_path)

    trips_path = out_dir / "trips.txt"
    _write_table(
        trips_path,
        ["route_id", "service_id", "trip_id", "direction_id"],
        [
            {
                "route_id": row.route_id,
                "service_id": row.service_id,
                "trip_id": row.trip_id,
                "direction_id": row.direction_id,
            }
            for row in dataset.trips
        ],
    )
    written.append(trips_path)

    stop_times_path = out_dir / "stop_times.txt"
    _write_table(
        stop_times_path,
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        [
            {
                "trip_id": row.trip_id,
                "arrival_time": row.arrival_time,
                "departure_time": row.departure_time,
                "stop_id": row.stop_id,
                "stop_sequence": row.stop_sequence,
            }
            for row in dataset.stop_times
        ],
    )
    written.append(stop_times_path)

    calendar_path = out_dir / "calendar.txt"
    _write_table(
        calendar_path,
        [
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ],
        [
            {
                "service_id": row.service_id,
                "monday": row.monday,
                "tuesday": row.tuesday,
                "wednesday": row.wednesday,
                "thursday": row.thursday,
                "friday": row.friday,
                "saturday": row.saturday,
                "sunday": row.sunday,
                "start_date": row.start_date,
                "end_date": row.end_date,
            }
            for row in dataset.calendars
        ],
    )
    written.append(calendar_path)

    calendar_dates_path = out_dir / "calendar_dates.txt"
    _write_table(
        calendar_dates_path,
        ["service_id", "date", "exception_type"],
        [
            {
                "service_id": row.service_id,
                "date": row.date,
                "exception_type": row.exception_type,
            }
            for row in dataset.calendar_dates
        ],
    )
    written.append(calendar_dates_path)

    transfers_path = out_dir / "transfers.txt"
    _write_table(
        transfers_path,
        ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
        [
            {
                "from_stop_id": row.from_stop_id,
                "to_stop_id": row.to_stop_id,
                "transfer_type": row.transfer_type,
                "min_transfer_time": row.min_transfer_time,
            }
            for row in dataset.transfers
        ],
    )
    written.append(transfers_path)

    pathways_path = out_dir / "pathways.txt"
    _write_table(
        pathways_path,
        [
            "pathway_id",
            "from_stop_id",
            "to_stop_id",
            "pathway_mode",
            "is_bidirectional",
            "length",
            "traversal_time",
        ],
        [
            {
                "pathway_id": row.pathway_id,
                "from_stop_id": row.from_stop_id,
                "to_stop_id": row.to_stop_id,
                "pathway_mode": row.pathway_mode,
                "is_bidirectional": row.is_bidirectional,
                "length": row.length,
                "traversal_time": row.traversal_time,
            }
            for row in dataset.pathways
        ],
    )
    written.append(pathways_path)

    feed_info_path = out_dir / "feed_info.txt"
    _write_table(
        feed_info_path,
        [
            "feed_publisher_name",
            "feed_publisher_url",
            "feed_lang",
            "feed_start_date",
            "feed_end_date",
            "feed_version",
        ],
        [
            {
                "feed_publisher_name": row.feed_publisher_name,
                "feed_publisher_url": row.feed_publisher_url,
                "feed_lang": row.feed_lang,
                "feed_start_date": row.feed_start_date,
                "feed_end_date": row.feed_end_date,
                "feed_version": row.feed_version,
            }
            for row in dataset.feed_info
        ],
    )
    written.append(feed_info_path)

    return written
