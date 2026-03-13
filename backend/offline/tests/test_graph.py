from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.graph.pipeline import run_build_graph
from transit_offline.ingest.pipeline import run_ingest
from transit_shared.settings import parse_settings
from helpers import make_settings_data, write_csv


class GraphPipelineTest(unittest.TestCase):
    def test_build_graph_exports_json(self) -> None:
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
            write_csv(
                gtfs / "trips.txt",
                ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
                [
                    ["R1", "S1", "T1", "x", "", "0"],
                    ["R1", "S1", "T2", "x", "", "0"],
                ],
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
                    ["B", "", "Stop B", "48.8008", "2.301", "1", "", "0", "PS", ""],
                    ["C", "", "Stop C", "48.8015", "2.302", "1", "", "0", "PS", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:05:00", "08:05:00", "B", "1"],
                    ["T2", "08:10:00", "08:10:00", "A", "0"],
                    ["T2", "08:16:00", "08:16:00", "B", "1"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [["P1", "B", "C", "1", "1", "120", "100"]],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [["A", "C", "2", "180"]],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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

            run_ingest(config=cfg)
            report = run_build_graph(config=cfg)

            self.assertGreater(report["graph_edges"], 0)
            graph_path = artifacts / "graph_vtest_weekday.json"
            self.assertTrue(graph_path.exists())
            graph = json.loads(graph_path.read_text(encoding="utf-8"))
            self.assertEqual(graph["profile"], "weekday_non_holiday")
            self.assertEqual(graph["nodes_count"], 3)

    def test_build_graph_persists_node_rail_metadata_from_route_types(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            interim = root / "interim"
            artifacts = root / "artifacts"
            raw = root / "raw"

            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["B1", "A1", "B1", "Bus 1", "3"],
                    ["M1", "A1", "M1", "Metro 1", "1"],
                ],
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
            write_csv(
                gtfs / "trips.txt",
                ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
                [
                    ["B1", "S1", "TB1", "x", "", "0"],
                    ["M1", "S1", "TM1", "x", "", "0"],
                ],
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
                    ["BUS_A", "", "Bus A", "48.8", "2.3", "1", "", "0", "", ""],
                    ["BUS_B", "", "Bus B", "48.801", "2.301", "1", "", "0", "", ""],
                    ["RAIL_A", "", "Rail A", "48.802", "2.302", "1", "", "0", "", ""],
                    ["RAIL_B", "", "Rail B", "48.803", "2.303", "1", "", "0", "", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["TB1", "08:00:00", "08:00:00", "BUS_A", "0"],
                    ["TB1", "08:05:00", "08:05:00", "BUS_B", "1"],
                    ["TM1", "08:10:00", "08:10:00", "RAIL_A", "0"],
                    ["TM1", "08:15:00", "08:15:00", "RAIL_B", "1"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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
            data["modes"]["include_route_types"] = [1, 3]
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

            run_ingest(config=cfg)
            run_build_graph(config=cfg)

            with (artifacts / "nodes_vtest.csv").open(newline="", encoding="utf-8") as fh:
                rows = {row["stop_id"]: row for row in csv.DictReader(fh)}

            self.assertEqual(rows["BUS_A"]["is_rail_like"], "0")
            self.assertEqual(rows["BUS_B"]["is_rail_like"], "0")
            self.assertEqual(rows["RAIL_A"]["is_rail_like"], "1")
            self.assertEqual(rows["RAIL_B"]["is_rail_like"], "1")

    def test_build_graph_emits_v2_route_state_graph(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs"
            interim = root / "interim"
            artifacts = root / "artifacts"
            raw = root / "raw"

            write_csv(
                gtfs / "routes.txt",
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [
                    ["R1", "A1", "R1", "Route 1", "1"],
                    ["R2", "A1", "R2", "Route 2", "1"],
                ],
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
            write_csv(
                gtfs / "trips.txt",
                ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
                [
                    ["R1", "S1", "T1", "x", "", "0"],
                    ["R1", "S1", "T2", "x", "", "0"],
                    ["R2", "S1", "T3", "x", "", "0"],
                    ["R2", "S1", "T4", "x", "", "0"],
                ],
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
                    ["A", "", "Stop A", "48.8000", "2.3000", "1", "", "0", "H1", ""],
                    ["B", "", "Stop B", "48.8008", "2.3010", "1", "", "0", "H1", ""],
                    ["C", "", "Stop C", "48.8016", "2.3020", "1", "", "0", "H2", ""],
                    ["D", "", "Stop D", "48.8024", "2.3030", "1", "", "0", "H2", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:05:00", "08:05:00", "B", "1"],
                    ["T2", "08:10:00", "08:10:00", "A", "0"],
                    ["T2", "08:15:00", "08:15:00", "B", "1"],
                    ["T3", "08:02:00", "08:02:00", "C", "0"],
                    ["T3", "08:07:00", "08:07:00", "D", "1"],
                    ["T4", "08:12:00", "08:12:00", "C", "0"],
                    ["T4", "08:17:00", "08:17:00", "D", "1"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [["P1", "B", "C", "1", "1", "60", "180"]],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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
            data["modes"]["include_route_types"] = [1]
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

            run_ingest(config=cfg)
            run_build_graph(config=cfg)

            graph = json.loads((artifacts / "graph_v2_weekday.json").read_text(encoding="utf-8"))
            with (artifacts / "nodes_v2.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))

            self.assertEqual(graph["physical_nodes_count"], 4)
            self.assertEqual(graph["onboard_nodes_count"], 4)
            self.assertEqual(graph["nodes_count"], 8)

            row_by_key = {row["node_key"]: row for row in rows}
            self.assertEqual(row_by_key["A"]["node_kind"], "physical")
            self.assertEqual(row_by_key["B"]["node_kind"], "physical")
            self.assertEqual(row_by_key["A::R1::0"]["node_kind"], "onboard")
            self.assertEqual(row_by_key["C::R2::0"]["node_kind"], "onboard")

            idx_by_key = graph["node_key_index"]
            legend = {int(key): value for key, value in graph["edge_kind_legend"].items()}

            def edge_kind_and_weight(from_idx: int, to_idx: int) -> tuple[str, int] | None:
                start = graph["adj_offsets"][from_idx]
                end = graph["adj_offsets"][from_idx + 1]
                for edge_pos in range(start, end):
                    if int(graph["adj_targets"][edge_pos]) == to_idx:
                        return (
                            legend[int(graph["edge_kind"][edge_pos])],
                            int(graph["adj_weights_s"][edge_pos]),
                        )
                return None

            self.assertEqual(edge_kind_and_weight(idx_by_key["A"], idx_by_key["A::R1::0"])[0], "boarding")
            self.assertEqual(edge_kind_and_weight(idx_by_key["A::R1::0"], idx_by_key["B::R1::0"])[0], "ride")
            self.assertEqual(edge_kind_and_weight(idx_by_key["B::R1::0"], idx_by_key["B"])[0], "alight")
            self.assertEqual(edge_kind_and_weight(idx_by_key["B"], idx_by_key["C"])[0], "transfer_pathway")
            self.assertIsNone(edge_kind_and_weight(idx_by_key["A"], idx_by_key["B"]))

    def test_build_graph_synthesizes_hub_transfers_when_gtfs_transfers_missing(self) -> None:
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
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
                    ["A", "", "Stop A", "48.8000", "2.3000", "1", "", "0", "HUB1", ""],
                    ["B", "", "Stop B", "48.8002", "2.3002", "1", "", "0", "HUB1", ""],
                    ["C", "", "Stop C", "48.9000", "2.4000", "1", "", "0", "", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:05:00", "08:05:00", "C", "1"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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

            run_ingest(config=cfg)
            report = run_build_graph(config=cfg)

            self.assertGreater(report["transfer_edges_hub_synth"], 0)
            self.assertGreater(report["edge_kind_counts"]["transfer_gtfs"], 0)

    def test_build_graph_floors_zero_time_transfer_edges(self) -> None:
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
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
                    ["A", "", "Stop A", "48.8000", "2.3000", "1", "", "0", "PS", ""],
                    ["B", "", "Stop B", "48.8003", "2.3003", "1", "", "0", "PS", ""],
                    ["C", "", "Stop C", "48.8006", "2.3006", "1", "", "0", "PS", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:05:00", "08:05:00", "C", "1"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [["P1", "B", "C", "1", "1", "", "0"]],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [["A", "B", "2", "0"]],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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

            run_ingest(config=cfg)
            report = run_build_graph(config=cfg)
            graph = json.loads((artifacts / "graph_vtest_weekday.json").read_text(encoding="utf-8"))

            self.assertEqual(report["transfer_min_floor_s"], 120)
            self.assertGreaterEqual(report["pathway_edges_floored"], 1)
            self.assertGreaterEqual(report["transfer_edges_floored"], 1)

            idx_a = int(graph["nodes_index"]["A"])
            idx_b = int(graph["nodes_index"]["B"])
            idx_c = int(graph["nodes_index"]["C"])

            def edge_weight(from_idx: int, to_idx: int) -> int:
                start = graph["adj_offsets"][from_idx]
                end = graph["adj_offsets"][from_idx + 1]
                for edge_pos in range(start, end):
                    if int(graph["adj_targets"][edge_pos]) == to_idx:
                        return int(graph["adj_weights_s"][edge_pos])
                return -1

            self.assertEqual(edge_weight(idx_a, idx_b), 120)
            self.assertEqual(edge_weight(idx_b, idx_c), 120)

    def test_build_graph_amortizes_wait_over_trip_segments(self) -> None:
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
            write_csv(gtfs / "calendar_dates.txt", ["service_id", "date", "exception_type"], [])
            write_csv(
                gtfs / "trips.txt",
                ["route_id", "service_id", "trip_id", "trip_headsign", "trip_short_name", "direction_id"],
                [
                    ["R1", "S1", "T1", "x", "", "0"],
                    ["R1", "S1", "T2", "x", "", "0"],
                ],
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
                    ["A", "", "Stop A", "48.8", "2.3", "1", "", "0", "", ""],
                    ["B", "", "Stop B", "48.8008", "2.301", "1", "", "0", "", ""],
                    ["C", "", "Stop C", "48.8015", "2.302", "1", "", "0", "", ""],
                ],
            )
            write_csv(
                gtfs / "stop_times.txt",
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    ["T1", "08:00:00", "08:00:00", "A", "0"],
                    ["T1", "08:05:00", "08:05:00", "B", "1"],
                    ["T1", "08:10:00", "08:10:00", "C", "2"],
                    ["T2", "08:10:00", "08:10:00", "A", "0"],
                    ["T2", "08:15:00", "08:15:00", "B", "1"],
                    ["T2", "08:20:00", "08:20:00", "C", "2"],
                ],
            )
            write_csv(
                gtfs / "pathways.txt",
                [
                    "pathway_id",
                    "from_stop_id",
                    "to_stop_id",
                    "pathway_mode",
                    "is_bidirectional",
                    "length",
                    "traversal_time",
                ],
                [],
            )
            write_csv(
                gtfs / "transfers.txt",
                ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
                [],
            )
            write_csv(gtfs / "agency.txt", ["agency_id"], [["A1"]])
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

            run_ingest(config=cfg)
            report = run_build_graph(config=cfg)
            graph = json.loads((artifacts / "graph_vtest_weekday.json").read_text(encoding="utf-8"))

            self.assertGreaterEqual(report["trip_segment_stats"]["route_dirs_with_trip_segments"], 1)

            idx_a = int(graph["nodes_index"]["A"])
            idx_b = int(graph["nodes_index"]["B"])
            idx_c = int(graph["nodes_index"]["C"])

            def edge_weight(from_idx: int, to_idx: int) -> int:
                start = graph["adj_offsets"][from_idx]
                end = graph["adj_offsets"][from_idx + 1]
                for edge_pos in range(start, end):
                    if int(graph["adj_targets"][edge_pos]) == to_idx:
                        return int(graph["adj_weights_s"][edge_pos])
                return -1

            # avg ride 300s, route wait 300s, median trip segments=2 => 300 + 150 = 450.
            self.assertEqual(edge_weight(idx_a, idx_b), 450)
            self.assertEqual(edge_weight(idx_b, idx_c), 450)
