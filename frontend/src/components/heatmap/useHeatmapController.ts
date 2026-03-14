import { useCallback, useEffect, useRef, useState } from "react";

import {
  fetchWakeup,
  type CityMetadata,
  type GeocodeResult,
  type MultiIsochroneResponse,
  type MultiPathItemResponse
} from "@/lib/api";
import { MAX_ORIGINS, SEARCH_MIN_CHARS } from "@/components/heatmap/constants";
import { isOnboardingSkippedByQuery } from "@/components/heatmap/queryParams";
import type {
  CursorPosition,
  InspectCardState,
  OnboardingOrigin,
  OriginPoint,
  ToastState
} from "@/components/heatmap/types";
import { useGeocodeSearch } from "@/components/heatmap/useGeocodeSearch";
import { useHeatmapActions } from "@/components/heatmap/useHeatmapActions";
import { useHeatmapEffects } from "@/components/heatmap/useHeatmapEffects";
import { useHeatmapQueries } from "@/components/heatmap/useHeatmapQueries";

type InteractionMode = "inspect" | "add_origin_pending";

type HeatmapController = {
  cities: CityMetadata[];
  activeCityId: string | null;
  defaultView: [number, number, number] | null;
  mapBbox: [number, number, number, number] | null;
  metadataLoading: boolean;
  origins: OriginPoint[];
  data: MultiIsochroneResponse | null;
  loading: boolean;
  error: string | null;
  toast: ToastState | null;
  inspectCard: InspectCardState | null;
  inspectAddressLabel: string | null;
  pathLoading: boolean;
  pathError: string | null;
  pathByOriginId: Record<string, MultiPathItemResponse | null>;
  onboardingOpen: boolean;
  citySelectionRequired: boolean;
  onboardingOrigins: OnboardingOrigin[];
  cursorPosition: CursorPosition | null;
  addModeActive: boolean;
  addModeBlocked: boolean;
  mapSearchResultsDisabled: boolean;
  showInspectDock: boolean;
  showCursorCrosshair: boolean;
  searchQuery: string;
  setSearchQuery: (value: string) => void;
  searchResults: GeocodeResult[];
  searchLoading: boolean;
  searchError: string | null;
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;
  onSelectCity: (cityId: string) => void;
  onMapPointClick: (point: InspectCardState) => void;
  onSelectAddressResult: (result: GeocodeResult) => Promise<void>;
  onRemoveOnboardingOrigin: (originId: string) => void;
  onConfirmOnboarding: () => Promise<void>;
  onCloseOnboarding: () => void;
  onStartAddOriginMode: () => void;
  onCancelAddOriginMode: () => void;
  onClearSelection: () => void;
  onRemoveOrigin: (originId: string) => Promise<void>;
};

