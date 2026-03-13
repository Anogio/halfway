import type { Map as MapLibreMap } from "maplibre-gl";
import type { MutableRefObject } from "react";

import type { TransitMapDebugHandle } from "@/components/heatmap/mapDebug";
import { DEBUG_LAYER_IDS, DEBUG_SOURCE_IDS } from "@/components/heatmap/maplibreIds";
import type { InspectCardState } from "@/components/heatmap/types";

export function createMapLibreDebugHandle(
  map: MapLibreMap,
  inspectCardRef: MutableRefObject<InspectCardState | null>,
  inspectAddressLabelRef: MutableRefObject<string | null>
): TransitMapDebugHandle {
  return {
    getSize() {
      const canvas = map.getCanvas();
      return { x: canvas.clientWidth, y: canvas.clientHeight };
    },
    containerPointToLatLng([x, y]) {
      const lngLat = map.unproject([x, y]);
      return { lat: lngLat.lat, lng: lngLat.lng };
    },
    fire(type, payload) {
      if (type !== "click") {
        return;
      }
      const point = map.project([payload.latlng.lng, payload.latlng.lat]);
      const canvas = map.getCanvas();
      map.fire("click", {
        lngLat: payload.latlng,
        point,
        target: map,
        originalEvent: {
          type: "click",
          target: canvas,
          currentTarget: canvas
        }
      });
    },
    getSourceFeatureCount(sourceName) {
      const source = map.getSource(DEBUG_SOURCE_IDS[sourceName]) as
        | { _data?: { features?: unknown[] } }
        | undefined;
      const features = source?._data?.features;
      return Array.isArray(features) ? features.length : null;
    },
    getRenderedFeatureCount(layerName, point) {
      const layers = [DEBUG_LAYER_IDS[layerName]];
      const features = point
        ? map.queryRenderedFeatures(point, { layers })
        : map.queryRenderedFeatures({ layers });
      return features.length;
    },
    getInspectDebug() {
      const markerNode = document.querySelector(".arrival-point-marker");
      const popupNode = document.querySelector(".maplibregl-popup.arrival-point-tooltip-popup");
      return {
        inspectCard: inspectCardRef.current,
        inspectAddressLabel: inspectAddressLabelRef.current,
        markerAttached: Boolean(markerNode),
        popupAttached: Boolean(popupNode)
      };
    }
  };
}

export function setBoundsAndView(
  map: MapLibreMap,
  defaultView: [number, number, number],
  maxBoundsBbox: [number, number, number, number]
) {
  const [minLon, minLat, maxLon, maxLat] = maxBoundsBbox;
  const bounds: [[number, number], [number, number]] = [
    [minLon, minLat],
    [maxLon, maxLat]
  ];
  map.setMaxBounds(bounds);
  const camera = map.cameraForBounds(bounds, { padding: 24 });
  if (camera?.zoom !== undefined) {
    map.setMinZoom(camera.zoom);
  }
  map.jumpTo({
    center: [defaultView[1], defaultView[0]],
    zoom: defaultView[2]
  });
}
