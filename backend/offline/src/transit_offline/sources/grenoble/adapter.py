from __future__ import annotations

from pathlib import Path

from transit_offline.common.config import AppConfig
from transit_offline.sources.base import PrepareReport, SourceAdapter

_CORE_GTFS_FILES = (
    "agency.txt",
    "calendar.txt",
    "calendar_dates.txt",
    "feed_info.txt",
    "routes.txt",
    "stop_times.txt",
    "stops.txt",
    "trips.txt",
)

_OPTIONAL_REQUIRED_FILES: dict[str, str] = {
    "pathways.txt": (
        "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional,"
        "length,traversal_time,stair_count,max_slope,min_width,signposted_as,"
        "reversed_signposted_as\n"
    ),
    "transfers.txt": "from_stop_id,to_stop_id,transfer_type,min_transfer_time\n",
}


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


class GrenobleSourceAdapter(SourceAdapter):
    name = "grenoble_gtfs"

    def prepare(self, cfg: AppConfig) -> PrepareReport:
        gtfs_dir = cfg.paths.gtfs_input
        missing_core_files = [name for name in _CORE_GTFS_FILES if not (gtfs_dir / name).exists()]
        if missing_core_files:
            return PrepareReport(
                city=cfg.city_id,
                adapter=self.name,
                status="missing_gtfs_files",
                ready_for_ingest=False,
                missing_required_files=missing_core_files,
                details={"gtfs_input": str(gtfs_dir)},
            )

        generated_files: list[str] = []
        for name, header in _OPTIONAL_REQUIRED_FILES.items():
            path = gtfs_dir / name
            if _write_if_missing(path, header):
                generated_files.append(str(path))

        notes = ["Expected input is official GTFS extracted in the configured city gtfs_input path."]
        warnings: list[str] = []
        if generated_files:
            warnings.append(
                "Generated empty optional GTFS files required by the current ingest pipeline."
            )

        return PrepareReport(
            city=cfg.city_id,
            adapter=self.name,
            status="ready_for_ingest",
            ready_for_ingest=True,
            notes=notes,
            warnings=warnings,
            generated_files=generated_files,
            details={"gtfs_input": str(gtfs_dir)},
        )
