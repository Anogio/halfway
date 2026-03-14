import type { Feature, GeoJsonProperties, MultiPolygon } from "geojson";
import type {
  LngLatLike,
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  Popup as MapLibrePopup
} from "maplibre-gl";
import type { MutableRefObject } from "react";

import { bucketLabel } from "@/lib/heatmapPresentation.mjs";
import { ISOCHRONE_FILL_LAYER_ID } from "@/components/heatmap/maplibreIds";
import type { InspectCardState } from "@/components/heatmap/types";

export type BucketLabelFormatterRef = MutableRefObject<
  (minMinutes: number, maxMinutes: number) => string
>;

const DESKTOP_CLICK_PREVIEW_MS = 1200;
const TOUCH_TAP_PREVIEW_MS = 3000;

function popupCoordinates(lngLat: { lng: number; lat: number }): LngLatLike {
  return [Number(lngLat.lng.toFixed(5)), Number(lngLat.lat.toFixed(5))];
}

function isTouchInteraction(originalEvent?: Event): boolean {
  if (!originalEvent) {
    return false;
  }

  if (typeof TouchEvent !== "undefined" && originalEvent instanceof TouchEvent) {
    return true;
  }

  if (typeof PointerEvent !== "undefined" && originalEvent instanceof PointerEvent) {
    return originalEvent.pointerType === "touch";
  }

  const sourceCapabilities = (originalEvent as MouseEvent & {
    sourceCapabilities?: { firesTouchEvents?: boolean };
  }).sourceCapabilities;
  return sourceCapabilities?.firesTouchEvents === true;
}

function featureBucketLabel(
  feature: Feature<MultiPolygon, GeoJsonProperties> | undefined,
  bucketLabelFormatterRef: BucketLabelFormatterRef
): { label: string; minS: number; maxS: number } | null {
  if (!feature) {
    return null;
  }

  const minS = Number(feature.properties?.min_time_s ?? 0);
  const maxS = Number(feature.properties?.max_time_s ?? 0);
  return {
    minS,
    maxS,
    label: bucketLabel(minS, maxS, bucketLabelFormatterRef.current)
  };
}

function ensureIsochronePopup(
  maplibregl: typeof import("maplibre-gl"),
  popupRef: MutableRefObject<MapLibrePopup | null>
) {
  if (!popupRef.current) {
    popupRef.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "isochrone-tooltip-popup",
      offset: 14
    });
  }
  return popupRef.current;
}

export function clearIsochronePopup(
  popupRef: MutableRefObject<MapLibrePopup | null>,
  popupTimeoutRef: MutableRefObject<number | null>,
  tapPreviewActiveRef?: MutableRefObject<boolean>
) {
  if (popupTimeoutRef.current !== null) {
    window.clearTimeout(popupTimeoutRef.current);
    popupTimeoutRef.current = null;
  }
  if (tapPreviewActiveRef) {
    tapPreviewActiveRef.current = false;
  }
  popupRef.current?.remove();
}

export function updateInspectMarker(
  maplibregl: typeof import("maplibre-gl"),
  map: MapLibreMap,
  markerRef: MutableRefObject<MapLibreMarker | null>,
  popupRef: MutableRefObject<MapLibrePopup | null>,
  inspectCard: InspectCardState | null,
  inspectAddressLabel: string | null
) {
  if (!inspectCard) {
    popupRef.current?.remove();
    popupRef.current = null;
    markerRef.current?.remove();
    markerRef.current = null;
    return;
  }

  if (!markerRef.current) {
    const el = document.createElement("div");
    el.className = "arrival-point-marker";
    el.innerHTML =
      `<div class="arrival-point-target" aria-hidden="true">
        <span class="arrival-point-pulse"></span>
        <span class="arrival-point-crosshair horizontal"></span>
        <span class="arrival-point-crosshair vertical"></span>
        <span class="arrival-point-ring"></span>
        <span class="arrival-point-core"></span>
      </div>`;
    markerRef.current = new maplibregl.Marker({
      element: el,
      anchor: "center"
    });
  }

  markerRef.current.setLngLat([inspectCard.lon, inspectCard.lat]).addTo(map);

  const label = inspectAddressLabel?.trim();
  if (!label) {
    popupRef.current?.remove();
    popupRef.current = null;
    return;
  }

  if (!popupRef.current) {
    popupRef.current = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
      className: "arrival-point-tooltip-popup",
      offset: 26,
      maxWidth: "280px"
    });
  }

  popupRef.current.setLngLat([inspectCard.lon, inspectCard.lat]).setText(label).addTo(map);
}

