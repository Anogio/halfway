import { type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import { fetchReverseGeocode, type MultiIsochroneResponse, type MultiPathItemResponse } from "@/lib/api";
import { MAX_ORIGINS, ORIGIN_COLORS } from "@/components/heatmap/constants";
import type { CursorPosition, InspectCardState, OnboardingOrigin, OriginPoint, ToastState } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type SetState<T> = Dispatch<SetStateAction<T>>;

type InteractionMode = "inspect" | "add_origin_pending";

type UseOriginActionsArgs = {
  activeCityId: string | null;
  origins: OriginPoint[];
  onboardingOpen: boolean;
  interactionMode: InteractionMode;
  loading: boolean;
  metadataLoading: boolean;
  pathLoading: boolean;
  originsRef: MutableRefObject<OriginPoint[]>;
  nextOriginIndexRef: MutableRefObject<number>;
  isochroneRequestSeqRef: MutableRefObject<number>;
  clearPathState: () => void;
  runMultiIsochroneQuery: (originsSnapshot: OriginPoint[]) => Promise<MultiIsochroneResponse | null>;
  resetSearch: () => void;
  setSearchOpen: (open: boolean) => void;
  setOrigins: SetState<OriginPoint[]>;
  setData: SetState<import("@/lib/api").MultiIsochroneResponse | null>;
  setError: SetState<string | null>;
  setToast: SetState<ToastState | null>;
  setInspectCard: SetState<InspectCardState | null>;
  setPathByOriginId: SetState<Record<string, MultiPathItemResponse | null>>;
  setOnboardingOpen: SetState<boolean>;
  setOnboardingOrigins: SetState<OnboardingOrigin[]>;
  setInteractionMode: SetState<InteractionMode>;
  setCursorPosition: SetState<CursorPosition | null>;
};

type OriginActions = {
  onAddOriginFromCoordinates: (latValue: number, lonValue: number, customLabel?: string) => Promise<void>;
  onMapPointClick: (point: InspectCardState) => void;
  onStartAddOriginMode: () => void;
  onCancelAddOriginMode: () => void;
  onRemoveOrigin: (originId: string) => Promise<void>;
  onClearSelection: () => void;
};

export function useOriginActions({
  activeCityId,
  origins,
  onboardingOpen,
  interactionMode,
  loading,
  metadataLoading,
  pathLoading,
  originsRef,
  nextOriginIndexRef,
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
}: UseOriginActionsArgs): OriginActions {
  const { messages } = useI18n();

  function resolveManualOriginLabelAsync(
    originId: string,
    latValue: number,
    lonValue: number,
    pendingLabel: string,
    unresolvedLabel: string
  ) {
    if (!activeCityId) {
      return;
    }
    void (async () => {
      try {
        const resolved = await fetchReverseGeocode(activeCityId, latValue, lonValue);
        if (!resolved || resolved === unresolvedLabel) {
          return;
        }

        setOrigins((prev) => {
          const targetIndex = prev.findIndex((origin) => origin.id === originId);
          if (targetIndex < 0) {
            return prev;
          }
          const targetOrigin = prev[targetIndex];
          if (!targetOrigin.labelPending || targetOrigin.label !== pendingLabel) {
            return prev;
          }

          const next = [...prev];
          next[targetIndex] = {
            ...targetOrigin,
            label: resolved,
            labelPending: false
          };
          return next;
        });
      } catch {
        setOrigins((prev) => {
          const targetIndex = prev.findIndex((origin) => origin.id === originId);
          if (targetIndex < 0) {
            return prev;
          }
          const targetOrigin = prev[targetIndex];
          if (!targetOrigin.labelPending || targetOrigin.label !== pendingLabel) {
            return prev;
          }

          const next = [...prev];
          next[targetIndex] = {
            ...targetOrigin,
            label: unresolvedLabel,
            labelPending: false
          };
          return next;
        });
      }
    })();
  }

  async function onAddOriginFromCoordinates(latValue: number, lonValue: number, customLabel?: string) {
    const currentOrigins = originsRef.current;
    if (currentOrigins.length >= MAX_ORIGINS) {
      setToast({ kind: "error", text: messages.toasts.pointLimitReached(MAX_ORIGINS) });
      return;
    }

    const idx = nextOriginIndexRef.current;
    nextOriginIndexRef.current += 1;
    const lat = Number(latValue.toFixed(5));
    const lon = Number(lonValue.toFixed(5));
    const originId = `origin-${idx}`;
    const normalizedCustomLabel = customLabel?.trim() ?? "";
    const pendingLabel = messages.status.loadingAddress;
    const unresolvedLabel = messages.status.selectedPoint;
    const label = normalizedCustomLabel || pendingLabel;

    const newOrigin: OriginPoint = {
      id: originId,
      label,
      labelPending: !normalizedCustomLabel,
      lat,
      lon,
      color: ORIGIN_COLORS[(idx - 1) % ORIGIN_COLORS.length]
    };

    const nextOrigins = [...currentOrigins, newOrigin];
    setOrigins(nextOrigins);
    setInspectCard(null);
    clearPathState();
    const isochronePromise = runMultiIsochroneQuery(nextOrigins);
    if (!normalizedCustomLabel) {
      resolveManualOriginLabelAsync(originId, lat, lon, pendingLabel, unresolvedLabel);
    }
    await isochronePromise;
  }

  function onMapPointClick(point: InspectCardState) {
    if (onboardingOpen) {
      return;
    }
    if (interactionMode === "add_origin_pending") {
      setInteractionMode("inspect");
      setCursorPosition(null);
      void onAddOriginFromCoordinates(point.lat, point.lon);
      return;
    }
    setInspectCard(point);
  }

  function onStartAddOriginMode() {
    if (loading || pathLoading || metadataLoading || origins.length >= MAX_ORIGINS) {
      return;
    }
    setInteractionMode("add_origin_pending");
    setInspectCard(null);
    setCursorPosition(null);
    setSearchOpen(false);
  }

  function onCancelAddOriginMode() {
    setInteractionMode("inspect");
    setCursorPosition(null);
  }

  async function onRemoveOrigin(originId: string) {
    const nextOrigins = originsRef.current.filter((origin) => origin.id !== originId);
    setOrigins(nextOrigins);
    setPathByOriginId((prev) => {
      const next = { ...prev };
      delete next[originId];
      return next;
    });
    clearPathState();

    if (nextOrigins.length === 0) {
      setData(null);
      return;
    }

    await runMultiIsochroneQuery(nextOrigins);
  }

  function onClearSelection() {
    isochroneRequestSeqRef.current += 1;
    clearPathState();
    setInteractionMode("inspect");
    setCursorPosition(null);
    setOrigins([]);
    setInspectCard(null);
    setData(null);
    setError(null);
    setOnboardingOrigins([]);
    resetSearch();
    setOnboardingOpen(false);
  }

  return {
    onAddOriginFromCoordinates,
    onMapPointClick,
    onStartAddOriginMode,
    onCancelAddOriginMode,
    onRemoveOrigin,
    onClearSelection
  };
}
