from __future__ import annotations

from transit_offline.common.config import AppConfig
from transit_offline.sources.base import PrepareReport, SourceAdapter
from transit_offline.sources.gtfs_writer import write_normalized_dataset
from transit_offline.sources.london.mappers import build_london_dataset
from transit_offline.sources.london.validators import build_london_identity_warnings
from transit_offline.sources.validators import find_missing_required_gtfs_files


class LondonSourceAdapter(SourceAdapter):
    """
    London-specific converter adapter.

    Current scope:
    - builds GTFS files from London raw sources under `offline_raw_dir/london`
    - writes required GTFS files in `gtfs_input`
    - emits identity/sanity warnings on generated output
    """

    name = "london_scaffold"

    def prepare(self, cfg: AppConfig) -> PrepareReport:
        build = build_london_dataset(cfg.paths.offline_raw_dir)
        if build.missing_sources:
            notes = [
                "London conversion requires raw source files under offline_raw_dir/london.",
                "Run with live syndicated TfL feeds before build-all.",
            ]
            return PrepareReport(
                city=cfg.city_id,
                adapter=self.name,
                status="blocked_missing_raw_sources",
                ready_for_ingest=False,
                notes=notes,
                warnings=build.warnings,
                missing_required_files=build.missing_sources,
                details={"offline_raw_dir": str(cfg.paths.offline_raw_dir)},
            )

        cfg.paths.gtfs_input.mkdir(parents=True, exist_ok=True)
        written = write_normalized_dataset(build.dataset, cfg.paths.gtfs_input)
        missing = find_missing_required_gtfs_files(cfg.paths.gtfs_input)
        warnings = list(build.warnings)
        warnings.extend(
            build_london_identity_warnings(
                cfg.paths.gtfs_input,
                cfg.city.scope.bbox,
            )
        )

        notes = [
            "London GTFS generated from raw london sources.",
            *build.notes,
        ]
        return PrepareReport(
            city=cfg.city_id,
            adapter=self.name,
            status="ready_for_ingest" if not missing else "blocked_missing_gtfs_files",
            ready_for_ingest=not missing,
            notes=notes,
            warnings=warnings,
            generated_files=[str(path) for path in written],
            missing_required_files=missing,
            details={
                "gtfs_input": str(cfg.paths.gtfs_input),
                "offline_raw_dir": str(cfg.paths.offline_raw_dir),
                "stats": build.stats,
            },
        )