export function handleIsochroneHover(
  maplibregl: typeof import("maplibre-gl"),
  map: MapLibreMap,
  bucketLabelFormatterRef: BucketLabelFormatterRef,
  popupRef: MutableRefObject<MapLibrePopup | null>,
  popupTimeoutRef: MutableRefObject<number | null>,
  tapPreviewActiveRef: MutableRefObject<boolean>,
  event: {
    features?: object[];
    point: { x: number; y: number };
    lngLat: { lng: number; lat: number };
    originalEvent?: Event;
  }
) {
  if (tapPreviewActiveRef.current || isTouchInteraction(event.originalEvent)) {
    return;
  }

  const hoveredFeature =
    (event.features?.[0] as Feature<MultiPolygon, GeoJsonProperties> | undefined) ??
    (map.queryRenderedFeatures([event.point.x, event.point.y], {
      layers: [ISOCHRONE_FILL_LAYER_ID]
    })[0] as Feature<MultiPolygon, GeoJsonProperties> | undefined);

  const bucket = featureBucketLabel(hoveredFeature, bucketLabelFormatterRef);
  if (!bucket) {
    clearIsochronePopup(popupRef, popupTimeoutRef, tapPreviewActiveRef);
    return;
  }

  if (popupTimeoutRef.current !== null) {
    window.clearTimeout(popupTimeoutRef.current);
    popupTimeoutRef.current = null;
  }

  ensureIsochronePopup(maplibregl, popupRef)
    .setLngLat(popupCoordinates(event.lngLat))
    .setText(bucket.label)
    .addTo(map);
}

export function handleMapClick(
  maplibregl: typeof import("maplibre-gl"),
  map: MapLibreMap,
  bucketLabelFormatterRef: BucketLabelFormatterRef,
  popupRef: MutableRefObject<MapLibrePopup | null>,
  popupTimeoutRef: MutableRefObject<number | null>,
  tapPreviewActiveRef: MutableRefObject<boolean>,
  onMapPointClickRef: MutableRefObject<(point: InspectCardState) => void>,
  event: {
    point: { x: number; y: number };
    lngLat: { lng: number; lat: number };
    originalEvent?: Event;
  }
) {
  const feature = map.queryRenderedFeatures([event.point.x, event.point.y], {
    layers: [ISOCHRONE_FILL_LAYER_ID]
  })[0] as Feature<MultiPolygon, GeoJsonProperties> | undefined;
  const lat = Number(event.lngLat.lat.toFixed(5));
  const lon = Number(event.lngLat.lng.toFixed(5));
  if (!feature) {
    clearIsochronePopup(popupRef, popupTimeoutRef, tapPreviewActiveRef);
    onMapPointClickRef.current({
      lat,
      lon,
      minS: null,
      maxS: null
    });
    return;
  }

  const bucket = featureBucketLabel(feature, bucketLabelFormatterRef);
  if (!bucket) {
    clearIsochronePopup(popupRef, popupTimeoutRef, tapPreviewActiveRef);
    return;
  }

  if (popupTimeoutRef.current !== null) {
    window.clearTimeout(popupTimeoutRef.current);
    popupTimeoutRef.current = null;
  }

  const touchInteraction = isTouchInteraction(event.originalEvent);
  tapPreviewActiveRef.current = touchInteraction;

  ensureIsochronePopup(maplibregl, popupRef)
    .setLngLat(popupCoordinates(event.lngLat))
    .setText(bucket.label)
    .addTo(map);
  onMapPointClickRef.current({
    lat,
    lon,
    minS: bucket.minS,
    maxS: bucket.maxS
  });
  popupTimeoutRef.current = window.setTimeout(() => {
    tapPreviewActiveRef.current = false;
    popupRef.current?.remove();
    popupTimeoutRef.current = null;
  }, touchInteraction ? TOUCH_TAP_PREVIEW_MS : DESKTOP_CLICK_PREVIEW_MS);
}
