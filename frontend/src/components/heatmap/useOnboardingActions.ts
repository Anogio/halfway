import { type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import type { GeocodeResult, MultiIsochroneResponse } from "@/lib/api";
import { MAX_ORIGINS, ORIGIN_COLORS } from "@/components/heatmap/constants";
import type { CursorPosition, OnboardingOrigin, OriginPoint, ToastState } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type SetState<T> = Dispatch<SetStateAction<T>>;

type InteractionMode = "inspect" | "add_origin_pending";

type UseOnboardingActionsArgs = {
  onboardingOrigins: OnboardingOrigin[];
  originsRef: MutableRefObject<OriginPoint[]>;
  nextOriginIndexRef: MutableRefObject<number>;
  nextOnboardingOriginIndexRef: MutableRefObject<number>;
  clearPathState: () => void;
  runMultiIsochroneQuery: (originsSnapshot: OriginPoint[]) => Promise<MultiIsochroneResponse | null>;
  resetSearch: () => void;
  setToast: SetState<ToastState | null>;
  setOrigins: SetState<OriginPoint[]>;
  setInspectCard: SetState<import("@/components/heatmap/types").InspectCardState | null>;
  setOnboardingOpen: SetState<boolean>;
  setOnboardingOrigins: SetState<OnboardingOrigin[]>;
  setOnboardingSubmitting: SetState<boolean>;
  setInteractionMode: SetState<InteractionMode>;
  setCursorPosition: SetState<CursorPosition | null>;
};

type OnboardingActions = {
  onAddOnboardingOrigin: (result: GeocodeResult) => void;
  onRemoveOnboardingOrigin: (originId: string) => void;
  onCloseOnboarding: () => void;
  onConfirmOnboarding: () => Promise<void>;
};

export function useOnboardingActions({
  onboardingOrigins,
  originsRef,
  nextOriginIndexRef,
  nextOnboardingOriginIndexRef,
  clearPathState,
  runMultiIsochroneQuery,
  resetSearch,
  setToast,
  setOrigins,
  setInspectCard,
  setOnboardingOpen,
  setOnboardingOrigins,
  setOnboardingSubmitting,
  setInteractionMode,
  setCursorPosition
}: UseOnboardingActionsArgs): OnboardingActions {
  const { messages } = useI18n();

  function onAddOnboardingOrigin(result: GeocodeResult) {
    if (onboardingOrigins.length >= MAX_ORIGINS) {
      setToast({ kind: "error", text: messages.toasts.pointLimitReached(MAX_ORIGINS) });
      return;
    }

    const lat = Number(result.lat.toFixed(5));
    const lon = Number(result.lon.toFixed(5));
    const pointLabel = result.label.trim();

    const alreadySelected = onboardingOrigins.some(
      (origin) => origin.lat === lat && origin.lon === lon && origin.label === pointLabel
    );
    if (alreadySelected) {
      return;
    }

    const idx = nextOnboardingOriginIndexRef.current;
    nextOnboardingOriginIndexRef.current += 1;
    setOnboardingOrigins((prev) => [
      ...prev,
      {
        id: `onboarding-origin-${idx}`,
        label: pointLabel,
        lat,
        lon
      }
    ]);
    resetSearch();
  }

  function onRemoveOnboardingOrigin(originId: string) {
    setOnboardingOrigins((prev) => prev.filter((origin) => origin.id !== originId));
  }

  function onCloseOnboarding() {
    resetSearch();
    setInteractionMode("inspect");
    setCursorPosition(null);
    setOnboardingOpen(false);
  }

  async function onConfirmOnboarding() {
    if (onboardingOrigins.length === 0) {
      return;
    }

    const startIndex = nextOriginIndexRef.current;
    const nextOrigins: OriginPoint[] = onboardingOrigins.map((origin, offset) => {
      const idx = startIndex + offset;
      return {
        id: `origin-${idx}`,
        label: origin.label,
        lat: origin.lat,
        lon: origin.lon,
        color: ORIGIN_COLORS[(idx - 1) % ORIGIN_COLORS.length]
      };
    });

    setOnboardingSubmitting(true);
    setInteractionMode("inspect");
    setCursorPosition(null);
    setInspectCard(null);

    try {
      const response = await runMultiIsochroneQuery(nextOrigins);
      if (!response) {
        return;
      }

      nextOriginIndexRef.current = startIndex + onboardingOrigins.length;
      originsRef.current = nextOrigins;
      setOrigins(nextOrigins);
      clearPathState();
      setOnboardingOpen(false);
      setOnboardingOrigins([]);
      resetSearch();
    } finally {
      setOnboardingSubmitting(false);
    }
  }

  return {
    onAddOnboardingOrigin,
    onRemoveOnboardingOrigin,
    onCloseOnboarding,
    onConfirmOnboarding
  };
}
