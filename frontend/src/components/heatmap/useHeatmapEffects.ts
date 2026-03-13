import { type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import type { CityMetadata, MultiPathItemResponse } from "@/lib/api";
import type { CursorPosition, InspectCardState, OriginPoint, ToastState } from "@/components/heatmap/types";
import { useHeatmapInspectEffects } from "@/components/heatmap/useHeatmapInspectEffects";
import { useHeatmapMetadataEffect } from "@/components/heatmap/useHeatmapMetadataEffect";
import { useHeatmapUiEffects } from "@/components/heatmap/useHeatmapUiEffects";

type SetState<T> = Dispatch<SetStateAction<T>>;

type InteractionMode = "inspect" | "add_origin_pending";

type UseHeatmapEffectsArgs = {
  origins: OriginPoint[];
  originsRef: MutableRefObject<OriginPoint[]>;
  inspectCard: InspectCardState | null;
  activeCityId: string | null;
  metadataLoading: boolean;
  onboardingOpen: boolean;
  interactionMode: InteractionMode;
  toast: ToastState | null;
  pathRequestSeqRef: MutableRefObject<number>;
  inspectAddressRequestSeqRef: MutableRefObject<number>;
  inspectAddressAbortControllerRef: MutableRefObject<AbortController | null>;
  runMultiPathQuery: (originsSnapshot: OriginPoint[], toLat: number, toLon: number) => Promise<void>;
  setCities: SetState<CityMetadata[]>;
  setActiveCityId: SetState<string | null>;
  setDefaultView: SetState<[number, number, number] | null>;
  setMapBbox: SetState<[number, number, number, number] | null>;
  setMetadataLoading: SetState<boolean>;
  setError: SetState<string | null>;
  setOnboardingOpen: SetState<boolean>;
  setInteractionMode: SetState<InteractionMode>;
  setCursorPosition: SetState<CursorPosition | null>;
  setToast: SetState<ToastState | null>;
  setPathLoading: SetState<boolean>;
  setPathError: SetState<string | null>;
  setPathByOriginId: SetState<Record<string, MultiPathItemResponse | null>>;
  setInspectAddressLabel: SetState<string | null>;
};

export function useHeatmapEffects(args: UseHeatmapEffectsArgs) {
  useHeatmapMetadataEffect({
    setCities: args.setCities,
    setActiveCityId: args.setActiveCityId,
    setDefaultView: args.setDefaultView,
    setMapBbox: args.setMapBbox,
    setMetadataLoading: args.setMetadataLoading,
    setError: args.setError
  });

  useHeatmapUiEffects({
    origins: args.origins,
    originsRef: args.originsRef,
    onboardingOpen: args.onboardingOpen,
    interactionMode: args.interactionMode,
    toast: args.toast,
    setOnboardingOpen: args.setOnboardingOpen,
    setInteractionMode: args.setInteractionMode,
    setCursorPosition: args.setCursorPosition,
    setToast: args.setToast
  });

  useHeatmapInspectEffects({
    inspectCard: args.inspectCard,
    activeCityId: args.activeCityId,
    metadataLoading: args.metadataLoading,
    originsRef: args.originsRef,
    pathRequestSeqRef: args.pathRequestSeqRef,
    inspectAddressRequestSeqRef: args.inspectAddressRequestSeqRef,
    inspectAddressAbortControllerRef: args.inspectAddressAbortControllerRef,
    runMultiPathQuery: args.runMultiPathQuery,
    setPathLoading: args.setPathLoading,
    setPathError: args.setPathError,
    setPathByOriginId: args.setPathByOriginId,
    setInspectAddressLabel: args.setInspectAddressLabel
  });
}
