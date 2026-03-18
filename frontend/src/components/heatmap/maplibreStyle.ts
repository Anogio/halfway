import type {
  ExpressionSpecification,
  LayerSpecification,
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
        "line-width": 6,
        "line-opacity": 0.92,
        "line-blur": 0.2
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
        "circle-radius": 4.5,
        "circle-color": ["coalesce", ["get", "color"], "#203347"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1.2
      }
    });
  }
  if (!map.getLayer(ORIGIN_LAYER_ID)) {
    map.addLayer({
      id: ORIGIN_LAYER_ID,
      type: "circle",
      source: ORIGIN_SOURCE_ID,
      paint: {
        "circle-radius": 7.5,
        "circle-color": ["coalesce", ["get", "color"], "#203347"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2.3,
        "circle-opacity": 0.95
      }
    });
  }
}

function buildLocalizedBaseMapStyle(locale: Locale): StyleSpecification {
  const style = structuredClone(BASE_LIBERTY_STYLE);
  style.layers = (style.layers ?? []).map((layer) => {
    const localizedLayer =
      locale === "en" || layer.type !== "symbol" || !layer.layout || layer.layout["text-field"] === undefined
        ? layer
        : {
            ...layer,
            layout: {
              ...layer.layout,
              "text-field": localizeExpression(layer.layout["text-field"])
            }
          };
    return tuneBaseMapLayer(localizedLayer);
  });
  return style;
}

function tuneBaseMapLayer(layer: LayerSpecification): LayerSpecification {
  switch (layer.id) {
    case "water":
      return withPaint(layer, {
        "fill-color": "#b8d7fb",
        "fill-opacity": 0.96
      });
    case "waterway_river":
      return withPaint(layer, {
        "line-color": "#7baee7",
        "line-width": ["interpolate", ["exponential", 1.18], ["zoom"], 9, 0.9, 13, 2.2, 20, 7]
      });
    case "waterway_other":
    case "waterway_tunnel":
      return withPaint(layer, {
        "line-color": "#8db8eb",
        "line-opacity": 0.88
      });
    case "park":
      return withPaint(layer, {
        "fill-color": "#d4e6bf",
        "fill-opacity": 0.82,
        "fill-outline-color": "rgba(116, 169, 92, 0.42)"
      });
    case "park_outline":
      return withPaint(layer, {
        "line-color": "rgba(139, 176, 112, 0.5)"
      });
    case "landcover_wood":
      return withPaint(layer, {
        "fill-color": "hsla(101,42%,68%,0.82)",
        "fill-opacity": 0.56
      });
    case "landcover_grass":
      return withPaint(layer, {
        "fill-color": "rgba(165, 211, 150, 1)",
        "fill-opacity": 0.44
      });
    case "landuse_cemetery":
      return withPaint(layer, {
        "fill-color": "hsl(84, 31%, 80%)"
      });
    case "road_trunk_primary":
    case "road_motorway":
    case "bridge_trunk_primary":
    case "bridge_motorway":
    case "tunnel_trunk_primary":
    case "tunnel_motorway":
      return withPaint(layer, {
        "line-opacity": 0.98
      });
    case "road_secondary_tertiary":
    case "bridge_secondary_tertiary":
    case "tunnel_secondary_tertiary":
      return withPaint(layer, {
        "line-opacity": 0.94
      });
    case "road_major_rail":
    case "road_transit_rail":
    case "bridge_major_rail":
    case "bridge_transit_rail":
    case "tunnel_major_rail":
    case "tunnel_transit_rail":
      return withPaint(layer, {
        "line-color": "#9b98a1",
        "line-width": ["interpolate", ["exponential", 1.35], ["zoom"], 12, 0.7, 15, 1.1, 20, 2.8],
        "line-opacity": 0.9
      });
    case "road_major_rail_hatching":
    case "road_transit_rail_hatching":
    case "bridge_major_rail_hatching":
    case "bridge_transit_rail_hatching":
    case "tunnel_major_rail_hatching":
    case "tunnel_transit_rail_hatching":
      return withPaint(layer, {
        "line-color": "#9b98a1",
        "line-opacity": 0.78
      });
    case "waterway_line_label":
    case "water_name_point_label":
    case "water_name_line_label":
      return withPaint(layer, {
        "text-color": "#5e8ec4",
        "text-halo-color": "rgba(255,255,255,0.82)",
        "text-halo-width": 1.8
      });
    case "poi_transit":
      return {
        ...layer,
        layout: {
          ...layer.layout,
          "icon-size": 0.8,
          "text-size": 12.5
        },
        paint: {
          ...layer.paint,
          "text-color": "#425f7d",
          "text-halo-width": 1.15
        }
      } as LayerSpecification;
    case "label_other":
      return {
        ...layer,
        layout: {
          ...layer.layout,
          "text-size": ["interpolate", ["linear"], ["zoom"], 7, 9.6, 10, 10.3, 12, 11.4]
        },
        paint: {
          ...layer.paint,
          "text-color": "#45586c",
          "text-halo-width": 1.25
        }
      } as LayerSpecification;
    case "label_village":
    case "label_town":
      return {
        ...layer,
        layout: {
          ...layer.layout,
          "text-size":
            layer.id === "label_village"
              ? ["interpolate", ["exponential", 1.2], ["zoom"], 6.6, 10.5, 11, 12.4]
              : ["interpolate", ["exponential", 1.2], ["zoom"], 6.6, 12.2, 11, 14.6]
        },
        paint: {
          ...layer.paint,
          "text-halo-width": 1.2
        }
      } as LayerSpecification;
    case "label_city":
    case "label_city_capital":
      return {
        ...layer,
        layout: {
          ...layer.layout,
          "text-size":
            layer.id === "label_city"
              ? ["interpolate", ["exponential", 1.18], ["zoom"], 3.5, 11.6, 7, 13.6, 11, 18.8]
              : ["interpolate", ["exponential", 1.18], ["zoom"], 3.5, 12.8, 7, 14.8, 11, 20.8]
        },
        paint: {
          ...layer.paint,
          "text-halo-width": 1.25
        }
      } as LayerSpecification;
    case "highway-name-major":
      return {
        ...layer,
        paint: {
          ...layer.paint,
          "text-color": "#7c6449",
          "text-halo-width": 1.1
        }
      } as LayerSpecification;
    default:
      return layer;
  }
}

function withPaint(layer: LayerSpecification, paint: Record<string, unknown>): LayerSpecification {
  return {
    ...layer,
    paint: {
      ...(layer.paint as Record<string, unknown> | undefined),
      ...paint
    }
  } as LayerSpecification;
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
