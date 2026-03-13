from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path

from transit_offline.sources.models import (
    NormalizedAgency,
    NormalizedCalendar,
    NormalizedDataset,
    NormalizedFeedInfo,
    NormalizedPathway,
    NormalizedRoute,
    NormalizedStop,
    NormalizedStopTime,
    NormalizedTrip,
)


TX_NAMESPACE = "http://www.transxchange.org.uk/"
TX_NS = {"tx": TX_NAMESPACE}


@dataclass(frozen=True)
class LondonDatasetBuildResult:
    dataset: NormalizedDataset
    stats: dict[str, int]
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    missing_sources: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _JourneyService:
    service_code: str
    line_name: str
    description: str
    mode: str
    operator_name: str
    route_type: str


@dataclass(frozen=True)
class _JourneyPattern:
    pattern_id: str
    service_code: str
    direction: str
    section_refs: tuple[str, ...]


@dataclass(frozen=True)
class _JourneyTimingLink:
    from_stop_id: str
    to_stop_id: str
    run_time_s: int
    wait_time_s: int


@dataclass(frozen=True)
class _JourneyVehicleJourney:
    trip_code: str
    service_code: str
    pattern_id: str
    departure_s: int
    days_mask: tuple[int, int, int, int, int, int, int]


@dataclass(frozen=True)
class _JourneyParseResult:
    services: dict[str, _JourneyService]
    patterns: dict[str, _JourneyPattern]
    sections: dict[str, list[_JourneyTimingLink]]
    vehicle_journeys: list[_JourneyVehicleJourney]
    stops: dict[str, tuple[float, float, str]]
    stats: dict[str, int]
    warnings: list[str]


