import { useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from "react";

import { fetchReverseGeocode, type MultiPathItemResponse } from "@/lib/api";
import type { InspectCardState, OriginPoint } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type SetState<T> = Dispatch<SetStateAction<T>>;

type UseHeatmapInspectEffectsArgs = {
  inspectCard: InspectCardState | null;
  activeCityId: string | null;
  metadataLoading: boolean;
  originsRef: MutableRefObject<OriginPoint[]>;
  pathRequestSeqRef: MutableRefObject<number>;
  inspectAddressRequestSeqRef: MutableRefObject<number>;
  inspectAddressAbortControllerRef: MutableRefObject<AbortController | null>;
  runMultiPathQuery: (originsSnapshot: OriginPoint[], toLat: number, toLon: number) => Promise<void>;
  setPathLoading: SetState<boolean>;
  setPathError: SetState<string | null>;
  setPathByOriginId: SetState<Record<string, MultiPathItemResponse | null>>;
  setInspectAddressLabel: SetState<string | null>;
};

export function useHeatmapInspectEffects({
  inspectCard,
  activeCityId,
  metadataLoading,
  originsRef,
  pathRequestSeqRef,
  inspectAddressRequestSeqRef,
  inspectAddressAbortControllerRef,
  runMultiPathQuery,
  setPathLoading,
  setPathError,
  setPathByOriginId,
  setInspectAddressLabel
}: UseHeatmapInspectEffectsArgs) {
  const { messages } = useI18n();

  useEffect(() => {
    if (!inspectCard) {
      pathRequestSeqRef.current += 1;
      setPathLoading(false);
      setPathError(null);
      setPathByOriginId({});
      return;
    }

    if (metadataLoading) {
      return;
    }

    if (!activeCityId) {
      setPathLoading(false);
      setPathError(null);
      setPathByOriginId({});
      return;
    }

    const currentOrigins = originsRef.current;
    if (currentOrigins.length === 0) {
      setPathLoading(false);
      setPathError(null);
      setPathByOriginId({});
      return;
    }

    void runMultiPathQuery(currentOrigins, inspectCard.lat, inspectCard.lon);
    // Intentionally only tied to selected destination changes
    // Origin add/remove actions clear stale path state and wait for next click.
  }, [
    activeCityId,
    inspectCard,
    metadataLoading,
    pathRequestSeqRef,
    runMultiPathQuery,
    originsRef,
    setPathError,
    setPathByOriginId,
    setPathLoading
  ]);

  useEffect(() => {
    if (!inspectCard) {
      inspectAddressAbortControllerRef.current?.abort();
      inspectAddressAbortControllerRef.current = null;
      inspectAddressRequestSeqRef.current += 1;
      setInspectAddressLabel(null);
      return;
    }
    if (!activeCityId) {
      inspectAddressAbortControllerRef.current?.abort();
      inspectAddressAbortControllerRef.current = null;
      inspectAddressRequestSeqRef.current += 1;
      setInspectAddressLabel(null);
      return;
    }

    const requestSeq = inspectAddressRequestSeqRef.current + 1;
    inspectAddressRequestSeqRef.current = requestSeq;
    setInspectAddressLabel(messages.status.loadingAddress);

    const controller = new AbortController();
    inspectAddressAbortControllerRef.current = controller;

    void (async () => {
      try {
        const label = await fetchReverseGeocode(activeCityId, inspectCard.lat, inspectCard.lon, controller.signal);
        if (inspectAddressRequestSeqRef.current !== requestSeq || controller.signal.aborted) {
          return;
        }
        if (label) {
          setInspectAddressLabel(label);
        }
      } catch (error) {
        if (inspectAddressRequestSeqRef.current !== requestSeq || controller.signal.aborted) {
          return;
        }
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
      } finally {
        if (inspectAddressAbortControllerRef.current === controller) {
          inspectAddressAbortControllerRef.current = null;
        }
      }
    })();

    return () => {
      controller.abort();
      if (inspectAddressAbortControllerRef.current === controller) {
        inspectAddressAbortControllerRef.current = null;
      }
    };
  }, [
    activeCityId,
    inspectCard,
    inspectAddressAbortControllerRef,
    inspectAddressRequestSeqRef,
    messages.status.loadingAddress,
    setInspectAddressLabel
  ]);
}
