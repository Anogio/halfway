from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.ingest.pipeline import run_ingest
from transit_shared.settings import parse_settings
from helpers import make_settings_data, write_csv


class IngestPipelineTest(unittest.TestCase):
    def test_ingest_builds_weekday_subset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            interim = root / "interim"
            artifacts = root / "artifacts"
            raw = root / "raw"

            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [["R1", "A1", "R1", "Route 1", "3"]],
            )
            write_csv(
                gtfs / "calendar.txt",
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
                [["S1", "1", "1", "1", "1", "1", "0", "0", "20260101", "20260131"]],
            )
            write_csv(
                gtfs / "calendar_dates.txt",
                ["service_id", "date", "exception_type"],
                [["S1", "20260102", "2"]],
            )
            write_csv(
                gtfs / "trips.txt",
                ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
                [["R1", "S1", "T1", "x", "", "0"]],
            )
            write_csv(
                gtfs / "stops.txt",
                [
                    "stop_id",
                    "stop_code",
                    "stop_name",
                    "stop_lat",
                    "stop_lon",
                    "wheelchair_boarding",
                    "stop_timezone",
                    "location_type",
                    "parent_station",
                    "level_id",
                ],
                [
                    ["A", "", "Stop A", "48.8", "2.3", "1", "", "0", "PS", ""],
                    ["B", "", "Stop B", "48.9", "2.4", "1", "", "0", "PS", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                [
                    "trip_id",
                    "arrival_time",
                    "departure_time",
                    "stop_id",
                    "stop_sequence",
                ],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:10:00", "08:10:00", "B", "1"],
                ],
            )

            # required but not used deeply in this unit test
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
            write_csv(gtfs / "pathways.txt", ["pathway_id", "from_stop_id", "to_stop_id", "pathway_mode", "is_bidirectional", "length", "traversal_time"], [])
            write_csv(gtfs / "transfers.txt", ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"], [])
            write_csv(
                gtfs / "feed_info.txt",
                [
                    "feed_publisher_name",
                    "feed_publisher_url",
                    "feed_lang",
                    "feed_start_date",
                    "feed_end_date",
                    "feed_version",
                ],
                [["x", "https://x", "EN", "20260101", "20260131", "v1"]],
            )

            data = make_settings_data(artifact_version="vtest")
            data["modes"]["include_route_types"] = [3]
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="paris",
                city=settings.cities["paris"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="paris",
                    gtfs_input=gtfs,
                    offline_raw_root=raw,
                    offline_interim_root=interim,
                    offline_artifacts_root=artifacts,
                    offline_raw_dir=raw,
                    offline_interim_dir=interim,
                    offline_artifacts_dir=artifacts,
                ),
            )

            report = run_ingest(config=cfg)
            self.assertEqual(report["counts"]["routes_selected"], 1)
            self.assertEqual(report["counts"]["trips_selected"], 1)
            self.assertEqual(report["counts"]["nodes_selected"], 2)
            self.assertEqual(report["counts"]["filtered_stop_times_rows"], 2)

            trips_path = interim / "trips_weekday.csv"
            self.assertTrue(trips_path.exists())
            ingest_report_path = interim / "ingest_report.json"
            loaded = json.loads(ingest_report_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["counts"]["filtered_stop_times_trip_ids"], 1)