def _sanitize_id(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    normalized = normalized.strip("_")
    return normalized or "x"


def _format_gtfs_time(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _trip_start_seconds(route: str, run: str) -> int:
    digest = hashlib.sha1(f"{route}|{run}".encode("utf-8")).digest()
    minute_offset = int.from_bytes(digest[:2], "big") % (16 * 60)
    return 5 * 3600 + minute_offset * 60


def _coerce_int(raw: str, default: int = 0) -> int:
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return default


def _coerce_float(raw: str, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _read_csv_rows_from_zip(zip_path: Path, member_name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member_name) as raw:
            with TextIOWrapper(raw, encoding="utf-8", newline="") as fh:
                return list(csv.DictReader(fh))


def _load_station_rows(raw_london_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str], list[str]]:
    station_gtfs_dir = raw_london_dir / "stationdata" / "gtfs"
    zip_path = raw_london_dir / "stationdata" / "tfl-stationdata-gtfs.zip"
    missing: list[str] = []

    if station_gtfs_dir.exists():
        required = ["stops.txt", "pathways.txt", "feed_info.txt"]
        for name in required:
            if not (station_gtfs_dir / name).exists():
                missing.append(f"stationdata/gtfs/{name}")
        if missing:
            return [], [], {}, missing
        stops = _read_csv_rows(station_gtfs_dir / "stops.txt")
        pathways = _read_csv_rows(station_gtfs_dir / "pathways.txt")
        feed_rows = _read_csv_rows(station_gtfs_dir / "feed_info.txt")
        return stops, pathways, (feed_rows[0] if feed_rows else {}), []

    if not zip_path.exists():
        return [], [], {}, ["stationdata/gtfs/stops.txt", "stationdata/gtfs/pathways.txt", "stationdata/gtfs/feed_info.txt"]

    try:
        stops = _read_csv_rows_from_zip(zip_path, "stops.txt")
        pathways = _read_csv_rows_from_zip(zip_path, "pathways.txt")
        feed_rows = _read_csv_rows_from_zip(zip_path, "feed_info.txt")
    except KeyError as exc:
        return [], [], {}, [f"stationdata/tfl-stationdata-gtfs.zip missing member: {exc.args[0]}"]

    return stops, pathways, (feed_rows[0] if feed_rows else {}), []


def _load_station_platform_parent_lookup(raw_london_dir: Path) -> dict[str, str]:
    detailed_dir = raw_london_dir / "stationdata" / "detailed"
    detailed_zip = raw_london_dir / "stationdata" / "tfl-stationdata-detailed.zip"

    rows: list[dict[str, str]] = []
    if (detailed_dir / "Platforms.csv").exists():
        rows = _read_csv_rows(detailed_dir / "Platforms.csv")
    elif detailed_zip.exists():
        try:
            rows = _read_csv_rows_from_zip(detailed_zip, "Platforms.csv")
        except KeyError:
            rows = []

    lookup: dict[str, str] = {}
    for row in rows:
        naptan = (row.get("PlatformNaptanCode") or "").strip()
        station = (row.get("StationUniqueId") or "").strip()
        if not naptan or not station:
            continue
        lookup[naptan] = station
    return lookup


def _upsert_stop(
    dataset: NormalizedDataset,
    stop_index_by_id: dict[str, int],
    stop: NormalizedStop,
) -> bool:
    """
    Insert a stop unless already present.

    Returns True only when a new stop row is inserted. If the stop exists and
    the new record contains a missing parent_station value, the existing row is
    updated in place.
    """
    existing_idx = stop_index_by_id.get(stop.stop_id)
    if existing_idx is None:
        stop_index_by_id[stop.stop_id] = len(dataset.stops)
        dataset.stops.append(stop)
        return True

    existing = dataset.stops[existing_idx]
    if not existing.parent_station and stop.parent_station:
        dataset.stops[existing_idx] = NormalizedStop(
            stop_id=existing.stop_id,
            stop_name=existing.stop_name,
            stop_lat=existing.stop_lat,
            stop_lon=existing.stop_lon,
            location_type=existing.location_type,
            parent_station=stop.parent_station,
        )
    return False


def _load_bus_stop_lookup(stop_points_json: Path) -> dict[str, tuple[float, float, str]]:
    data = json.loads(stop_points_json.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        points = data.get("stopPoints", [])
    elif isinstance(data, list):
        points = data
    else:
        points = []

    lookup: dict[str, tuple[float, float, str]] = {}
    for row in points:
        if not isinstance(row, dict):
            continue
        stop_id = (row.get("naptanId") or "").strip()
        if not stop_id:
            continue
        lat = row.get("lat")
        lon = row.get("lon")
        if lat is None or lon is None:
            continue
        lookup[stop_id] = (float(lat), float(lon), (row.get("commonName") or "").strip())
    return lookup


def _feed_dates(feed_info_row: dict[str, str]) -> tuple[str, str]:
    start = (feed_info_row.get("feed_start_date") or "").strip()
    if len(start) == 8 and start.isdigit():
        return start, f"{start[:4]}1231"
    return "20260101", "20261231"


def _parse_iso_duration_seconds(raw: str) -> int:
    value = (raw or "").strip()
    if not value:
        return 0
    # TransXChange uses ISO-8601 durations such as PT2M or PT7M30S.
    pattern = r"^P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$"
    match = re.match(pattern, value)
    if match is None:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _parse_hms_seconds(raw: str) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 3:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
    except ValueError:
        return None
    if minutes < 0 or minutes > 59 or seconds < 0 or seconds > 59:
        return None
    if hours < 0:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _tx_text(parent: ET.Element, path: str) -> str:
    node = parent.find(path, TX_NS)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _extract_days_mask(days_of_week: ET.Element | None) -> tuple[int, int, int, int, int, int, int] | None:
    if days_of_week is None:
        return None
    child_tags = []
    for child in list(days_of_week):
        local_name = child.tag.split("}", 1)[-1]
        child_tags.append(local_name)
    if not child_tags:
        return None

    explicit = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }
    mask = [0, 0, 0, 0, 0, 0, 0]
    for tag in child_tags:
        if tag == "MondayToSunday":
            return (1, 1, 1, 1, 1, 1, 1)
        if tag == "MondayToSaturday":
            return (1, 1, 1, 1, 1, 1, 0)
        if tag == "MondayToFriday":
            return (1, 1, 1, 1, 1, 0, 0)
        if tag == "Weekend":
            return (0, 0, 0, 0, 0, 1, 1)
        if tag == "SaturdayOrSunday":
            return (0, 0, 0, 0, 0, 1, 1)
        if tag in explicit:
            mask[explicit[tag]] = 1
    return tuple(mask)


def _days_mask_to_service_id(mask: tuple[int, int, int, int, int, int, int]) -> str:
    if mask == (1, 1, 1, 1, 1, 0, 0):
        return "WD"
    return f"DY_{''.join(str(bit) for bit in mask)}"


def _infer_route_type(
    mode: str,
    line_name: str,
    description: str,
    service_code: str,
    operator_name: str,
) -> str:
    mode_l = (mode or "").strip().lower()
    text = f"{line_name} {description} {service_code} {operator_name}".lower()

    if mode_l == "tram":
        return "0"
    if mode_l == "underground":
        return "1"
    if mode_l == "ferry":
        return "4"
    if "cable car" in text or "-cab-" in text or "ifs cloud" in text or "emirates air line" in text:
        return "6"
    if mode_l == "rail":
        return "2"
    if mode_l == "bus":
        return "3"
    return "2"


def _is_supported_route_type(route_type: str) -> bool:
    return route_type in {"0", "1", "2", "3", "4", "6", "7"}


def _iter_journey_xml_files(journey_dir: Path) -> list[Path]:
    unpacked_dir = journey_dir / "live_unpacked"
    if not unpacked_dir.exists():
        return []

    all_xml = sorted(unpacked_dir.rglob("*.xml"))
    selected: list[Path] = []
    for path in all_xml:
        parts_upper = [part.upper() for part in path.parts]
        if any("REPLACEMENT_BUSES" in part for part in parts_upper):
            continue
        bus_dir = next((part for part in parts_upper if part.startswith("BUSES_PART_")), "")
        if bus_dir:
            selected.append(path)
            continue
        selected.append(path)
    return selected


def _east_north_to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """
    Convert British National Grid coordinates (OSGB36 / EPSG:27700) to WGS84.

    The implementation follows the Ordnance Survey algorithm plus Helmert
    transform to WGS84, with no external dependency.
    """

    # Airy 1830 (OSGB36) ellipsoid.
    a = 6377563.396
    b = 6356256.909
    f0 = 0.9996012717
    lat0 = math.radians(49.0)
    lon0 = math.radians(-2.0)
    n0 = -100000.0
    e0 = 400000.0
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    lat = lat0
    m = 0.0
    while northing - n0 - m >= 1e-5:
        lat = (northing - n0 - m) / (a * f0) + lat
        ma = (1 + n + (5.0 / 4.0) * n * n + (5.0 / 4.0) * n**3) * (lat - lat0)
        mb = (3 * n + 3 * n * n + (21.0 / 8.0) * n**3) * math.sin(lat - lat0) * math.cos(lat + lat0)
        mc = ((15.0 / 8.0) * n * n + (15.0 / 8.0) * n**3) * math.sin(2 * (lat - lat0)) * math.cos(
            2 * (lat + lat0)
        )
        md = (35.0 / 24.0) * n**3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0))
        m = b * f0 * (ma - mb + mc - md)

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    nu = a * f0 / math.sqrt(1 - e2 * sin_lat * sin_lat)
    rho = a * f0 * (1 - e2) / (1 - e2 * sin_lat * sin_lat) ** 1.5
    eta2 = nu / rho - 1
    d_e = easting - e0

    vii = math.tan(lat) / (2 * rho * nu)
    viii = math.tan(lat) / (24 * rho * nu**3) * (5 + 3 * math.tan(lat) ** 2 + eta2 - 9 * math.tan(lat) ** 2 * eta2)
    ix = math.tan(lat) / (720 * rho * nu**5) * (61 + 90 * math.tan(lat) ** 2 + 45 * math.tan(lat) ** 4)
    x = 1 / (nu * cos_lat)
    xi = 1 / (6 * nu**3 * cos_lat) * (nu / rho + 2 * math.tan(lat) ** 2)
    xii = 1 / (120 * nu**5 * cos_lat) * (5 + 28 * math.tan(lat) ** 2 + 24 * math.tan(lat) ** 4)
    xiia = 1 / (5040 * nu**7 * cos_lat) * (
        61 + 662 * math.tan(lat) ** 2 + 1320 * math.tan(lat) ** 4 + 720 * math.tan(lat) ** 6
    )

    lat_osgb = lat - vii * d_e**2 + viii * d_e**4 - ix * d_e**6
    lon_osgb = lon0 + x * d_e - xi * d_e**3 + xii * d_e**5 - xiia * d_e**7

    # Convert to cartesian (OSGB36).
    h = 0.0
    sin_lat = math.sin(lat_osgb)
    cos_lat = math.cos(lat_osgb)
    sin_lon = math.sin(lon_osgb)
    cos_lon = math.cos(lon_osgb)
    v = a / math.sqrt(1 - e2 * sin_lat * sin_lat)
    x1 = (v + h) * cos_lat * cos_lon
    y1 = (v + h) * cos_lat * sin_lon
    z1 = ((1 - e2) * v + h) * sin_lat

    # Helmert transform OSGB36 -> WGS84.
    tx = 446.448
    ty = -125.157
    tz = 542.060
    s = 20.4894 * 1e-6
    rx = math.radians(0.1502 / 3600.0)
    ry = math.radians(0.2470 / 3600.0)
    rz = math.radians(0.8421 / 3600.0)

    x2 = tx + (1 + s) * x1 - rz * y1 + ry * z1
    y2 = ty + rz * x1 + (1 + s) * y1 - rx * z1
    z2 = tz - ry * x1 + rx * y1 + (1 + s) * z1

    # WGS84 ellipsoid.
    a2 = 6378137.0
    b2 = 6356752.3141
    e2_2 = 1 - (b2 * b2) / (a2 * a2)

    p = math.sqrt(x2 * x2 + y2 * y2)
    lat_wgs = math.atan2(z2, p * (1 - e2_2))
    for _ in range(12):
        v2 = a2 / math.sqrt(1 - e2_2 * math.sin(lat_wgs) ** 2)
        next_lat = math.atan2(z2 + e2_2 * v2 * math.sin(lat_wgs), p)
        if abs(next_lat - lat_wgs) < 1e-12:
            lat_wgs = next_lat
            break
        lat_wgs = next_lat
    lon_wgs = math.atan2(y2, x2)

    return math.degrees(lat_wgs), math.degrees(lon_wgs)


