import { useEffect, useRef } from "react";
import type { Map as MapLibreMap, Marker as MapLibreMarker, Popup as MapLibrePopup } from "maplibre-gl";

import type { MultiPathItemResponse } from "@/lib/api";
import type { InspectCardState, OriginPoint } from "@/components/heatmap/types";
import type { TransitMapDebugHandle } from "@/components/heatmap/mapDebug";
import {
  buildIsochroneSourceData,
  buildOriginSourceData,
  buildPathSourceData
} from "@/components/heatmap/maplibreData";
import { createMapLibreDebugHandle, setBoundsAndView } from "@/components/heatmap/maplibreDebug";
import {
  clearIsochronePopup,
  handleIsochroneHover,
  handleMapClick,
  updateInspectMarker
} from "@/components/heatmap/maplibreInteractions";
import {
  ISOCHRONE_FILL_LAYER_ID,
  ISOCHRONE_SOURCE_ID,
  ORIGIN_SOURCE_ID,
  PATH_SOURCE_ID
} from "@/components/heatmap/maplibreIds";
import {
  createRasterStyle,
  ensureOverlaySourcesAndLayers,
  updateGeoJsonSource
} from "@/components/heatmap/maplibreStyle";

type UseMapLibreMapArgs = {
  defaultView: [number, number, number] | null;
  maxBoundsBbox: [number, number, number, number] | null;
  displayFeatureCollection: unknown;
  bucketLabelFormatter: (minMinutes: number, maxMinutes: number) => string;
  origins: OriginPoint[];
  pathByOriginId: Record<string, MultiPathItemResponse | null>;
  inspectCard: InspectCardState | null;
  inspectAddressLabel: string | null;
  onMapPointClick: (point: InspectCardState) => void;
};

declare global {
  interface Window {
    __transitMap?: TransitMapDebugHandle;
  }
}

