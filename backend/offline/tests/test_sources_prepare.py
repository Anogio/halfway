from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import make_settings_data
from transit_offline.common.config import AppConfig, AppPaths
from transit_offline.sources.pipeline import run_prepare_data
from transit_shared.settings import parse_settings


def _with_london_city(data: dict[str, object]) -> dict[str, object]:
    data["cities"]["london"] = {
        "label": "London",
        "artifact_version": "v1",
        "paths": {"gtfs_input": "backend/offline/data/gtfs/london"},
        "scope": {
            "use_bbox": True,
            "bbox": [-0.5103, 51.2868, 0.3340, 51.6923],
            "default_view": [51.5074, -0.1278, 11],
        },
        "geocoding": {
            "country_codes": "gb",
            "viewbox": "-0.5103,51.2868,0.3340,51.6923",
            "bounded": True,
        },
        "validation": {
            "mape_threshold": 0.3,
            "range_tolerance_ratio": 0.25,
            "performance_p95_ms_threshold": 1500,
            "od_pairs": [
                {
                    "name": "A-B",
                    "from_lat": 51.50,
                    "from_lon": -0.12,
                    "to_lat": 51.52,
                    "to_lon": -0.10,
                    "expected_min_s": 600,
                    "expected_max_s": 2400,
                }
            ],
        },
    }
    return data


def _with_madrid_city(data: dict[str, object]) -> dict[str, object]:
    data["cities"]["madrid"] = {
        "label": "Madrid",
        "artifact_version": "v1",
        "paths": {"gtfs_input": "backend/offline/data/gtfs/madrid"},
        "scope": {
            "use_bbox": True,
            "bbox": [-3.9200, 40.2700, -3.5050, 40.6450],
            "default_view": [40.4168, -3.7038, 10],
        },
        "geocoding": {
            "country_codes": "es",
            "viewbox": "-3.9200,40.2700,-3.5050,40.6450",
            "bounded": True,
        },
        "validation": {
            "mape_threshold": 0.25,
            "range_tolerance_ratio": 0.30,
            "performance_p95_ms_threshold": 2000,
            "od_pairs": [
                {
                    "name": "A-B",
                    "from_lat": 40.4168,
                    "from_lon": -3.7038,
                    "to_lat": 40.4463,
                    "to_lon": -3.6925,
                    "expected_min_s": 600,
                    "expected_max_s": 2400,
                }
            ],
        },
    }
    return data


