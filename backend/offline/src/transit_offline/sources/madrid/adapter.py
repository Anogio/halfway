from __future__ import annotations

import csv
import io
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

from transit_offline.common.config import AppConfig
from transit_offline.sources.base import PrepareReport, SourceAdapter
from transit_offline.sources.validators import find_missing_required_gtfs_files

STANDARD_HEADERS: dict[str, list[str]] = {
    "agency.txt": ["agency_id", "agency_name", "agency_url", "agency_timezone"],
    "calendar.txt": [
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
    "calendar_dates.txt": ["service_id", "date", "exception_type"],
    "feed_info.txt": [
        "feed_publisher_name",
        "feed_publisher_url",
        "feed_lang",
        "feed_start_date",
        "feed_end_date",
        "feed_version",
    ],
    "pathways.txt": [
        "pathway_id",
        "from_stop_id",
        "to_stop_id",
        "pathway_mode",
        "is_bidirectional",
        "length",
        "traversal_time",
    ],
    "routes.txt": ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
    "stop_times.txt": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
    "stops.txt": ["stop_id", "stop_name", "stop_lat", "stop_lon", "location_type", "parent_station"],
    "transfers.txt": ["from_stop_id", "to_stop_id", "transfer_type", "min_transfer_time"],
    "trips.txt": ["route_id", "service_id", "trip_id", "direction_id"],
}


@dataclass(frozen=True)
class SourceSpec:
    key: str
    label: str
    keywords: tuple[str, ...]
    required: bool = True


@dataclass(frozen=True)
class FeedSource:
    spec: SourceSpec
    path: Path


@dataclass(frozen=True)
class SourceContext:
    default_agency_id: str
    feed_info: dict[str, str]


SOURCE_SPECS = (
    SourceSpec("metro_ligero", "Metro Ligero", ("google_transit_m10", "m10", "metro_ligero", "metroligero")),
    SourceSpec("metro", "Metro", ("google_transit_m4", "m4", "metro")),
    SourceSpec("emt", "EMT", ("google_transit_m6", "m6", "emt")),
    SourceSpec("urban_bus", "Urban buses", ("google_transit_m9", "m9", "urban_bus", "urbanos")),
    SourceSpec("interurban_bus", "Interurban buses", ("google_transit_m89", "m89", "interurban_bus", "interurbanos")),
    SourceSpec("cercanias", "Cercanias", ("google_transit_m5", "m5", "cercanias"), required=False),
)


def _normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.lower().replace("-", "_").replace(" ", "_")


def _prefixed(source: FeedSource, value: str) -> str:
    token = value.strip()
    if not token:
        return ""
    return f"{source.spec.key}__{token}"


def _find_zip_member(zf: zipfile.ZipFile, filename: str) -> str | None:
    wanted = filename.lower()
    for name in zf.namelist():
        if Path(name).name.lower() == wanted:
            return name
    return None


def _iter_rows(source: FeedSource, filename: str):
    if source.path.is_dir():
        path = source.path / filename
        if not path.exists():
            return
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                yield {str(key): (value or "") for key, value in row.items()}
        return

    with zipfile.ZipFile(source.path) as zf:
        member = _find_zip_member(zf, filename)
        if member is None:
            return
        with zf.open(member) as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    yield {str(key): (value or "") for key, value in row.items()}


def _read_first_row(source: FeedSource, filename: str) -> dict[str, str]:
    for row in _iter_rows(source, filename):
        return row
    return {}


def _discover_sources(raw_dir: Path) -> tuple[list[FeedSource], list[str], list[str]]:
    discovered: dict[str, FeedSource] = {}
    issues: list[str] = []
    warnings: list[str] = []

    if not raw_dir.exists():
        missing = [spec.label for spec in SOURCE_SPECS if spec.required]
        return [], missing, warnings

    for path in sorted(raw_dir.iterdir()):
        if path.name.startswith("."):
            continue
        if not path.is_dir() and path.suffix.lower() != ".zip":
            continue

        normalized_name = _normalize_name(path.stem if path.is_file() else path.name)
        matches = [spec for spec in SOURCE_SPECS if any(keyword in normalized_name for keyword in spec.keywords)]
        if not matches:
            warnings.append(f"Ignoring unrecognized Madrid source '{path.name}'.")
            continue

        spec = matches[0]
        if spec.key in discovered:
            issues.append(f"Duplicate Madrid source for {spec.label}: {discovered[spec.key].path.name}, {path.name}")
            continue
        discovered[spec.key] = FeedSource(spec=spec, path=path)

    missing = [spec.label for spec in SOURCE_SPECS if spec.required and spec.key not in discovered]
    if "cercanias" not in discovered:
        warnings.append("Cercanias is currently excluded because the public GTFS archive is upstream-broken.")

    ordered = [discovered[spec.key] for spec in SOURCE_SPECS if spec.key in discovered]
    return ordered, issues + missing, warnings


def _build_source_contexts(sources: list[FeedSource]) -> dict[str, SourceContext]:
    contexts: dict[str, SourceContext] = {}
    for source in sources:
        agency = _read_first_row(source, "agency.txt")
        agency_id = agency.get("agency_id", "").strip() or source.spec.key
        contexts[source.spec.key] = SourceContext(
            default_agency_id=_prefixed(source, agency_id),
            feed_info=_read_first_row(source, "feed_info.txt"),
        )
    return contexts


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _merge_table(
    *,
    out_path: Path,
    fieldnames: list[str],
    sources: list[FeedSource],
    row_builder,
) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for source in sources:
            for row in row_builder(source):
                writer.writerow(row)
                rows_written += 1
    return rows_written


def _valid_date(value: str) -> str:
    token = value.strip()
    return token if len(token) == 8 and token.isdigit() else ""


def _calendar_bounds(path: Path) -> tuple[str, str]:
    start_dates: list[str] = []
    end_dates: list[str] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            start_date = _valid_date(row.get("start_date", ""))
            end_date = _valid_date(row.get("end_date", ""))
            if start_date:
                start_dates.append(start_date)
            if end_date:
                end_dates.append(end_date)
    return (min(start_dates) if start_dates else "", max(end_dates) if end_dates else "")


class MadridSourceAdapter(SourceAdapter):
    name = "madrid_gtfs_merge"

    def prepare(self, cfg: AppConfig) -> PrepareReport:
        sources, issues, warnings = _discover_sources(cfg.paths.offline_raw_dir)
        if issues:
            notes = [
                "Madrid preparation expects the official public GTFS archives under offline_raw_dir/madrid.",
                "Required feeds: Metro, Metro Ligero, EMT, Urban buses, Interurban buses.",
            ]
            return PrepareReport(
                city=cfg.city_id,
                adapter=self.name,
                status="blocked_missing_raw_sources",
                ready_for_ingest=False,
                notes=notes,
                warnings=warnings,
                missing_required_files=issues,
                details={"offline_raw_dir": str(cfg.paths.offline_raw_dir)},
            )

        contexts = _build_source_contexts(sources)
        cfg.paths.gtfs_input.mkdir(parents=True, exist_ok=True)
        generated_files: list[str] = []
        row_counts: dict[str, int] = {}

        agency_path = cfg.paths.gtfs_input / "agency.txt"
        written_agencies: set[str] = set()
        agency_rows: list[dict[str, str]] = []
        for source in sources:
            source_rows = 0
            for row in _iter_rows(source, "agency.txt"):
                agency_id = _prefixed(source, row.get("agency_id") or source.spec.key)
                written_agencies.add(agency_id)
                agency_rows.append(
                    {
                        "agency_id": agency_id,
                        "agency_name": (row.get("agency_name") or source.spec.label).strip() or source.spec.label,
                        "agency_url": (row.get("agency_url") or "https://www.crtm.es/").strip() or "https://www.crtm.es/",
                        "agency_timezone": (row.get("agency_timezone") or "Europe/Madrid").strip() or "Europe/Madrid",
                    }
                )
                source_rows += 1
            if source_rows == 0:
                default_agency_id = contexts[source.spec.key].default_agency_id
                if default_agency_id not in written_agencies:
                    written_agencies.add(default_agency_id)
                    agency_rows.append(
                        {
                            "agency_id": default_agency_id,
                            "agency_name": source.spec.label,
                            "agency_url": "https://www.crtm.es/",
                            "agency_timezone": "Europe/Madrid",
                        }
                    )
        _write_csv(agency_path, STANDARD_HEADERS["agency.txt"], agency_rows)
        generated_files.append(str(agency_path))
        row_counts["agency.txt"] = len(agency_rows)

        routes_path = cfg.paths.gtfs_input / "routes.txt"
        row_counts["routes.txt"] = _merge_table(
            out_path=routes_path,
            fieldnames=STANDARD_HEADERS["routes.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "route_id": _prefixed(source, row.get("route_id") or ""),
                    "agency_id": (
                        _prefixed(source, row.get("agency_id") or "")
                        or contexts[source.spec.key].default_agency_id
                    ),
                    "route_short_name": (row.get("route_short_name") or "").strip(),
                    "route_long_name": (row.get("route_long_name") or "").strip(),
                    "route_type": (row.get("route_type") or "").strip(),
                }
                for row in _iter_rows(source, "routes.txt")
            ),
        )
        generated_files.append(str(routes_path))

        stops_path = cfg.paths.gtfs_input / "stops.txt"
        row_counts["stops.txt"] = _merge_table(
            out_path=stops_path,
            fieldnames=STANDARD_HEADERS["stops.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "stop_id": _prefixed(source, row.get("stop_id") or ""),
                    "stop_name": (row.get("stop_name") or "").strip(),
                    "stop_lat": (row.get("stop_lat") or "").strip(),
                    "stop_lon": (row.get("stop_lon") or "").strip(),
                    "location_type": (row.get("location_type") or "0").strip() or "0",
                    "parent_station": _prefixed(source, row.get("parent_station") or ""),
                }
                for row in _iter_rows(source, "stops.txt")
            ),
        )
        generated_files.append(str(stops_path))

        trips_path = cfg.paths.gtfs_input / "trips.txt"
        row_counts["trips.txt"] = _merge_table(
            out_path=trips_path,
            fieldnames=STANDARD_HEADERS["trips.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "route_id": _prefixed(source, row.get("route_id") or ""),
                    "service_id": _prefixed(source, row.get("service_id") or ""),
                    "trip_id": _prefixed(source, row.get("trip_id") or ""),
                    "direction_id": (row.get("direction_id") or "0").strip() or "0",
                }
                for row in _iter_rows(source, "trips.txt")
            ),
        )
        generated_files.append(str(trips_path))

        stop_times_path = cfg.paths.gtfs_input / "stop_times.txt"
        row_counts["stop_times.txt"] = _merge_table(
            out_path=stop_times_path,
            fieldnames=STANDARD_HEADERS["stop_times.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "trip_id": _prefixed(source, row.get("trip_id") or ""),
                    "arrival_time": (row.get("arrival_time") or "").strip(),
                    "departure_time": (row.get("departure_time") or "").strip(),
                    "stop_id": _prefixed(source, row.get("stop_id") or ""),
                    "stop_sequence": (row.get("stop_sequence") or "").strip(),
                }
                for row in _iter_rows(source, "stop_times.txt")
            ),
        )
        generated_files.append(str(stop_times_path))

        calendar_path = cfg.paths.gtfs_input / "calendar.txt"
        row_counts["calendar.txt"] = _merge_table(
            out_path=calendar_path,
            fieldnames=STANDARD_HEADERS["calendar.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "service_id": _prefixed(source, row.get("service_id") or ""),
                    "monday": (row.get("monday") or "0").strip() or "0",
                    "tuesday": (row.get("tuesday") or "0").strip() or "0",
                    "wednesday": (row.get("wednesday") or "0").strip() or "0",
                    "thursday": (row.get("thursday") or "0").strip() or "0",
                    "friday": (row.get("friday") or "0").strip() or "0",
                    "saturday": (row.get("saturday") or "0").strip() or "0",
                    "sunday": (row.get("sunday") or "0").strip() or "0",
                    "start_date": (row.get("start_date") or "").strip(),
                    "end_date": (row.get("end_date") or "").strip(),
                }
                for row in _iter_rows(source, "calendar.txt")
            ),
        )
        generated_files.append(str(calendar_path))

        calendar_dates_path = cfg.paths.gtfs_input / "calendar_dates.txt"
        row_counts["calendar_dates.txt"] = _merge_table(
            out_path=calendar_dates_path,
            fieldnames=STANDARD_HEADERS["calendar_dates.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "service_id": _prefixed(source, row.get("service_id") or ""),
                    "date": (row.get("date") or "").strip(),
                    "exception_type": (row.get("exception_type") or "").strip(),
                }
                for row in _iter_rows(source, "calendar_dates.txt")
            ),
        )
        generated_files.append(str(calendar_dates_path))

        transfers_path = cfg.paths.gtfs_input / "transfers.txt"
        row_counts["transfers.txt"] = _merge_table(
            out_path=transfers_path,
            fieldnames=STANDARD_HEADERS["transfers.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "from_stop_id": _prefixed(source, row.get("from_stop_id") or ""),
                    "to_stop_id": _prefixed(source, row.get("to_stop_id") or ""),
                    "transfer_type": (row.get("transfer_type") or "0").strip() or "0",
                    "min_transfer_time": (row.get("min_transfer_time") or "0").strip() or "0",
                }
                for row in _iter_rows(source, "transfers.txt")
            ),
        )
        generated_files.append(str(transfers_path))

        pathways_path = cfg.paths.gtfs_input / "pathways.txt"
        row_counts["pathways.txt"] = _merge_table(
            out_path=pathways_path,
            fieldnames=STANDARD_HEADERS["pathways.txt"],
            sources=sources,
            row_builder=lambda source: (
                {
                    "pathway_id": _prefixed(source, row.get("pathway_id") or ""),
                    "from_stop_id": _prefixed(source, row.get("from_stop_id") or ""),
                    "to_stop_id": _prefixed(source, row.get("to_stop_id") or ""),
                    "pathway_mode": (row.get("pathway_mode") or "1").strip() or "1",
                    "is_bidirectional": (row.get("is_bidirectional") or "0").strip() or "0",
                    "length": (row.get("length") or "0").strip() or "0",
                    "traversal_time": (row.get("traversal_time") or "0").strip() or "0",
                }
                for row in _iter_rows(source, "pathways.txt")
            ),
        )
        generated_files.append(str(pathways_path))

        start_dates = []
        end_dates = []
        version_tokens: list[str] = []
        for source in sources:
            feed_info = contexts[source.spec.key].feed_info
            start_date = _valid_date(feed_info.get("feed_start_date", ""))
            end_date = _valid_date(feed_info.get("feed_end_date", ""))
            if start_date:
                start_dates.append(start_date)
            if end_date:
                end_dates.append(end_date)
            version = (feed_info.get("feed_version") or "").strip()
            version_tokens.append(f"{source.spec.key}:{version or source.path.stem}")

        calendar_start_date, calendar_end_date = _calendar_bounds(calendar_path)

        feed_info_path = cfg.paths.gtfs_input / "feed_info.txt"
        _write_csv(
            feed_info_path,
            STANDARD_HEADERS["feed_info.txt"],
            [
                {
                    "feed_publisher_name": "Consorcio Regional de Transportes de Madrid + EMT Madrid",
                    "feed_publisher_url": "https://www.crtm.es/",
                    "feed_lang": "es",
                    "feed_start_date": min(start_dates) if start_dates else calendar_start_date,
                    "feed_end_date": max(end_dates) if end_dates else calendar_end_date,
                    "feed_version": ",".join(version_tokens),
                }
            ],
        )
        generated_files.append(str(feed_info_path))
        row_counts["feed_info.txt"] = 1

        missing = find_missing_required_gtfs_files(cfg.paths.gtfs_input)
        notes = [
            "Madrid GTFS generated by merging the public CRTM and EMT GTFS archives.",
            "Cercanias is intentionally excluded until the public GTFS archive is fixed upstream.",
        ]
        return PrepareReport(
            city=cfg.city_id,
            adapter=self.name,
            status="ready_for_ingest" if not missing else "blocked_missing_gtfs_files",
            ready_for_ingest=not missing,
            notes=notes,
            warnings=warnings,
            generated_files=generated_files,
            missing_required_files=missing,
            details={
                "offline_raw_dir": str(cfg.paths.offline_raw_dir),
                "gtfs_input": str(cfg.paths.gtfs_input),
                "sources": [source.path.name for source in sources],
                "rows_written": row_counts,
            },
        )
