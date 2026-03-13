from __future__ import annotations

import json

from transit_offline.common.config import AppConfig, ensure_dirs, load_config
from transit_offline.sources.registry import get_source_adapter


def run_prepare_data(*, city_id: str | None = None, config: AppConfig | None = None) -> dict[str, object]:
    if config is None and city_id is None:
        raise ValueError("city_id is required when config is not provided")
    cfg = config or load_config(city_id=city_id or "")
    ensure_dirs(cfg)

    adapter = get_source_adapter(cfg.city_id)
    report = adapter.prepare(cfg).to_dict()

    report_path = cfg.paths.offline_interim_dir / "prepare_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report
