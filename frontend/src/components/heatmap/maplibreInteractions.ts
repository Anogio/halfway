import type {
  LngLatLike,
  Map as MapLibreMap,
  Marker as MapLibreMarker,
  Popup as MapLibrePopup
} from "maplibre-gl";
import type { MutableRefObject } from "react";

import type { IsochroneScalarGrid } from "@/lib/api";
import { sampleScalarGridAtLngLat } from "@/components/heatmap/scalarGrid";
import type { InspectCardState } from "@/components/heatmap/types";

export type TimeLabelFormatterRef = MutableRefObject<(seconds: number) => string>;
export type ScalarGridRef = MutableRefObject<IsochroneScalarGrid | null | undefined>;

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

function scalarGridLabel(
  scalarGridRef: ScalarGridRef,
  lngLat: { lng: number; lat: number },
  timeLabelFormatterRef: TimeLabelFormatterRef
): { label: string; minS: number; maxS: number } | null {
  const sample = sampleScalarGridAtLngLat(scalarGridRef.current, lngLat.lng, lngLat.lat);
  if (!sample) {
    return null;
  }
  return {
    label: timeLabelFormatterRef.current(sample.timeS),
    minS: sample.timeS,
    maxS: sample.timeS
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
  timeLabelFormatterRef: TimeLabelFormatterRef,
  scalarGridRef: ScalarGridRef,
  popupRef: MutableRefObject<MapLibrePopup | null>,
  popupTimeoutRef: MutableRefObject<number | null>,
  tapPreviewActiveRef: MutableRefObject<boolean>,
  event: {
    lngLat: { lng: number; lat: number };
    originalEvent?: Event;
  }
) {
  if (tapPreviewActiveRef.current || isTouchInteraction(event.originalEvent)) {
    return;
  }

  const resolvedBucket = scalarGridLabel(scalarGridRef, event.lngLat, timeLabelFormatterRef);
  if (!resolvedBucket) {
    clearIsochronePopup(popupRef, popupTimeoutRef, tapPreviewActiveRef);
    return;
  }

  if (popupTimeoutRef.current !== null) {
    window.clearTimeout(popupTimeoutRef.current);
    popupTimeoutRef.current = null;
  }

  ensureIsochronePopup(maplibregl, popupRef)
    .setLngLat(popupCoordinates(event.lngLat))
    .setText(resolvedBucket.label)
    .addTo(map);
}

export function handleMapClick(
  maplibregl: typeof import("maplibre-gl"),
  map: MapLibreMap,
  timeLabelFormatterRef: TimeLabelFormatterRef,
  scalarGridRef: ScalarGridRef,
  popupRef: MutableRefObject<MapLibrePopup | null>,
  popupTimeoutRef: MutableRefObject<number | null>,
  tapPreviewActiveRef: MutableRefObject<boolean>,
  onMapPointClickRef: MutableRefObject<(point: InspectCardState) => void>,
  event: {
    lngLat: { lng: number; lat: number };
    originalEvent?: Event;
  }
) {
  const scalarBucket = scalarGridLabel(scalarGridRef, event.lngLat, timeLabelFormatterRef);
  const lat = Number(event.lngLat.lat.toFixed(5));
  const lon = Number(event.lngLat.lng.toFixed(5));
  if (!scalarBucket) {
    clearIsochronePopup(popupRef, popupTimeoutRef, tapPreviewActiveRef);
    onMapPointClickRef.current({
      lat,
      lon,
      minS: null,
      maxS: null
    });
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
    .setText(scalarBucket.label)
    .addTo(map);
  onMapPointClickRef.current({
    lat,
    lon,
    minS: scalarBucket.minS,
    maxS: scalarBucket.maxS
  });
  popupTimeoutRef.current = window.setTimeout(() => {
    tapPreviewActiveRef.current = false;
    popupRef.current?.remove();
    popupTimeoutRef.current = null;
  }, touchInteraction ? TOUCH_TAP_PREVIEW_MS : DESKTOP_CLICK_PREVIEW_MS);
}
