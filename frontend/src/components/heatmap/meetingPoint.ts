import type { MultiIsochroneResponse } from "@/lib/api";

import { findScalarGridMinimum } from "@/components/heatmap/scalarGrid";
import type { InspectCardState } from "@/components/heatmap/types";

export function findBestMeetingInspectCard(data: MultiIsochroneResponse | null): InspectCardState | null {
  const bestSample = findScalarGridMinimum(data?.scalar_grid);
  if (!bestSample) {
    return null;
  }
  return {
    lat: bestSample.lat,
    lon: bestSample.lon,
    minS: bestSample.timeS,
    maxS: bestSample.timeS
  };
}