export function useHeatmapController(): HeatmapController {
  const inspectAddressRequestSeqRef = useRef(0);
  const inspectAddressAbortControllerRef = useRef<AbortController | null>(null);

  const originsRef = useRef<OriginPoint[]>([]);

  const nextOriginIndexRef = useRef(1);
  const nextOnboardingOriginIndexRef = useRef(1);

  const [cities, setCities] = useState<CityMetadata[]>([]);
  const [activeCityId, setActiveCityId] = useState<string | null>(null);
  const [defaultView, setDefaultView] = useState<[number, number, number] | null>(null);
  const [mapBbox, setMapBbox] = useState<[number, number, number, number] | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(true);

  const [origins, setOrigins] = useState<OriginPoint[]>([]);
  const [data, setData] = useState<MultiIsochroneResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);

  const [inspectCard, setInspectCard] = useState<InspectCardState | null>(null);
  const [inspectAddressLabel, setInspectAddressLabel] = useState<string | null>(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);
  const [pathByOriginId, setPathByOriginId] = useState<Record<string, MultiPathItemResponse | null>>({});

  const [onboardingOpen, setOnboardingOpen] = useState(true);
  const [onboardingOrigins, setOnboardingOrigins] = useState<OnboardingOrigin[]>([]);
  const [interactionMode, setInteractionMode] = useState<InteractionMode>("inspect");
  const [cursorPosition, setCursorPosition] = useState<CursorPosition | null>(null);

  const { pathRequestSeqRef, isochroneRequestSeqRef, clearPathState, runMultiIsochroneQuery, runMultiPathQuery } =
    useHeatmapQueries({
      activeCityId,
      setData,
      setLoading,
      setError,
      setToast,
      setInspectCard,
      setPathLoading,
      setPathError,
      setPathByOriginId
    });

  const {
    searchQuery,
    setSearchQuery,
    searchResults,
    searchLoading,
    searchError,
    searchOpen,
    setSearchOpen,
    resetSearch
  } = useGeocodeSearch(activeCityId, SEARCH_MIN_CHARS);

  const citySelectionRequired = activeCityId === null;

  const onSelectCity = useCallback((cityId: string) => {
    const normalizedCityId = cityId.trim();
    if (!normalizedCityId) {
      return;
    }
    if (activeCityId === normalizedCityId && !citySelectionRequired) {
      return;
    }

    const nextCity = cities.find((city) => city.id === normalizedCityId);
    if (!nextCity) {
      return;
    }

    isochroneRequestSeqRef.current += 1;
    inspectAddressAbortControllerRef.current?.abort();
    inspectAddressAbortControllerRef.current = null;
    inspectAddressRequestSeqRef.current += 1;
    nextOriginIndexRef.current = 1;
    nextOnboardingOriginIndexRef.current = 1;
    originsRef.current = [];

    setInteractionMode("inspect");
    setCursorPosition(null);
    setInspectCard(null);
    setInspectAddressLabel(null);
    setOrigins([]);
    setOnboardingOrigins([]);
    setData(null);
    setLoading(false);
    setError(null);
    setToast(null);
    clearPathState();
    resetSearch();

    setActiveCityId(nextCity.id);
    setDefaultView([
      Number(nextCity.default_view[0]),
      Number(nextCity.default_view[1]),
      Number(nextCity.default_view[2])
    ]);
    setMapBbox([
      Number(nextCity.bbox[0]),
      Number(nextCity.bbox[1]),
      Number(nextCity.bbox[2]),
      Number(nextCity.bbox[3])
    ]);
    setOnboardingOpen(!isOnboardingSkippedByQuery());
  }, [
    activeCityId,
    cities,
    citySelectionRequired,
    clearPathState,
    inspectAddressAbortControllerRef,
    inspectAddressRequestSeqRef,
    isochroneRequestSeqRef,
    nextOnboardingOriginIndexRef,
    nextOriginIndexRef,
    originsRef,
    resetSearch
  ]);

  useEffect(() => {
    if (!activeCityId) {
      return;
    }
    void fetchWakeup(activeCityId).catch(() => {});
  }, [activeCityId]);

  useHeatmapEffects({
    origins,
    originsRef,
    inspectCard,
    activeCityId,
    metadataLoading,
    onboardingOpen,
    interactionMode,
    toast,
    pathRequestSeqRef,
    inspectAddressRequestSeqRef,
    inspectAddressAbortControllerRef,
    runMultiPathQuery,
    setCities,
    setActiveCityId,
    setDefaultView,
    setMapBbox,
    setMetadataLoading,
    setError,
    setOnboardingOpen,
    setInteractionMode,
    setCursorPosition,
    setToast,
    setPathLoading,
    setPathError,
    setPathByOriginId,
    setInspectAddressLabel
  });

  const {
    onMapPointClick,
    onSelectAddressResult,
    onRemoveOnboardingOrigin,
    onConfirmOnboarding,
    onCloseOnboarding,
    onStartAddOriginMode,
    onCancelAddOriginMode,
    onClearSelection,
    onRemoveOrigin
  } = useHeatmapActions({
    activeCityId,
    origins,
    onboardingOpen,
    onboardingOrigins,
    interactionMode,
    loading,
    metadataLoading,
    pathLoading,
    originsRef,
    nextOriginIndexRef,
    nextOnboardingOriginIndexRef,
    isochroneRequestSeqRef,
    clearPathState,
    runMultiIsochroneQuery,
    resetSearch,
    setSearchOpen,
    setOrigins,
    setData,
    setError,
    setToast,
    setInspectCard,
    setPathByOriginId,
    setOnboardingOpen,
    setOnboardingOrigins,
    setInteractionMode,
    setCursorPosition
  });

  const addModeActive = interactionMode === "add_origin_pending" && !onboardingOpen;
  const addModeBlocked = citySelectionRequired || loading || pathLoading || metadataLoading || origins.length >= MAX_ORIGINS;
  const mapSearchResultsDisabled =
    citySelectionRequired || loading || metadataLoading || pathLoading || origins.length >= MAX_ORIGINS;
  const showInspectDock = !onboardingOpen && !citySelectionRequired;
  const showCursorCrosshair = addModeActive && Boolean(cursorPosition);

  return {
    cities,
    activeCityId,
    defaultView,
    mapBbox,
    metadataLoading,
    origins,
    data,
    loading,
    error,
    toast,
    inspectCard,
    inspectAddressLabel,
    pathLoading,
    pathError,
    pathByOriginId,
    onboardingOpen,
    citySelectionRequired,
    onboardingOrigins,
    cursorPosition,
    addModeActive,
    addModeBlocked,
    mapSearchResultsDisabled,
    showInspectDock,
    showCursorCrosshair,
    searchQuery,
    setSearchQuery,
    searchResults,
    searchLoading,
    searchError,
    searchOpen,
    setSearchOpen,
    onSelectCity,
    onMapPointClick,
    onSelectAddressResult,
    onRemoveOnboardingOrigin,
    onConfirmOnboarding,
    onCloseOnboarding,
    onStartAddOriginMode,
    onCancelAddOriginMode,
    onClearSelection,
    onRemoveOrigin
  };
}
