import type { Feature, FeatureCollection, GeoJsonProperties, LineString, Point } from "geojson";

import type { MultiPathItemResponse } from "@/lib/api";
import { shouldHideOriginLabel } from "@/components/heatmap/originLabels";
import type { OriginPoint } from "@/components/heatmap/types";

export const EMPTY_FEATURE_COLLECTION: FeatureCollection = {
  type: "FeatureCollection",
  features: []
};

function isFeatureCollection(value: unknown): value is FeatureCollection {
  return Boolean(
    value &&
      typeof value === "object" &&
      (value as { type?: unknown }).type === "FeatureCollection" &&
      Array.isArray((value as { features?: unknown }).features)
  );
}

export function buildIsochroneSourceData(displayFeatureCollection: unknown): FeatureCollection {
  if (!isFeatureCollection(displayFeatureCollection)) {
    return EMPTY_FEATURE_COLLECTION;
  }
  return displayFeatureCollection;
}

export function buildPathSourceData(
  origins: OriginPoint[],
  pathByOriginId: Record<string, MultiPathItemResponse | null>
): FeatureCollection {
  const originColorById = new Map(origins.map((origin) => [origin.id, origin.color]));
  const features: Array<Feature<LineString | Point, GeoJsonProperties>> = [];

  for (const origin of origins) {
    const pathData = pathByOriginId[origin.id];
    if (!pathData || !pathData.reachable || !Array.isArray(pathData.nodes)) {
      continue;
    }
    const color = originColorById.get(origin.id) ?? "#203347";
    const coordinates = pathData.nodes.map((node) => [node.lon, node.lat] as [number, number]);
    if (coordinates.length >= 2) {
      features.push({
        type: "Feature",
        properties: { origin_id: origin.id, color },
        geometry: { type: "LineString", coordinates }
      });
      continue;
    }
    if (coordinates.length === 1) {
      features.push({
        type: "Feature",
        properties: { origin_id: origin.id, color },
        geometry: { type: "Point", coordinates: coordinates[0] }
      });
    }
  }

  return {
    type: "FeatureCollection",
    features
  };
}

export function buildOriginSourceData(origins: OriginPoint[]): FeatureCollection {
  const features: Array<Feature<Point, GeoJsonProperties>> = origins.map((origin) => ({
    type: "Feature",
    properties: {
      origin_id: origin.id,
      color: origin.color,
      label: shouldHideOriginLabel(origin) ? "" : origin.label
    },
    geometry: {
      type: "Point",
      coordinates: [origin.lon, origin.lat]
    }
  }));

  return {
    type: "FeatureCollection",
    features
  };
}