def _parse_journey_data(raw_london_dir: Path) -> _JourneyParseResult:
    journey_dir = raw_london_dir / "journey"
    xml_files = _iter_journey_xml_files(journey_dir)
    if not xml_files:
        return _JourneyParseResult(
            services={},
            patterns={},
            sections={},
            vehicle_journeys=[],
            stops={},
            stats={
                "journey_xml_files_selected": 0,
                "journey_xml_files_selected_bus": 0,
                "journey_xml_files_selected_non_bus": 0,
                "journey_services": 0,
                "journey_patterns": 0,
                "journey_sections": 0,
                "journey_vehicle_journeys": 0,
                "journey_stops": 0,
            },
            warnings=[],
        )

    stops: dict[str, tuple[float, float, str]] = {}
    services: dict[str, _JourneyService] = {}
    patterns: dict[str, _JourneyPattern] = {}
    sections: dict[str, list[_JourneyTimingLink]] = {}
    service_days_defaults: dict[str, tuple[int, int, int, int, int, int, int]] = {}
    vehicle_journeys: list[_JourneyVehicleJourney] = []
    seen_trip_codes: set[str] = set()
    warnings: list[str] = []

    for xml_path in xml_files:
        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as exc:
            warnings.append(f"Journey XML parse error in '{xml_path.name}': {exc}.")
            continue

        operators: dict[str, str] = {}
        for operator in root.findall("./tx:Operators/tx:Operator", TX_NS):
            operator_id = (operator.get("id") or "").strip()
            if not operator_id:
                continue
            operators[operator_id] = (
                _tx_text(operator, "tx:OperatorShortName")
                or _tx_text(operator, "tx:TradingName")
                or _tx_text(operator, "tx:OperatorCode")
            )

        for stop_point in root.findall("./tx:StopPoints/tx:StopPoint", TX_NS):
            stop_id = _tx_text(stop_point, "tx:AtcoCode")
            if not stop_id:
                continue
            name = _tx_text(stop_point, "tx:Descriptor/tx:CommonName") or stop_id
            east_raw = _tx_text(stop_point, "tx:Place/tx:Location/tx:Easting")
            north_raw = _tx_text(stop_point, "tx:Place/tx:Location/tx:Northing")
            if not east_raw or not north_raw:
                continue
            try:
                lat, lon = _east_north_to_wgs84(float(east_raw), float(north_raw))
            except ValueError:
                continue
            stops[stop_id] = (lat, lon, name)

        for service in root.findall("./tx:Services/tx:Service", TX_NS):
            service_code = _tx_text(service, "tx:ServiceCode")
            if not service_code:
                continue

            line_name = _tx_text(service, "tx:Lines/tx:Line/tx:LineName")
            description = _tx_text(service, "tx:Description")
            mode = _tx_text(service, "tx:Mode").lower()
            operator_ref = _tx_text(service, "tx:RegisteredOperatorRef")
            operator_name = operators.get(operator_ref, "")
            route_type = _infer_route_type(mode, line_name, description, service_code, operator_name)

            service_days = _extract_days_mask(
                service.find("./tx:OperatingProfile/tx:RegularDayType/tx:DaysOfWeek", TX_NS)
            )
            if service_days is not None:
                service_days_defaults[service_code] = service_days

            if not _is_supported_route_type(route_type):
                continue

            if service_code not in services:
                services[service_code] = _JourneyService(
                    service_code=service_code,
                    line_name=line_name or service_code,
                    description=description or line_name or service_code,
                    mode=mode,
                    operator_name=operator_name,
                    route_type=route_type,
                )

            for pattern in service.findall("./tx:StandardService/tx:JourneyPattern", TX_NS):
                pattern_id = (pattern.get("id") or "").strip()
                if not pattern_id:
                    continue
                refs_raw = _tx_text(pattern, "tx:JourneyPatternSectionRefs")
                if not refs_raw:
                    continue
                refs = tuple(ref for ref in refs_raw.split() if ref)
                if not refs:
                    continue
                direction = _tx_text(pattern, "tx:Direction").lower()
                patterns[pattern_id] = _JourneyPattern(
                    pattern_id=pattern_id,
                    service_code=service_code,
                    direction=direction,
                    section_refs=refs,
                )

        for section in root.findall("./tx:JourneyPatternSections/tx:JourneyPatternSection", TX_NS):
            section_id = (section.get("id") or "").strip()
            if not section_id:
                continue
            links: list[_JourneyTimingLink] = []
            for link in section.findall("./tx:JourneyPatternTimingLink", TX_NS):
                from_stop_id = _tx_text(link, "tx:From/tx:StopPointRef")
                to_stop_id = _tx_text(link, "tx:To/tx:StopPointRef")
                if not from_stop_id or not to_stop_id:
                    continue
                run_time_s = _parse_iso_duration_seconds(_tx_text(link, "tx:RunTime"))
                wait_time_s = _parse_iso_duration_seconds(_tx_text(link, "tx:To/tx:WaitTime"))
                links.append(
                    _JourneyTimingLink(
                        from_stop_id=from_stop_id,
                        to_stop_id=to_stop_id,
                        run_time_s=run_time_s,
                        wait_time_s=wait_time_s,
                    )
                )
            if links:
                sections[section_id] = links

        for vehicle_journey in root.findall("./tx:VehicleJourneys/tx:VehicleJourney", TX_NS):
            service_code = _tx_text(vehicle_journey, "tx:ServiceRef")
            if not service_code or service_code not in services:
                continue

            pattern_id = _tx_text(vehicle_journey, "tx:JourneyPatternRef")
            if not pattern_id or pattern_id not in patterns:
                continue

            departure_s = _parse_hms_seconds(_tx_text(vehicle_journey, "tx:DepartureTime"))
            if departure_s is None:
                continue

            trip_code = _tx_text(vehicle_journey, "tx:VehicleJourneyCode")
            if not trip_code:
                trip_code = f"VJ_{service_code}_{pattern_id}_{departure_s}"
            if trip_code in seen_trip_codes:
                trip_code = f"{trip_code}_{xml_path.stem}"
            seen_trip_codes.add(trip_code)

            days_mask = _extract_days_mask(
                vehicle_journey.find("./tx:OperatingProfile/tx:RegularDayType/tx:DaysOfWeek", TX_NS)
            )
            if days_mask is None:
                days_mask = service_days_defaults.get(service_code, (1, 1, 1, 1, 1, 1, 1))

            vehicle_journeys.append(
                _JourneyVehicleJourney(
                    trip_code=trip_code,
                    service_code=service_code,
                    pattern_id=pattern_id,
                    departure_s=departure_s,
                    days_mask=days_mask,
                )
            )

    selected_bus_files = 0
    for path in xml_files:
        parts_upper = [part.upper() for part in path.parts]
        if any(part.startswith("BUSES_PART_") for part in parts_upper):
            selected_bus_files += 1

    stats = {
        "journey_xml_files_selected": len(xml_files),
        "journey_xml_files_selected_bus": selected_bus_files,
        "journey_xml_files_selected_non_bus": len(xml_files) - selected_bus_files,
        "journey_services": len(services),
        "journey_patterns": len(patterns),
        "journey_sections": len(sections),
        "journey_vehicle_journeys": len(vehicle_journeys),
        "journey_stops": len(stops),
    }
    return _JourneyParseResult(
        services=services,
        patterns=patterns,
        sections=sections,
        vehicle_journeys=vehicle_journeys,
        stops=stops,
        stats=stats,
        warnings=warnings,
    )


