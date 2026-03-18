import type {
  ExpressionSpecification,
  Map as MapLibreMap,
  StyleSpecification
} from "maplibre-gl";
import type { FeatureCollection } from "geojson";

import { EMPTY_FEATURE_COLLECTION } from "@/components/heatmap/maplibreData";
import type { Locale } from "@/i18n/types";
import openFreeMapLibertyStyle from "@/components/heatmap/openfreemap-liberty-style.json";
import {
  ISOCHRONE_RASTER_LAYER_ID,
  ISOCHRONE_RASTER_SOURCE_ID,
  ORIGIN_LAYER_ID,
  ORIGIN_SOURCE_ID,
  PATH_LINE_LAYER_ID,
  PATH_POINT_LAYER_ID,
  PATH_SOURCE_ID
} from "@/components/heatmap/maplibreIds";

const localizedStyleCache = new Map<Locale, StyleSpecification>();
const BASE_LIBERTY_STYLE = openFreeMapLibertyStyle as StyleSpecification;

export function createBaseMapStyle(locale: Locale): StyleSpecification {
  const cached = localizedStyleCache.get(locale);
  if (cached) {
    return cached;
  }

  const localizedStyle = buildLocalizedBaseMapStyle(locale);
  localizedStyleCache.set(locale, localizedStyle);
  return localizedStyle;
}

export function ensureOverlaySourcesAndLayers(map: MapLibreMap) {
  if (!map.getSource(PATH_SOURCE_ID)) {
    map.addSource(PATH_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION
    });
  }
  if (!map.getSource(ORIGIN_SOURCE_ID)) {
    map.addSource(ORIGIN_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION
    });
  }
  if (!map.getLayer(PATH_LINE_LAYER_ID)) {
    map.addLayer({
      id: PATH_LINE_LAYER_ID,
      type: "line",
      source: PATH_SOURCE_ID,
      filter: ["==", ["geometry-type"], "LineString"],
      paint: {
        "line-color": ["coalesce", ["get", "color"], "#203347"],
        "line-width": 5,
        "line-opacity": 0.9
      },
      layout: {
        "line-join": "round",
        "line-cap": "round"
      }
    });
  }
  if (!map.getLayer(PATH_POINT_LAYER_ID)) {
    map.addLayer({
      id: PATH_POINT_LAYER_ID,
      type: "circle",
      source: PATH_SOURCE_ID,
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 4,
        "circle-color": ["coalesce", ["get", "color"], "#203347"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1
      }
    });
  }
  if (!map.getLayer(ORIGIN_LAYER_ID)) {
    map.addLayer({
      id: ORIGIN_LAYER_ID,
      type: "circle",
      source: ORIGIN_SOURCE_ID,
      paint: {
        "circle-radius": 7,
        "circle-color": ["coalesce", ["get", "color"], "#203347"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
        "circle-opacity": 0.95
      }
    });
  }
}

function buildLocalizedBaseMapStyle(locale: Locale): StyleSpecification {
  const style = structuredClone(BASE_LIBERTY_STYLE);
  if (locale === "en") {
    return style;
  }

  style.layers = (style.layers ?? []).map((layer) => {
    if (layer.type !== "symbol" || !layer.layout || layer.layout["text-field"] === undefined) {
      return layer;
    }

    return {
      ...layer,
      layout: {
        ...layer.layout,
        "text-field": localizeExpression(layer.layout["text-field"])
      }
    };
  });

  return style;
}

function localizeExpression(value: unknown): string | ExpressionSpecification {
  if (!Array.isArray(value)) {
    return typeof value === "string" ? value : "";
  }
  if (value.length === 2 && value[0] === "get" && value[1] === "name_en") {
    return [
      "coalesce",
      ["get", "name:fr"],
      ["get", "name_fr"],
      ["get", "name"],
      ["get", "name_en"]
    ] as ExpressionSpecification;
  }
  return value.map((item) => localizeExpression(item)) as ExpressionSpecification;
}

export function updateGeoJsonSource(map: MapLibreMap, sourceId: string, data: FeatureCollection) {
  const source = map.getSource(sourceId);
  if (!source || !("setData" in source) || typeof source.setData !== "function") {
    return;
  }
  source.setData(data);
}

type RasterOverlay = {
  imageUrl: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
};

function findHeatmapInsertBeforeLayerId(map: MapLibreMap): string | undefined {
  const layers = map.getStyle()?.layers ?? [];
  return layers.find((layer) => layer.type === "symbol")?.id;
}

export function updateIsochroneRasterSource(map: MapLibreMap, overlay: RasterOverlay | null) {
  const existingLayer = map.getLayer(ISOCHRONE_RASTER_LAYER_ID);
  const existingSource = map.getSource(ISOCHRONE_RASTER_SOURCE_ID) as
    | { updateImage?: (options: { url: string; coordinates: RasterOverlay["coordinates"] }) => void }
    | undefined;

  if (!overlay) {
    if (existingLayer) {
      map.removeLayer(ISOCHRONE_RASTER_LAYER_ID);
    }
    if (existingSource) {
      map.removeSource(ISOCHRONE_RASTER_SOURCE_ID);
    }
    return;
  }

  if (!existingSource) {
    map.addSource(ISOCHRONE_RASTER_SOURCE_ID, {
      type: "image",
      url: overlay.imageUrl,
      coordinates: overlay.coordinates
    });
  } else {
    existingSource.updateImage?.({
      url: overlay.imageUrl,
      coordinates: overlay.coordinates
    });
  }

  if (!map.getLayer(ISOCHRONE_RASTER_LAYER_ID)) {
    map.addLayer({
      id: ISOCHRONE_RASTER_LAYER_ID,
      type: "raster",
      source: ISOCHRONE_RASTER_SOURCE_ID,
      paint: {
        "raster-opacity": 1
      }
    }, findHeatmapInsertBeforeLayerId(map));
  }
}