export function useMapLibreMap({
  defaultView,
  maxBoundsBbox,
  displayFeatureCollection,
  bucketLabelFormatter,
  origins,
  pathByOriginId,
  inspectCard,
  inspectAddressLabel,
  onMapPointClick
}: UseMapLibreMapArgs) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import("maplibre-gl") | null>(null);
  const bucketLabelFormatterRef = useRef(bucketLabelFormatter);
  const onMapPointClickRef = useRef(onMapPointClick);
  const displayFeatureCollectionRef = useRef(displayFeatureCollection);
  const originsRef = useRef(origins);
  const pathByOriginIdRef = useRef(pathByOriginId);
  const inspectCardRef = useRef(inspectCard);
  const inspectAddressLabelRef = useRef(inspectAddressLabel);
  const inspectMarkerRef = useRef<MapLibreMarker | null>(null);
  const inspectPopupRef = useRef<MapLibrePopup | null>(null);
  const isochronePopupRef = useRef<MapLibrePopup | null>(null);
  const isochronePopupTimeoutRef = useRef<number | null>(null);
  const isochroneTapPreviewActiveRef = useRef(false);
  const defaultLat = defaultView?.[0] ?? null;
  const defaultLon = defaultView?.[1] ?? null;
  const defaultZoom = defaultView?.[2] ?? null;
  const bboxMinLon = maxBoundsBbox?.[0] ?? null;
  const bboxMinLat = maxBoundsBbox?.[1] ?? null;
  const bboxMaxLon = maxBoundsBbox?.[2] ?? null;
  const bboxMaxLat = maxBoundsBbox?.[3] ?? null;

  useEffect(() => {
    bucketLabelFormatterRef.current = bucketLabelFormatter;
  }, [bucketLabelFormatter]);

  useEffect(() => {
    onMapPointClickRef.current = onMapPointClick;
  }, [onMapPointClick]);

  useEffect(() => {
    displayFeatureCollectionRef.current = displayFeatureCollection;
  }, [displayFeatureCollection]);

  useEffect(() => {
    originsRef.current = origins;
  }, [origins]);

  useEffect(() => {
    pathByOriginIdRef.current = pathByOriginId;
  }, [pathByOriginId]);

  useEffect(() => {
    inspectCardRef.current = inspectCard;
  }, [inspectCard]);

  useEffect(() => {
    inspectAddressLabelRef.current = inspectAddressLabel;
  }, [inspectAddressLabel]);

  useEffect(() => {
    let mounted = true;

    async function initMap() {
      if (
        defaultLat === null ||
        defaultLon === null ||
        defaultZoom === null ||
        bboxMinLon === null ||
        bboxMinLat === null ||
        bboxMaxLon === null ||
        bboxMaxLat === null ||
        !mapRef.current ||
        mapInstanceRef.current
      ) {
        return;
      }
      const defaultViewTuple: [number, number, number] = [defaultLat, defaultLon, defaultZoom];
      const maxBoundsTuple: [number, number, number, number] = [
        bboxMinLon,
        bboxMinLat,
        bboxMaxLon,
        bboxMaxLat
      ];

      const maplibregl = await import("maplibre-gl");
      if (!mounted || !mapRef.current || mapInstanceRef.current) {
        return;
      }

      const map = new maplibregl.Map({
        container: mapRef.current,
        style: createRasterStyle(),
        center: [defaultViewTuple[1], defaultViewTuple[0]],
        zoom: defaultViewTuple[2]
      });
      map.dragRotate.disable();
      map.touchZoomRotate.disableRotation();

      map.on("load", () => {
        if (!mounted) {
          return;
        }
        ensureOverlaySourcesAndLayers(map);
        setBoundsAndView(map, defaultViewTuple, maxBoundsTuple);
        map.on("mouseenter", ISOCHRONE_FILL_LAYER_ID, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mousemove", ISOCHRONE_FILL_LAYER_ID, (event) => {
          handleIsochroneHover(
            maplibregl,
            map,
            bucketLabelFormatterRef,
            isochronePopupRef,
            isochronePopupTimeoutRef,
            isochroneTapPreviewActiveRef,
            event
          );
        });
        map.on("mouseleave", ISOCHRONE_FILL_LAYER_ID, () => {
          map.getCanvas().style.cursor = "";
          if (isochroneTapPreviewActiveRef.current) {
            return;
          }
          clearIsochronePopup(
            isochronePopupRef,
            isochronePopupTimeoutRef,
            isochroneTapPreviewActiveRef
          );
        });
        updateGeoJsonSource(
          map,
          ISOCHRONE_SOURCE_ID,
          buildIsochroneSourceData(displayFeatureCollectionRef.current)
        );
        updateGeoJsonSource(
          map,
          PATH_SOURCE_ID,
          buildPathSourceData(originsRef.current, pathByOriginIdRef.current)
        );
        updateGeoJsonSource(map, ORIGIN_SOURCE_ID, buildOriginSourceData(originsRef.current));
        updateInspectMarker(
          maplibregl,
          map,
          inspectMarkerRef,
          inspectPopupRef,
          inspectCardRef.current,
          inspectAddressLabelRef.current
        );
      });

      map.on("click", (event) => {
        handleMapClick(
          maplibregl,
          map,
          bucketLabelFormatterRef,
          isochronePopupRef,
          isochronePopupTimeoutRef,
          isochroneTapPreviewActiveRef,
          onMapPointClickRef,
          event
        );
      });

      maplibreRef.current = maplibregl;
      mapInstanceRef.current = map;
      if (typeof window !== "undefined") {
        window.__transitMap = createMapLibreDebugHandle(
          map,
          inspectCardRef,
          inspectAddressLabelRef
        );
      }
    }

    void initMap();

    return () => {
      mounted = false;
      clearIsochronePopup(
        isochronePopupRef,
        isochronePopupTimeoutRef,
        isochroneTapPreviewActiveRef
      );
      isochronePopupRef.current = null;
      inspectPopupRef.current?.remove();
      inspectPopupRef.current = null;
      inspectMarkerRef.current?.remove();
      inspectMarkerRef.current = null;
      mapInstanceRef.current?.remove();
      mapInstanceRef.current = null;
      maplibreRef.current = null;
      if (typeof window !== "undefined") {
        window.__transitMap = undefined;
      }
    };
  }, [defaultLat, defaultLon, defaultZoom, bboxMinLon, bboxMinLat, bboxMaxLon, bboxMaxLat]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (
      !map ||
      defaultLat === null ||
      defaultLon === null ||
      defaultZoom === null ||
      bboxMinLon === null ||
      bboxMinLat === null ||
      bboxMaxLon === null ||
      bboxMaxLat === null
    ) {
      return;
    }
    setBoundsAndView(
      map,
      [defaultLat, defaultLon, defaultZoom],
      [bboxMinLon, bboxMinLat, bboxMaxLon, bboxMaxLat]
    );
  }, [defaultLat, defaultLon, defaultZoom, bboxMinLon, bboxMinLat, bboxMaxLon, bboxMaxLat]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) {
      return;
    }
    updateGeoJsonSource(map, ISOCHRONE_SOURCE_ID, buildIsochroneSourceData(displayFeatureCollection));
  }, [displayFeatureCollection]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) {
      return;
    }
    updateGeoJsonSource(map, PATH_SOURCE_ID, buildPathSourceData(origins, pathByOriginId));
  }, [origins, pathByOriginId]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) {
      return;
    }
    updateGeoJsonSource(map, ORIGIN_SOURCE_ID, buildOriginSourceData(origins));
  }, [origins]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    const maplibregl = maplibreRef.current;
    if (!map || !maplibregl) {
      return;
    }
    updateInspectMarker(
      maplibregl,
      map,
      inspectMarkerRef,
      inspectPopupRef,
      inspectCard,
      inspectAddressLabel
    );
  }, [inspectCard, inspectAddressLabel]);

  return {
    mapRef
  };
}
