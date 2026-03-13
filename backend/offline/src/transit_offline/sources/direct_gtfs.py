from __future__ import annotations

from transit_offline.common.config import AppConfig
from transit_offline.sources.base import PrepareReport, SourceAdapter


class DirectGtfsSourceAdapter(SourceAdapter):
    name = "direct_gtfs"

    def prepare(self, cfg: AppConfig) -> PrepareReport:
        return PrepareReport(
            city=cfg.city_id,
            adapter=self.name,
            status="ready_for_ingest",
            ready_for_ingest=True,
            notes=["Expected input is already GTFS in the configured city gtfs_input path."],
            details={"gtfs_input": str(cfg.paths.gtfs_input)},
        )
