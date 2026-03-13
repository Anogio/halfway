import type { ExpressionSpecification, Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import type { FeatureCollection } from "geojson";

import { EMPTY_FEATURE_COLLECTION } from "@/components/heatmap/maplibreData";
import {
  ISOCHRONE_FILL_LAYER_ID,
  ISOCHRONE_LINE_LAYER_ID,
  ISOCHRONE_SOURCE_ID,
  ORIGIN_LAYER_ID,
  ORIGIN_SOURCE_ID,
  PATH_LINE_LAYER_ID,
  PATH_POINT_LAYER_ID,
  PATH_SOURCE_ID
} from "@/components/heatmap/maplibreIds";

const ISOCHRONE_COLOR_STOPS: Array<[number, string]> = [
  [0, "rgb(21 48 122)"],
  [300, "rgb(18 95 181)"],
  [600, "rgb(0 141 213)"],
  [900, "rgb(0 181 180)"],
  [1200, "rgb(117 205 58)"],
  [1500, "rgb(236 221 68)"],
  [1800, "rgb(250 171 56)"],
  [2700, "rgb(230 93 66)"],
  [3600, "rgb(174 36 69)"]
];

function isochroneFillColorExpression(): ExpressionSpecification {
  return [
    "interpolate",
    ["linear"],
    ["coalesce", ["to-number", ["get", "max_time_s"]], 0],
    ...ISOCHRONE_COLOR_STOPS.flatMap(([seconds, color]) => [seconds, color])
  ] as ExpressionSpecification;
}

export function createRasterStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: [
          "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
          "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png"
        ],
        tileSize: 256,
        attribution: "&copy; OpenStreetMap contributors"
      }
    },
    layers: [
      {
        id: "osm",
        type: "raster",
        source: "osm"
      }
    ]
  };
}

export function ensureOverlaySourcesAndLayers(map: MapLibreMap) {
  if (!map.getSource(ISOCHRONE_SOURCE_ID)) {
    map.addSource(ISOCHRONE_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_FEATURE_COLLECTION
    });
  }
  if (!map.getLayer(ISOCHRONE_FILL_LAYER_ID)) {
    map.addLayer({
      id: ISOCHRONE_FILL_LAYER_ID,
      type: "fill",
      source: ISOCHRONE_SOURCE_ID,
      paint: {
        "fill-color": isochroneFillColorExpression(),
        "fill-opacity": 0.44
      }
    });
  }
  if (!map.getLayer(ISOCHRONE_LINE_LAYER_ID)) {
    map.addLayer({
      id: ISOCHRONE_LINE_LAYER_ID,
      type: "line",
      source: ISOCHRONE_SOURCE_ID,
      paint: {
        "line-color": isochroneFillColorExpression(),
        "line-width": 1,
        "line-opacity": 0.9
      },
      layout: {
        "line-join": "round",
        "line-cap": "round"
      }
    });
  }
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

export function updateGeoJsonSource(map: MapLibreMap, sourceId: string, data: FeatureCollection) {
  const source = map.getSource(sourceId);
  if (!source || !("setData" in source) || typeof source.setData !== "function") {
    return;
  }
  source.setData(data);
}
