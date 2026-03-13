import { type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import type { GeocodeResult, MultiPathItemResponse } from "@/lib/api";
import type { CursorPosition, InspectCardState, OnboardingOrigin, OriginPoint, ToastState } from "@/components/heatmap/types";
import { useOnboardingActions } from "@/components/heatmap/useOnboardingActions";
import { useOriginActions } from "@/components/heatmap/useOriginActions";

type SetState<T> = Dispatch<SetStateAction<T>>;

type InteractionMode = "inspect" | "add_origin_pending";

type UseHeatmapActionsArgs = {
  activeCityId: string | null;
  origins: OriginPoint[];
  onboardingOpen: boolean;
  onboardingOrigins: OnboardingOrigin[];
  interactionMode: InteractionMode;
  loading: boolean;
  metadataLoading: boolean;
  pathLoading: boolean;
  originsRef: MutableRefObject<OriginPoint[]>;
  nextOriginIndexRef: MutableRefObject<number>;
  nextOnboardingOriginIndexRef: MutableRefObject<number>;
  isochroneRequestSeqRef: MutableRefObject<number>;
  clearPathState: () => void;
  runMultiIsochroneQuery: (originsSnapshot: OriginPoint[]) => Promise<unknown>;
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

type HeatmapActions = {
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

export function useHeatmapActions(args: UseHeatmapActionsArgs): HeatmapActions {
  const {
    onMapPointClick,
    onAddOriginFromCoordinates,
    onStartAddOriginMode,
    onCancelAddOriginMode,
    onClearSelection,
    onRemoveOrigin
  } = useOriginActions(args);

  const {
    onAddOnboardingOrigin,
    onRemoveOnboardingOrigin,
    onConfirmOnboarding,
    onCloseOnboarding
  } = useOnboardingActions(args);

  async function onSelectAddressResult(result: GeocodeResult) {
    if (args.onboardingOpen) {
      onAddOnboardingOrigin(result);
      return;
    }

    const targetLat = Number(result.lat.toFixed(5));
    const targetLon = Number(result.lon.toFixed(5));
    args.resetSearch();
    await onAddOriginFromCoordinates(targetLat, targetLon, result.label);
  }

  return {
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
