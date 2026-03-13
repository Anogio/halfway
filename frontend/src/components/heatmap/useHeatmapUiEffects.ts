import { useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import { MAX_ORIGINS } from "@/components/heatmap/constants";
import { isOnboardingSkippedByQuery } from "@/components/heatmap/queryParams";
import type { CursorPosition, OriginPoint, ToastState } from "@/components/heatmap/types";

type SetState<T> = Dispatch<SetStateAction<T>>;

type InteractionMode = "inspect" | "add_origin_pending";

type UseHeatmapUiEffectsArgs = {
  origins: OriginPoint[];
  originsRef: MutableRefObject<OriginPoint[]>;
  onboardingOpen: boolean;
  interactionMode: InteractionMode;
  toast: ToastState | null;
  setOnboardingOpen: SetState<boolean>;
  setInteractionMode: SetState<InteractionMode>;
  setCursorPosition: SetState<CursorPosition | null>;
  setToast: SetState<ToastState | null>;
};

export function useHeatmapUiEffects({
  origins,
  originsRef,
  onboardingOpen,
  interactionMode,
  toast,
  setOnboardingOpen,
  setInteractionMode,
  setCursorPosition,
  setToast
}: UseHeatmapUiEffectsArgs) {
  useEffect(() => {
    originsRef.current = origins;
  }, [origins, originsRef]);

  useEffect(() => {
    if (isOnboardingSkippedByQuery()) {
      setOnboardingOpen(false);
    }
  }, [setOnboardingOpen]);

  useEffect(() => {
    if (!toast) {
      return;
    }
    const timer = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(timer);
  }, [toast, setToast]);

  useEffect(() => {
    if (interactionMode !== "add_origin_pending") {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") {
        return;
      }
      setInteractionMode("inspect");
      setCursorPosition(null);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [interactionMode, setCursorPosition, setInteractionMode]);

  useEffect(() => {
    if (interactionMode !== "add_origin_pending" || onboardingOpen) {
      return;
    }

    const onPointerMove = (event: PointerEvent) => {
      if (event.pointerType === "touch") {
        setCursorPosition(null);
        return;
      }
      setCursorPosition({ x: event.clientX, y: event.clientY });
    };
    const onWindowBlur = () => {
      setCursorPosition(null);
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerdown", onPointerMove);
    window.addEventListener("blur", onWindowBlur);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", onPointerMove);
      window.removeEventListener("blur", onWindowBlur);
    };
  }, [interactionMode, onboardingOpen, setCursorPosition]);

  useEffect(() => {
    if (!onboardingOpen && origins.length < MAX_ORIGINS) {
      return;
    }
    setInteractionMode("inspect");
    setCursorPosition(null);
  }, [onboardingOpen, origins.length, setCursorPosition, setInteractionMode]);
}
