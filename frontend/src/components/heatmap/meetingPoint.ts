import type { MultiIsochroneResponse } from "@/lib/api";

import type { InspectCardState } from "@/components/heatmap/types";

function computeRingCentroid(ring: unknown): { lat: number; lon: number } | null {
  if (!Array.isArray(ring) || ring.length < 3) {
    return null;
  }

  let sumLon = 0;
  let sumLat = 0;
  let count = 0;
  const maxIdx = ring.length - 1;
  for (let idx = 0; idx < ring.length; idx += 1) {
    if (idx === maxIdx && ring.length > 3) {
      const first = ring[0];
      const last = ring[maxIdx];
      if (
        Array.isArray(first) &&
        Array.isArray(last) &&
        Number(first[0]) === Number(last[0]) &&
        Number(first[1]) === Number(last[1])
      ) {
        continue;
      }
    }

    const point = ring[idx];
    if (!Array.isArray(point) || point.length < 2) {
      continue;
    }

    const lon = Number(point[0]);
    const lat = Number(point[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      continue;
    }

    sumLon += lon;
    sumLat += lat;
    count += 1;
  }

  if (count === 0) {
    return null;
  }

  return {
    lat: Number((sumLat / count).toFixed(5)),
    lon: Number((sumLon / count).toFixed(5))
  };
}

export function findBestMeetingInspectCard(data: MultiIsochroneResponse | null): InspectCardState | null {
  const features = data?.feature_collection?.features;
  if (!Array.isArray(features) || features.length === 0) {
    return null;
  }

  let bestInspect: InspectCardState | null = null;
  let bestMinS = Number.POSITIVE_INFINITY;
  for (const feature of features) {
    const minS = Number(feature?.properties?.min_time_s);
    const maxS = Number(feature?.properties?.max_time_s);
    if (!Number.isFinite(minS) || !Number.isFinite(maxS)) {
      continue;
    }

    const coordinates = feature?.geometry?.coordinates;
    if (!Array.isArray(coordinates) || coordinates.length === 0) {
      continue;
    }
    const firstPolygon = coordinates[0];
    if (!Array.isArray(firstPolygon) || firstPolygon.length === 0) {
      continue;
    }

    const outerRing = firstPolygon[0];
    const centroid = computeRingCentroid(outerRing);
    if (!centroid) {
      continue;
    }

    if (minS < bestMinS) {
      bestInspect = {
        lat: centroid.lat,
        lon: centroid.lon,
        minS,
        maxS
      };
      bestMinS = minS;
    }
  }

  return bestInspect;
}
