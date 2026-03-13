import { useCallback, useRef, type Dispatch, type SetStateAction } from "react";

import {
  fetchMultiPath,
  fetchMultiIsochrones,
  type MultiIsochroneResponse,
  type MultiOrigin,
  type MultiPathItemResponse
} from "@/lib/api";
import { findBestMeetingInspectCard } from "@/components/heatmap/meetingPoint";
import type { OriginPoint, ToastState } from "@/components/heatmap/types";
import { useI18n } from "@/i18n/useI18n";

type SetState<T> = Dispatch<SetStateAction<T>>;

type UseHeatmapQueriesArgs = {
  activeCityId: string | null;
  setData: SetState<MultiIsochroneResponse | null>;
  setLoading: SetState<boolean>;
  setError: SetState<string | null>;
  setToast: SetState<ToastState | null>;
  setInspectCard: SetState<{
    lat: number;
    lon: number;
    minS: number | null;
    maxS: number | null;
  } | null>;
  setPathLoading: SetState<boolean>;
  setPathError: SetState<string | null>;
  setPathByOriginId: SetState<Record<string, MultiPathItemResponse | null>>;
};

function toApiOrigins(origins: OriginPoint[]): MultiOrigin[] {
  return origins.map((origin) => ({
    id: origin.id,
    lat: origin.lat,
    lon: origin.lon
  }));
}

export function useHeatmapQueries({
  activeCityId,
  setData,
  setLoading,
  setError,
  setToast,
  setInspectCard,
  setPathLoading,
  setPathError,
  setPathByOriginId
}: UseHeatmapQueriesArgs) {
  const { messages } = useI18n();
  const pathRequestSeqRef = useRef(0);
  const isochroneRequestSeqRef = useRef(0);

  const clearPathState = useCallback(() => {
    pathRequestSeqRef.current += 1;
    setPathLoading(false);
    setPathError(null);
    setPathByOriginId({});
  }, [setPathByOriginId, setPathError, setPathLoading]);

  const runMultiIsochroneQuery = useCallback(async (
    originsSnapshot: OriginPoint[]
  ): Promise<MultiIsochroneResponse | null> => {
    const requestSeq = isochroneRequestSeqRef.current + 1;
    isochroneRequestSeqRef.current = requestSeq;

    if (originsSnapshot.length === 0) {
      setData(null);
      setLoading(false);
      setError(null);
      return null;
    }
    if (!activeCityId) {
      setLoading(false);
      return null;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await fetchMultiIsochrones(activeCityId, toApiOrigins(originsSnapshot));
      if (isochroneRequestSeqRef.current !== requestSeq) {
        return null;
      }
      setData(response);
      setInspectCard(findBestMeetingInspectCard(response));
      return response;
    } catch (err) {
      if (isochroneRequestSeqRef.current !== requestSeq) {
        return null;
      }
      const message = err instanceof Error ? err.message : messages.errors.unknownError;
      setError(message);
      setToast({ kind: "error", text: messages.toasts.failedToFetchIsochrones });
      return null;
    } finally {
      if (isochroneRequestSeqRef.current === requestSeq) {
        setLoading(false);
      }
    }
  }, [
    activeCityId,
    messages.errors.unknownError,
    messages.toasts.failedToFetchIsochrones,
    setData,
    setError,
    setInspectCard,
    setLoading,
    setToast
  ]);

  const runMultiPathQuery = useCallback(async (originsSnapshot: OriginPoint[], toLat: number, toLon: number) => {
    const requestSeq = pathRequestSeqRef.current + 1;
    pathRequestSeqRef.current = requestSeq;
    setPathLoading(true);
    setPathError(null);
    setPathByOriginId({});
    if (!activeCityId) {
      setPathLoading(false);
      return;
    }

    try {
      const response = await fetchMultiPath(activeCityId, toApiOrigins(originsSnapshot), toLat, toLon);
      if (pathRequestSeqRef.current !== requestSeq) {
        return;
      }

      const byOriginId: Record<string, MultiPathItemResponse | null> = {};
      for (const origin of originsSnapshot) {
        byOriginId[origin.id] = null;
      }
      for (const pathItem of response.paths) {
        byOriginId[pathItem.origin_id] = pathItem;
      }
      setPathByOriginId(byOriginId);
    } catch (err) {
      if (pathRequestSeqRef.current !== requestSeq) {
        return;
      }
      const message = err instanceof Error ? err.message : messages.errors.unknownError;
      setPathError(message);
    } finally {
      if (pathRequestSeqRef.current === requestSeq) {
        setPathLoading(false);
      }
    }
  }, [activeCityId, messages.errors.unknownError, setPathByOriginId, setPathError, setPathLoading]);

  return {
    pathRequestSeqRef,
    isochroneRequestSeqRef,
    clearPathState,
    runMultiIsochroneQuery,
    runMultiPathQuery
  };
}
