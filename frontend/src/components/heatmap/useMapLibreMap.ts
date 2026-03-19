import { useEffect, useRef } from "react";
import type { Map as MapLibreMap, Marker as MapLibreMarker, Popup as MapLibrePopup } from "maplibre-gl";

import type { IsochroneScalarGrid, MultiPathItemResponse } from "@/lib/api";
import type { InspectCardState, OriginPoint } from "@/components/heatmap/types";
import type { TransitMapDebugHandle } from "@/components/heatmap/mapDebug";
import type { Locale } from "@/i18n/types";
import { buildOriginSourceData, buildPathSourceData } from "@/components/heatmap/maplibreData";
import { createMapLibreDebugHandle, setBoundsAndView } from "@/components/heatmap/maplibreDebug";
import {
  clearIsochronePopup,
  handleIsochroneHover,
  handleMapClick,
  updateInspectMarker
} from "@/components/heatmap/maplibreInteractions";
import { ORIGIN_SOURCE_ID, PATH_SOURCE_ID } from "@/components/heatmap/maplibreIds";
import {
  createBaseMapStyle,
  ensureHeatmapCanvasSourceAndLayer,
  ensureOverlaySourcesAndLayers,
  refreshHeatmapCanvasSource,
  updateGeoJsonSource
} from "@/components/heatmap/maplibreStyle";
import { buildScalarFieldTexture } from "@/components/heatmap/scalarGrid";
import { createWebglHeatmapCanvasRenderer } from "@/components/heatmap/webglHeatmapCanvas";

type UseMapLibreMapArgs = {
  locale: Locale;
  defaultView: [number, number, number] | null;
  maxBoundsBbox: [number, number, number, number] | null;
  scalarGrid: IsochroneScalarGrid | null | undefined;
  timeLabelFormatter: (seconds: number) => string;
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
  locale,
  defaultView,
  maxBoundsBbox,
  scalarGrid,
  timeLabelFormatter,
  origins,
  pathByOriginId,
  inspectCard,
  inspectAddressLabel,
  onMapPointClick
}: UseMapLibreMapArgs) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import("maplibre-gl") | null>(null);
  const timeLabelFormatterRef = useRef(timeLabelFormatter);
  const scalarGridRef = useRef(scalarGrid);
  const onMapPointClickRef = useRef(onMapPointClick);
  const originsRef = useRef(origins);
  const pathByOriginIdRef = useRef(pathByOriginId);
  const inspectCardRef = useRef(inspectCard);
  const inspectAddressLabelRef = useRef(inspectAddressLabel);
  const inspectMarkerRef = useRef<MapLibreMarker | null>(null);
  const inspectPopupRef = useRef<MapLibrePopup | null>(null);
  const isochronePopupRef = useRef<MapLibrePopup | null>(null);
  const isochronePopupTimeoutRef = useRef<number | null>(null);
  const isochroneTapPreviewActiveRef = useRef(false);
  const heatmapRendererRef = useRef<ReturnType<typeof createWebglHeatmapCanvasRenderer> | null>(null);
  const defaultLat = defaultView?.[0] ?? null;
  const defaultLon = defaultView?.[1] ?? null;
  const defaultZoom = defaultView?.[2] ?? null;
  const bboxMinLon = maxBoundsBbox?.[0] ?? null;
  const bboxMinLat = maxBoundsBbox?.[1] ?? null;
  const bboxMaxLon = maxBoundsBbox?.[2] ?? null;
  const bboxMaxLat = maxBoundsBbox?.[3] ?? null;

  useEffect(() => {
    timeLabelFormatterRef.current = timeLabelFormatter;
  }, [timeLabelFormatter]);

  useEffect(() => {
    scalarGridRef.current = scalarGrid;
  }, [scalarGrid]);

  useEffect(() => {
    onMapPointClickRef.current = onMapPointClick;
  }, [onMapPointClick]);

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
        style: createBaseMapStyle(locale),
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
        map.on("mousemove", (event) => {
          handleIsochroneHover(
            maplibregl,
            map,
            timeLabelFormatterRef,
            scalarGridRef,
            isochronePopupRef,
            isochronePopupTimeoutRef,
            isochroneTapPreviewActiveRef,
            event
          );
        });
        map.on("mouseout", () => {
          if (isochroneTapPreviewActiveRef.current) {
            return;
          }
          clearIsochronePopup(
            isochronePopupRef,
            isochronePopupTimeoutRef,
            isochroneTapPreviewActiveRef
          );
        });
        const initialField = buildScalarFieldTexture(scalarGridRef.current);
        const heatmapRenderer = createWebglHeatmapCanvasRenderer(initialField);
        heatmapRendererRef.current = heatmapRenderer;
        const initialBounds = heatmapRenderer.getBounds();
        if (initialBounds) {
          ensureHeatmapCanvasSourceAndLayer(map, heatmapRenderer.getCanvas(), initialBounds);
          refreshHeatmapCanvasSource(map);
        }
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
          timeLabelFormatterRef,
          scalarGridRef,
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
      heatmapRendererRef.current?.destroy();
      heatmapRendererRef.current = null;
      mapInstanceRef.current?.remove();
      mapInstanceRef.current = null;
      maplibreRef.current = null;
      if (typeof window !== "undefined") {
        window.__transitMap = undefined;
      }
    };
  }, [locale, defaultLat, defaultLon, defaultZoom, bboxMinLon, bboxMinLat, bboxMaxLon, bboxMaxLat]);

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
    const renderer = heatmapRendererRef.current;
    if (!map || !renderer) {
      return;
    }
    renderer.setField(buildScalarFieldTexture(scalarGrid));
    const bounds = renderer.getBounds();
    if (bounds) {
      ensureHeatmapCanvasSourceAndLayer(map, renderer.getCanvas(), bounds);
      refreshHeatmapCanvasSource(map);
    }
  }, [scalarGrid]);

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