def _compose_pattern_stops(
    pattern: _JourneyPattern,
    sections: dict[str, list[_JourneyTimingLink]],
) -> tuple[list[str], list[int]]:
    stop_ids: list[str] = []
    deltas: list[int] = []

    for section_ref in pattern.section_refs:
        links = sections.get(section_ref)
        if not links:
            continue
        for link in links:
            edge_seconds = max(0, link.run_time_s + link.wait_time_s)
            if not stop_ids:
                stop_ids = [link.from_stop_id, link.to_stop_id]
                deltas = [edge_seconds]
                continue
            if stop_ids[-1] != link.from_stop_id:
                stop_ids.append(link.from_stop_id)
                deltas.append(0)
            stop_ids.append(link.to_stop_id)
            deltas.append(edge_seconds)

    if len(stop_ids) < 2:
        return [], []

    dedup_stops = [stop_ids[0]]
    dedup_deltas: list[int] = []
    for idx in range(1, len(stop_ids)):
        stop_id = stop_ids[idx]
        delta = deltas[idx - 1] if idx - 1 < len(deltas) else 0
        if stop_id == dedup_stops[-1]:
            if dedup_deltas:
                dedup_deltas[-1] += delta
            continue
        dedup_stops.append(stop_id)
        dedup_deltas.append(delta)

    if len(dedup_stops) < 2:
        return [], []
    return dedup_stops, dedup_deltas


