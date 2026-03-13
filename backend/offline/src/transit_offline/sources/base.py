from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from transit_offline.common.config import AppConfig


@dataclass(frozen=True)
class PrepareReport:
    city: str
    adapter: str
    status: str
    ready_for_ingest: bool
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    generated_files: list[str] = field(default_factory=list)
    missing_required_files: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "adapter": self.adapter,
            "status": self.status,
            "ready_for_ingest": self.ready_for_ingest,
            "notes": self.notes,
            "warnings": self.warnings,
            "generated_files": self.generated_files,
            "missing_required_files": self.missing_required_files,
            "details": self.details,
        }


class SourceAdapter(ABC):
    """
    Contract for city-specific source preparation.

    The adapter may parse city-specific raw inputs and/or validate existing GTFS files.
    It should always return a structured report and avoid implicit side effects.
    """

    name = "source_adapter"

    @abstractmethod
    def prepare(self, cfg: AppConfig) -> PrepareReport:
        raise NotImplementedError
