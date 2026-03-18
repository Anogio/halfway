import type { Map as MapLibreMap, StyleSpecification } from "maplibre-gl";
import type { FeatureCollection } from "geojson";

import { EMPTY_FEATURE_COLLECTION } from "@/components/heatmap/maplibreData";
import {
  ISOCHRONE_RASTER_LAYER_ID,
  ISOCHRONE_RASTER_SOURCE_ID,
  ORIGIN_LAYER_ID,
  ORIGIN_SOURCE_ID,
  PATH_LINE_LAYER_ID,
  PATH_POINT_LAYER_ID,
  PATH_SOURCE_ID
} from "@/components/heatmap/maplibreIds";

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

type RasterOverlay = {
  imageUrl: string;
  coordinates: [[number, number], [number, number], [number, number], [number, number]];
};

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
    }, PATH_LINE_LAYER_ID);
  }
}