def _csv_text(header: list[str], rows: list[list[str]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _write_gtfs_zip(path: Path, tables: dict[str, tuple[list[str], list[list[str]]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, (header, rows) in tables.items():
            zf.writestr(name, _csv_text(header, rows))


def _make_minimal_madrid_zip(path: Path, *, agency_id: str, route_id: str, route_short_name: str, route_type: str) -> None:
    _write_gtfs_zip(
        path,
        {
            "agency.txt": (
                ["agency_id", "agency_name", "agency_url", "agency_timezone"],
                [[agency_id, agency_id.upper(), "https://example.test", "Europe/Madrid"]],
            ),
            "routes.txt": (
                ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                [[route_id, "", route_short_name, f"{route_short_name} long", route_type]],
            ),
            "stops.txt": (
                ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
                [
                    [f"{route_id}-A", f"{route_short_name} A", "40.40", "-3.70", "0", ""],
                    [f"{route_id}-B", f"{route_short_name} B", "40.41", "-3.69", "0", ""],
                ],
            ),
            "trips.txt": (
                ["route_id", "service_id", "trip_id", "direction_id"],
                [[route_id, f"{route_id}-WK", f"{route_id}-TRIP", "0"]],
            ),
            "stop_times.txt": (
                ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                [
                    [f"{route_id}-TRIP", "08:00:00", "08:00:00", f"{route_id}-A", "1"],
                    [f"{route_id}-TRIP", "08:10:00", "08:10:00", f"{route_id}-B", "2"],
                ],
            ),
            "calendar.txt": (
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
                [[f"{route_id}-WK", "1", "1", "1", "1", "1", "0", "0", "20260101", "20261231"]],
            ),
            "calendar_dates.txt": (["service_id", "date", "exception_type"], []),
            "feed_info.txt": (
                [
                    "feed_publisher_name",
                    "feed_publisher_url",
                    "feed_lang",
                    "feed_start_date",
                    "feed_end_date",
                    "feed_version",
                ],
                [[agency_id.upper(), "https://example.test", "es", "20260101", "20261231", f"{route_id}-v1"]],
            ),
        },
    )


class PrepareDataPipelineTest(unittest.TestCase):
    def test_prepare_data_uses_registered_direct_gtfs_adapter_for_paris(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = make_settings_data(artifact_version="v1")
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="paris",
                city=settings.cities["paris"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="paris",
                    gtfs_input=root / "gtfs" / "paris",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=root / "raw" / "paris",
                    offline_interim_dir=root / "interim" / "paris",
                    offline_artifacts_dir=root / "artifacts" / "paris",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["adapter"], "direct_gtfs")
            self.assertEqual(report["status"], "ready_for_ingest")

            report_path = cfg.paths.offline_interim_dir / "prepare_report.json"
            self.assertTrue(report_path.exists())
            loaded = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["city"], "paris")

    def test_prepare_data_london_blocks_when_raw_sources_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gtfs = root / "gtfs" / "london"

            data = make_settings_data(artifact_version="v1")
            _with_london_city(data)
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="london",
                city=settings.cities["london"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="london",
                    gtfs_input=gtfs,
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=root / "raw" / "london",
                    offline_interim_dir=root / "interim" / "london",
                    offline_artifacts_dir=root / "artifacts" / "london",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["adapter"], "london_scaffold")
            self.assertEqual(report["status"], "blocked_missing_raw_sources")
            missing = " | ".join(report["missing_required_files"])
            self.assertIn("bus/bus-stops-live.csv", missing)

    def test_prepare_data_london_generates_gtfs_from_raw_sources(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_london = root / "raw" / "london"
            gtfs = root / "gtfs" / "london"

            (raw_london / "bus").mkdir(parents=True, exist_ok=True)
            (raw_london / "stationdata" / "gtfs").mkdir(parents=True, exist_ok=True)
            (raw_london / "journey").mkdir(parents=True, exist_ok=True)

            with (raw_london / "bus" / "bus-stops-live.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "Stop_Code_LBSL",
                        "Bus_Stop_Code",
                        "Naptan_Atco",
                        "Stop_Name",
                        "Location_Easting",
                        "Location_Northing",
                        "Heading",
                        "Stop_Area",
                        "Virtual_Bus_Stop",
                    ]
                )
                writer.writerow(["1", "1", "490000000A", "Stop A", "", "", "", "", "0"])
                writer.writerow(["2", "2", "490000000B", "Stop B", "", "", "", "", "0"])

            with (raw_london / "bus" / "bus-sequences-live.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "Route",
                        "Run",
                        "Sequence",
                        "Stop_Code_LBSL",
                        "Bus_Stop_Code",
                        "Naptan_Atco",
                        "Stop_Name",
                        "Location_Easting",
                        "Location_Northing",
                        "Heading",
                        "Virtual_Bus_Stop",
                    ]
                )
                writer.writerow(["1", "1", "1", "1", "1", "490000000A", "Stop A", "", "", "", "0"])
                writer.writerow(["1", "1", "2", "2", "2", "490000000B", "Stop B", "", "", "", "0"])

            stop_points_payload = {
                "stopPoints": [
                    {"naptanId": "490000000A", "commonName": "Stop A", "lat": 51.5001, "lon": -0.1201},
                    {"naptanId": "490000000B", "commonName": "Stop B", "lat": 51.5008, "lon": -0.1210},
                ]
            }
            (raw_london / "bus" / "stoppoint-mode-bus-all.json").write_text(
                json.dumps(stop_points_payload), encoding="utf-8"
            )

            with (raw_london / "stationdata" / "gtfs" / "stops.txt").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"])
                writer.writerow(["STN_A", "Station A", "51.5010", "-0.1190", "0", ""])

            with (raw_london / "stationdata" / "gtfs" / "pathways.txt").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "pathway_id",
                        "from_stop_id",
                        "to_stop_id",
                        "pathway_mode",
                        "is_bidirectional",
                        "length",
                        "traversal_time",
                    ]
                )
                writer.writerow(["P1", "STN_A", "STN_A", "1", "0", "10", "20"])

            with (raw_london / "stationdata" / "gtfs" / "feed_info.txt").open(
                "w", newline="", encoding="utf-8"
            ) as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "feed_publisher_name",
                        "feed_publisher_url",
                        "feed_lang",
                        "feed_start_date",
                    ]
                )
                writer.writerow(["Transport for London", "https://tfl.gov.uk", "en", "20260309"])

            data = make_settings_data(artifact_version="v1")
            _with_london_city(data)
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="london",
                city=settings.cities["london"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="london",
                    gtfs_input=gtfs,
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=raw_london,
                    offline_interim_dir=root / "interim" / "london",
                    offline_artifacts_dir=root / "artifacts" / "london",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["status"], "ready_for_ingest")
            self.assertTrue(report["ready_for_ingest"])
            self.assertTrue((gtfs / "routes.txt").exists())
            self.assertTrue((gtfs / "trips.txt").exists())
            self.assertTrue((gtfs / "stop_times.txt").exists())

            with (gtfs / "stop_times.txt").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertGreater(len(rows), 0)

    def test_prepare_data_madrid_blocks_when_required_sources_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = make_settings_data(artifact_version="v1")
            _with_madrid_city(data)
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="madrid",
                city=settings.cities["madrid"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="madrid",
                    gtfs_input=root / "gtfs" / "madrid",
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=root / "raw" / "madrid",
                    offline_interim_dir=root / "interim" / "madrid",
                    offline_artifacts_dir=root / "artifacts" / "madrid",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["adapter"], "madrid_gtfs_merge")
            self.assertEqual(report["status"], "blocked_missing_raw_sources")
            missing = " | ".join(report["missing_required_files"])
            self.assertIn("Metro", missing)
            self.assertIn("Interurban buses", missing)

    def test_prepare_data_madrid_merges_public_gtfs_archives(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_madrid = root / "raw" / "madrid"
            gtfs = root / "gtfs" / "madrid"

            _make_minimal_madrid_zip(raw_madrid / "google_transit_M4.zip", agency_id="CRTM", route_id="M4-1", route_short_name="1", route_type="1")
            _make_minimal_madrid_zip(raw_madrid / "google_transit_M10.zip", agency_id="ML", route_id="ML1", route_short_name="ML1", route_type="0")
            _make_minimal_madrid_zip(raw_madrid / "google_transit_M6.zip", agency_id="EMT", route_id="EMT-27", route_short_name="27", route_type="3")
            _make_minimal_madrid_zip(raw_madrid / "google_transit_M9.zip", agency_id="URB", route_id="U1", route_short_name="U1", route_type="3")
            _make_minimal_madrid_zip(raw_madrid / "google_transit_M89.zip", agency_id="INT", route_id="I1", route_short_name="I1", route_type="3")

            data = make_settings_data(artifact_version="v1")
            _with_madrid_city(data)
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="madrid",
                city=settings.cities["madrid"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="madrid",
                    gtfs_input=gtfs,
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=raw_madrid,
                    offline_interim_dir=root / "interim" / "madrid",
                    offline_artifacts_dir=root / "artifacts" / "madrid",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["adapter"], "madrid_gtfs_merge")
            self.assertEqual(report["status"], "ready_for_ingest")
            self.assertTrue(report["ready_for_ingest"])
            self.assertIn("Cercanias", " | ".join(report["warnings"]))

            with (gtfs / "routes.txt").open(newline="", encoding="utf-8") as fh:
                routes = list(csv.DictReader(fh))
            self.assertEqual(len(routes), 5)
            routes_by_id = {row["route_id"]: row for row in routes}
            self.assertIn("metro__M4-1", routes_by_id)
            self.assertEqual(routes_by_id["metro__M4-1"]["agency_id"], "metro__CRTM")

            with (gtfs / "transfers.txt").open(newline="", encoding="utf-8") as fh:
                transfers = list(csv.DictReader(fh))
            self.assertEqual(transfers, [])

            with (gtfs / "feed_info.txt").open(newline="", encoding="utf-8") as fh:
                feed_info = next(csv.DictReader(fh))
            self.assertEqual(feed_info["feed_lang"], "es")
            self.assertEqual(feed_info["feed_start_date"], "20260101")

    def test_prepare_data_london_parses_non_bus_journey_xml(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_london = root / "raw" / "london"
            gtfs = root / "gtfs" / "london"

            (raw_london / "bus").mkdir(parents=True, exist_ok=True)
            (raw_london / "stationdata" / "gtfs").mkdir(parents=True, exist_ok=True)
            (raw_london / "stationdata" / "detailed").mkdir(parents=True, exist_ok=True)
            journey_dir = raw_london / "journey" / "live_unpacked" / "LULDLRTRAMRIVERCABLE_FULL_20260309"
            journey_dir.mkdir(parents=True, exist_ok=True)

            with (raw_london / "bus" / "bus-stops-live.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "Stop_Code_LBSL",
                        "Bus_Stop_Code",
                        "Naptan_Atco",
                        "Stop_Name",
                        "Location_Easting",
                        "Location_Northing",
                        "Heading",
                        "Stop_Area",
                        "Virtual_Bus_Stop",
                    ]
                )

            with (raw_london / "bus" / "bus-sequences-live.csv").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "Route",
                        "Run",
                        "Sequence",
                        "Stop_Code_LBSL",
                        "Bus_Stop_Code",
                        "Naptan_Atco",
                        "Stop_Name",
                        "Location_Easting",
                        "Location_Northing",
                        "Heading",
                        "Virtual_Bus_Stop",
                    ]
                )

            (raw_london / "bus" / "stoppoint-mode-bus-all.json").write_text(
                json.dumps({"stopPoints": []}), encoding="utf-8"
            )

            with (raw_london / "stationdata" / "gtfs" / "stops.txt").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"])
                writer.writerow(["STN_A", "Station A", "51.5010", "-0.1190", "0", ""])
                # Existing stop without parent to validate upsert from detailed platform mapping.
                writer.writerow(["9400ZZTESTA", "Test Alpha", "51.5000", "-0.1200", "0", ""])

            with (raw_london / "stationdata" / "gtfs" / "pathways.txt").open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "pathway_id",
                        "from_stop_id",
                        "to_stop_id",
                        "pathway_mode",
                        "is_bidirectional",
                        "length",
                        "traversal_time",
                    ]
                )

            with (raw_london / "stationdata" / "gtfs" / "feed_info.txt").open(
                "w", newline="", encoding="utf-8"
            ) as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "feed_publisher_name",
                        "feed_publisher_url",
                        "feed_lang",
                        "feed_start_date",
                    ]
                )
                writer.writerow(["Transport for London", "https://tfl.gov.uk", "en", "20260309"])

            with (raw_london / "stationdata" / "detailed" / "Platforms.csv").open(
                "w", newline="", encoding="utf-8"
            ) as fh:
                writer = csv.writer(fh)
                writer.writerow(
                    [
                        "UniqueId",
                        "StationUniqueId",
                        "PlatformNumber",
                        "CardinalDirection",
                        "PlatformNaptanCode",
                        "FriendlyName",
                        "IsCustomerFacing",
                        "HasServiceInterchange",
                        "AccessibleEntranceName",
                        "HasStepFreeRouteInformation",
                    ]
                )
                writer.writerow(
                    [
                        "HUBTEST-Plat01",
                        "HUBTEST",
                        "1",
                        "Northbound",
                        "9400ZZTESTA",
                        "Test Platform",
                        "TRUE",
                        "FALSE",
                        "",
                        "TRUE",
                    ]
                )

            xml_payload = """<?xml version="1.0" encoding="utf-8"?>
<TransXChange xmlns="http://www.transxchange.org.uk/">
  <StopPoints>
    <StopPoint>
      <AtcoCode>9400ZZTESTA</AtcoCode>
      <Descriptor><CommonName>Test Alpha</CommonName></Descriptor>
      <Place><Location><Easting>530000</Easting><Northing>180000</Northing></Location></Place>
    </StopPoint>
    <StopPoint>
      <AtcoCode>9400ZZTESTB</AtcoCode>
      <Descriptor><CommonName>Test Beta</CommonName></Descriptor>
      <Place><Location><Easting>530500</Easting><Northing>180200</Northing></Location></Place>
    </StopPoint>
  </StopPoints>
  <JourneyPatternSections>
    <JourneyPatternSection id="JPS_TEST_1">
      <JourneyPatternTimingLink>
        <From><StopPointRef>9400ZZTESTA</StopPointRef></From>
        <To><StopPointRef>9400ZZTESTB</StopPointRef></To>
        <RunTime>PT4M</RunTime>
      </JourneyPatternTimingLink>
    </JourneyPatternSection>
  </JourneyPatternSections>
  <Operators>
    <Operator id="OP_TEST"><OperatorShortName>TfL Test</OperatorShortName></Operator>
  </Operators>
  <Services>
    <Service>
      <ServiceCode>1-TST-_-y05-1</ServiceCode>
      <Lines><Line><LineName>Test Line</LineName></Line></Lines>
      <OperatingProfile><RegularDayType><DaysOfWeek><MondayToFriday /></DaysOfWeek></RegularDayType></OperatingProfile>
      <RegisteredOperatorRef>OP_TEST</RegisteredOperatorRef>
      <Mode>underground</Mode>
      <Description>Alpha - Beta</Description>
      <StandardService>
        <JourneyPattern id="JP_TEST_1">
          <Direction>inbound</Direction>
          <JourneyPatternSectionRefs>JPS_TEST_1</JourneyPatternSectionRefs>
        </JourneyPattern>
      </StandardService>
    </Service>
  </Services>
  <VehicleJourneys>
    <VehicleJourney>
      <VehicleJourneyCode>VJ_TEST_1</VehicleJourneyCode>
      <ServiceRef>1-TST-_-y05-1</ServiceRef>
      <JourneyPatternRef>JP_TEST_1</JourneyPatternRef>
      <DepartureTime>08:00:00</DepartureTime>
    </VehicleJourney>
  </VehicleJourneys>
</TransXChange>
"""
            (journey_dir / "tfl_1-TST-_-y05-1.xml").write_text(xml_payload, encoding="utf-8")

            data = make_settings_data(artifact_version="v1")
            _with_london_city(data)
            settings = parse_settings(data)
            cfg = AppConfig(
                settings=settings,
                city_id="london",
                city=settings.cities["london"],
                data=data,
                paths=AppPaths(
                    repo_root=root,
                    city_id="london",
                    gtfs_input=gtfs,
                    offline_raw_root=root / "raw",
                    offline_interim_root=root / "interim",
                    offline_artifacts_root=root / "artifacts",
                    offline_raw_dir=raw_london,
                    offline_interim_dir=root / "interim" / "london",
                    offline_artifacts_dir=root / "artifacts" / "london",
                ),
            )

            report = run_prepare_data(config=cfg)
            self.assertEqual(report["status"], "ready_for_ingest")
            stats = report["details"]["stats"]
            self.assertGreater(stats["journey_trips_built"], 0)

            with (gtfs / "routes.txt").open(newline="", encoding="utf-8") as fh:
                routes = list(csv.DictReader(fh))
            self.assertTrue(any(r["route_id"] == "TXC_1_TST_y05_1" and r["route_type"] == "1" for r in routes))

            with (gtfs / "stops.txt").open(newline="", encoding="utf-8") as fh:
                stops = {row["stop_id"]: row for row in csv.DictReader(fh)}
            self.assertIn("9400ZZTESTA", stops)
            self.assertIn("9400ZZTESTB", stops)
            self.assertNotEqual(stops["9400ZZTESTA"]["stop_lat"], "")
            self.assertNotEqual(stops["9400ZZTESTA"]["stop_lon"], "")
            self.assertEqual(stops["9400ZZTESTA"]["parent_station"], "HUBTEST")

            with (gtfs / "stop_times.txt").open(newline="", encoding="utf-8") as fh:
                stop_times = [row for row in csv.DictReader(fh) if row["trip_id"] == "VJ_VJ_TEST_1"]
            self.assertEqual(len(stop_times), 2)