def _add_calendar_if_missing(
    dataset: NormalizedDataset,
    existing_ids: set[str],
    service_id: str,
    days_mask: tuple[int, int, int, int, int, int, int],
    start_date: str,
    end_date: str,
) -> None:
    if service_id in existing_ids:
        return
    dataset.calendars.append(
        NormalizedCalendar(
            service_id=service_id,
            monday=days_mask[0],
            tuesday=days_mask[1],
            wednesday=days_mask[2],
            thursday=days_mask[3],
            friday=days_mask[4],
            saturday=days_mask[5],
            sunday=days_mask[6],
            start_date=start_date,
            end_date=end_date,
        )
    )
    existing_ids.add(service_id)


def build_london_dataset(raw_london_dir: Path) -> LondonDatasetBuildResult:
    bus_stops_path = raw_london_dir / "bus" / "bus-stops-live.csv"
    bus_sequences_path = raw_london_dir / "bus" / "bus-sequences-live.csv"
    bus_stop_points_path = raw_london_dir / "bus" / "stoppoint-mode-bus-all.json"
    journey_live_path = raw_london_dir / "journey" / "journey-planner-timetables-live.zip"

    missing_sources: list[str] = []
    for rel, path in [
        ("bus/bus-stops-live.csv", bus_stops_path),
        ("bus/bus-sequences-live.csv", bus_sequences_path),
        ("bus/stoppoint-mode-bus-all.json", bus_stop_points_path),
    ]:
        if not path.exists():
            missing_sources.append(rel)

    station_stops_rows, station_pathways_rows, station_feed_info, station_missing = _load_station_rows(raw_london_dir)
    missing_sources.extend(station_missing)
    if missing_sources:
        return LondonDatasetBuildResult(
            dataset=NormalizedDataset(),
            stats={},
            missing_sources=sorted(set(missing_sources)),
            warnings=["Missing required London raw sources for conversion."],
        )

    station_platform_parent_lookup = _load_station_platform_parent_lookup(raw_london_dir)
    bus_stop_lookup = _load_bus_stop_lookup(bus_stop_points_path)
    bus_stops_rows = _read_csv_rows(bus_stops_path)
    bus_sequences_rows = _read_csv_rows(bus_sequences_path)
    journey = _parse_journey_data(raw_london_dir)

    feed_name = (station_feed_info.get("feed_publisher_name") or "").strip() or "Transport for London"
    feed_url = (station_feed_info.get("feed_publisher_url") or "").strip() or "https://tfl.gov.uk"
    feed_lang = (station_feed_info.get("feed_lang") or "").strip() or "en"
    start_date, end_date = _feed_dates(station_feed_info)

    dataset = NormalizedDataset()
    dataset.agencies.append(
        NormalizedAgency(
            agency_id="TFL",
            agency_name=feed_name,
            agency_url=feed_url,
            agency_timezone="Europe/London",
        )
    )
    dataset.calendars.append(
        NormalizedCalendar(
            service_id="WD",
            monday=1,
            tuesday=1,
            wednesday=1,
            thursday=1,
            friday=1,
            saturday=0,
            sunday=0,
            start_date=start_date,
            end_date=end_date,
        )
    )
    dataset.feed_info.append(
        NormalizedFeedInfo(
            feed_publisher_name=feed_name,
            feed_publisher_url=feed_url,
            feed_lang=feed_lang,
            feed_start_date=start_date,
            feed_end_date=end_date,
            feed_version="london-source-v1",
        )
    )

    seen_stop_ids: set[str] = set()
    stop_index_by_id: dict[str, int] = {}
    station_stops_kept = 0
    for row in station_stops_rows:
        stop_id = (row.get("stop_id") or "").strip()
        if not stop_id:
            continue
        lat_raw = (row.get("stop_lat") or "").strip()
        lon_raw = (row.get("stop_lon") or "").strip()
        if not lat_raw or not lon_raw:
            continue
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except ValueError:
            continue
        parent_station = (row.get("parent_station") or "").strip() or station_platform_parent_lookup.get(stop_id, "")
        inserted = _upsert_stop(
            dataset,
            stop_index_by_id,
            NormalizedStop(
                stop_id=stop_id,
                stop_name=(row.get("stop_name") or "").strip() or stop_id,
                stop_lat=lat,
                stop_lon=lon,
                location_type=(row.get("location_type") or "").strip() or "0",
                parent_station=parent_station,
            ),
        )
        if inserted:
            station_stops_kept += 1
        seen_stop_ids.add(stop_id)

    bus_stops_kept = 0
    bus_stops_missing_coords = 0
    for row in bus_stops_rows:
        stop_id = (row.get("Naptan_Atco") or "").strip()
        if not stop_id or stop_id in seen_stop_ids:
            continue
        lookup = bus_stop_lookup.get(stop_id)
        if lookup is None:
            bus_stops_missing_coords += 1
            continue
        lat, lon, fallback_name = lookup
        name = (row.get("Stop_Name") or "").strip() or fallback_name or stop_id
        inserted = _upsert_stop(
            dataset,
            stop_index_by_id,
            NormalizedStop(
                stop_id=stop_id,
                stop_name=name,
                stop_lat=lat,
                stop_lon=lon,
                location_type="0",
                parent_station="",
            ),
        )
        seen_stop_ids.add(stop_id)
        if inserted:
            bus_stops_kept += 1

    route_seen: set[str] = set()
    calendar_service_ids: set[str] = {"WD"}
    journey_bus_line_names = {
        service.line_name.strip()
        for service in journey.services.values()
        if service.route_type == "3" and service.line_name.strip()
    }
    synthetic_bus_routes_skipped_due_journey = 0
    trip_entries: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for row in bus_sequences_rows:
        route = (row.get("Route") or "").strip()
        run = (row.get("Run") or "").strip()
        stop_id = (row.get("Naptan_Atco") or "").strip()
        if not route or not run or not stop_id:
            continue
        if stop_id not in seen_stop_ids:
            lookup = bus_stop_lookup.get(stop_id)
            if lookup is None:
                continue
            lat, lon, fallback_name = lookup
            inserted = _upsert_stop(
                dataset,
                stop_index_by_id,
                NormalizedStop(
                    stop_id=stop_id,
                    stop_name=fallback_name or stop_id,
                    stop_lat=lat,
                    stop_lon=lon,
                    location_type="0",
                    parent_station="",
                ),
            )
            if inserted:
                bus_stops_kept += 1
            seen_stop_ids.add(stop_id)

        seq = _coerce_int((row.get("Sequence") or "").strip(), default=0)
        trip_entries.setdefault((route, run), []).append((seq, stop_id))

    for route, run in sorted(trip_entries):
        if route in journey_bus_line_names:
            synthetic_bus_routes_skipped_due_journey += 1
            continue
        ordered = sorted(trip_entries[(route, run)], key=lambda item: (item[0], item[1]))
        stop_ids = [stop_id for _, stop_id in ordered]
        deduped: list[str] = []
        for stop_id in stop_ids:
            if not deduped or deduped[-1] != stop_id:
                deduped.append(stop_id)
        if len(deduped) < 2:
            continue

        route_id = f"BUS_{_sanitize_id(route)}"
        if route_id not in route_seen:
            dataset.routes.append(
                NormalizedRoute(
                    route_id=route_id,
                    agency_id="TFL",
                    route_short_name=route,
                    route_long_name=f"Bus route {route}",
                    route_type="3",
                )
            )
            route_seen.add(route_id)

        trip_id = f"{route_id}_{_sanitize_id(run)}"
        dataset.trips.append(
            NormalizedTrip(
                route_id=route_id,
                service_id="WD",
                trip_id=trip_id,
                direction_id="0",
            )
        )

        start_s = _trip_start_seconds(route, run)
        for idx, stop_id in enumerate(deduped):
            t = start_s + idx * 120
            gtfs_time = _format_gtfs_time(t)
            dataset.stop_times.append(
                NormalizedStopTime(
                    trip_id=trip_id,
                    arrival_time=gtfs_time,
                    departure_time=gtfs_time,
                    stop_id=stop_id,
                    stop_sequence=idx + 1,
                )
            )

    for idx, row in enumerate(station_pathways_rows, start=1):
        dataset.pathways.append(
            NormalizedPathway(
                pathway_id=(row.get("pathway_id") or "").strip() or f"pth_{idx}",
                from_stop_id=(row.get("from_stop_id") or "").strip(),
                to_stop_id=(row.get("to_stop_id") or "").strip(),
                pathway_mode=_coerce_int((row.get("pathway_mode") or "").strip(), default=1),
                is_bidirectional=_coerce_int((row.get("is_bidirectional") or "").strip(), default=0),
                length=_coerce_float((row.get("length") or "").strip(), default=0.0),
                traversal_time=_coerce_int((row.get("traversal_time") or "").strip(), default=0),
                )
            )

    journey_stops_added = 0
    for stop_id, (lat, lon, name) in sorted(journey.stops.items()):
        parent_station = station_platform_parent_lookup.get(stop_id, "")
        inserted = _upsert_stop(
            dataset,
            stop_index_by_id,
            NormalizedStop(
                stop_id=stop_id,
                stop_name=name or stop_id,
                stop_lat=lat,
                stop_lon=lon,
                location_type="0",
                parent_station=parent_station,
            ),
        )
        seen_stop_ids.add(stop_id)
        if inserted:
            journey_stops_added += 1

    journey_routes_built = 0
    journey_trips_built = 0
    journey_stop_times_built = 0
    journey_trips_missing_pattern = 0
    journey_trips_missing_stops = 0
    used_trip_ids: set[str] = {trip.trip_id for trip in dataset.trips}

    for vehicle_journey in journey.vehicle_journeys:
        pattern = journey.patterns.get(vehicle_journey.pattern_id)
        if pattern is None:
            journey_trips_missing_pattern += 1
            continue
        service = journey.services.get(vehicle_journey.service_code)
        if service is None:
            journey_trips_missing_pattern += 1
            continue

        stop_ids, deltas = _compose_pattern_stops(pattern, journey.sections)
        if len(stop_ids) < 2:
            journey_trips_missing_pattern += 1
            continue

        unresolved_stops = [stop_id for stop_id in stop_ids if stop_id not in seen_stop_ids]
        if unresolved_stops:
            journey_trips_missing_stops += 1
            continue

        route_id = f"TXC_{_sanitize_id(service.service_code)}"
        if route_id not in route_seen:
            short_name = service.line_name.strip() or service.service_code
            dataset.routes.append(
                NormalizedRoute(
                    route_id=route_id,
                    agency_id="TFL",
                    route_short_name=short_name,
                    route_long_name=service.description or short_name,
                    route_type=service.route_type,
                )
            )
            route_seen.add(route_id)
            journey_routes_built += 1

        trip_id = f"VJ_{_sanitize_id(vehicle_journey.trip_code)}"
        if trip_id in used_trip_ids:
            trip_id = f"{trip_id}_{_sanitize_id(service.service_code)}"
        used_trip_ids.add(trip_id)
        direction_id = "1" if pattern.direction == "outbound" else "0"
        service_id = _days_mask_to_service_id(vehicle_journey.days_mask)
        _add_calendar_if_missing(
            dataset=dataset,
            existing_ids=calendar_service_ids,
            service_id=service_id,
            days_mask=vehicle_journey.days_mask,
            start_date=start_date,
            end_date=end_date,
        )

        dataset.trips.append(
            NormalizedTrip(
                route_id=route_id,
                service_id=service_id,
                trip_id=trip_id,
                direction_id=direction_id,
            )
        )
        journey_trips_built += 1

        current_s = vehicle_journey.departure_s
        first_time = _format_gtfs_time(current_s)
        dataset.stop_times.append(
            NormalizedStopTime(
                trip_id=trip_id,
                arrival_time=first_time,
                departure_time=first_time,
                stop_id=stop_ids[0],
                stop_sequence=1,
            )
        )
        journey_stop_times_built += 1

        for idx in range(1, len(stop_ids)):
            current_s += deltas[idx - 1]
            stamp = _format_gtfs_time(current_s)
            dataset.stop_times.append(
                NormalizedStopTime(
                    trip_id=trip_id,
                    arrival_time=stamp,
                    departure_time=stamp,
                    stop_id=stop_ids[idx],
                    stop_sequence=idx + 1,
                )
            )
            journey_stop_times_built += 1

    notes: list[str] = []
    if journey_live_path.exists():
        notes.append("Journey timetable archive is present.")
    else:
        notes.append("Journey timetable archive not found; generated schedule is bus-sequence based.")
    if journey.stats["journey_xml_files_selected"] == 0:
        notes.append("No journey XML files detected under journey/live_unpacked.")
    else:
        notes.append(
            f"Parsed {journey.stats['journey_xml_files_selected']} journey XML files "
            f"({journey.stats.get('journey_xml_files_selected_non_bus', 0)} non-bus, "
            f"{journey.stats.get('journey_xml_files_selected_bus', 0)} bus) "
            f"and built {journey_trips_built} timetable trips."
        )
        if journey.stats.get("journey_xml_files_selected_bus", 0) > 0:
            notes.append(
                "Bus XML ingestion includes all BUSES_PART_* feeds; REPLACEMENT_BUSES is intentionally excluded."
            )

    stats = {
        "station_stops_rows": len(station_stops_rows),
        "station_stops_kept": station_stops_kept,
        "station_pathways_rows": len(station_pathways_rows),
        "bus_stops_rows": len(bus_stops_rows),
        "bus_stops_kept": bus_stops_kept,
        "bus_stops_missing_coords": bus_stops_missing_coords,
        "bus_sequence_rows": len(bus_sequences_rows),
        "journey_stops_added": journey_stops_added,
        "journey_platform_parent_links": len(station_platform_parent_lookup),
        "journey_routes_built": journey_routes_built,
        "journey_trips_built": journey_trips_built,
        "journey_stop_times_built": journey_stop_times_built,
        "journey_trips_missing_pattern": journey_trips_missing_pattern,
        "journey_trips_missing_stops": journey_trips_missing_stops,
        "synthetic_bus_routes_skipped_due_journey": synthetic_bus_routes_skipped_due_journey,
        "routes_built_total": len(dataset.routes),
        "trips_built_total": len(dataset.trips),
        "stop_times_built_total": len(dataset.stop_times),
        "stops_total": len(dataset.stops),
        "pathways_total": len(dataset.pathways),
    }
    stats.update(journey.stats)

    warnings: list[str] = []
    if bus_stops_missing_coords > 0:
        warnings.append(
            f"{bus_stops_missing_coords} bus stops were dropped due to missing lat/lon lookup."
        )
    if len(dataset.trips) == 0:
        warnings.append("No trips were built from available London inputs.")
    if journey_trips_missing_pattern > 0:
        warnings.append(
            f"{journey_trips_missing_pattern} non-bus journeys were skipped due to missing "
            "pattern/section mapping."
        )
    if journey_trips_missing_stops > 0:
        warnings.append(
            f"{journey_trips_missing_stops} non-bus journeys were skipped due to unresolved stop coordinates."
        )
    warnings.extend(journey.warnings)

    return LondonDatasetBuildResult(
        dataset=dataset,
        stats=stats,
        warnings=warnings,
        notes=notes,
    )
