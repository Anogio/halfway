import { useEffect, useRef, type Dispatch, type SetStateAction } from "react";

import { fetchMetadata, type CityMetadata } from "@/lib/api";
import { getCityPresetFromQuery } from "@/components/heatmap/queryParams";
import { useI18n } from "@/i18n/useI18n";

type SetState<T> = Dispatch<SetStateAction<T>>;

const PREFERRED_CITY_ORDER = ["paris_fr", "grenoble_fr", "london_uk", "madrid_es"] as const;

function toNumberTuple3(value: readonly unknown[], field: string): [number, number, number] {
  if (value.length !== 3) {
    throw new Error(`${field} must contain exactly 3 numbers`);
  }

  const tuple: [number, number, number] = [Number(value[0]), Number(value[1]), Number(value[2])];
  if (tuple.some((item) => !Number.isFinite(item))) {
    throw new Error(`${field} must contain only finite numbers`);
  }

  return tuple;
}

function toNumberTuple4(value: readonly unknown[], field: string): [number, number, number, number] {
  if (value.length !== 4) {
    throw new Error(`${field} must contain exactly 4 numbers`);
  }

  const tuple: [number, number, number, number] = [
    Number(value[0]),
    Number(value[1]),
    Number(value[2]),
    Number(value[3])
  ];
  if (tuple.some((item) => !Number.isFinite(item))) {
    throw new Error(`${field} must contain only finite numbers`);
  }

  return tuple;
}

function compareCityOrder(left: CityMetadata, right: CityMetadata): number {
  const leftIndex = PREFERRED_CITY_ORDER.indexOf(left.id as (typeof PREFERRED_CITY_ORDER)[number]);
  const rightIndex = PREFERRED_CITY_ORDER.indexOf(right.id as (typeof PREFERRED_CITY_ORDER)[number]);

  if (leftIndex !== -1 || rightIndex !== -1) {
    if (leftIndex === -1) {
      return 1;
    }
    if (rightIndex === -1) {
      return -1;
    }
    return leftIndex - rightIndex;
  }

  return left.id.localeCompare(right.id);
}

type UseHeatmapMetadataEffectArgs = {
  setCities: SetState<CityMetadata[]>;
  setActiveCityId: SetState<string | null>;
  setDefaultView: SetState<[number, number, number] | null>;
  setMapBbox: SetState<[number, number, number, number] | null>;
  setMetadataLoading: SetState<boolean>;
  setError: SetState<string | null>;
};

export function useHeatmapMetadataEffect({
  setCities,
  setActiveCityId,
  setDefaultView,
  setMapBbox,
  setMetadataLoading,
  setError
}: UseHeatmapMetadataEffectArgs) {
  const { messages } = useI18n();
  const errorsRef = useRef(messages.errors);

  useEffect(() => {
    errorsRef.current = messages.errors;
  }, [messages.errors]);

  useEffect(() => {
    let active = true;

    async function loadMetadata() {
      try {
        const metadata = await fetchMetadata();
        if (!active) {
          return;
        }

        if (!Array.isArray(metadata.cities) || metadata.cities.length === 0) {
          throw new Error("No cities available in backend metadata");
        }

        const cities: CityMetadata[] = metadata.cities
          .map((city): CityMetadata => ({
            ...city,
            country_code: String(city.country_code).trim().toLowerCase(),
            default_view: toNumberTuple3(city.default_view, `default_view for city ${city.id}`),
            bbox: toNumberTuple4(city.bbox, `bbox for city ${city.id}`)
          }))
          .sort(compareCityOrder);
        setCities(cities);

        const presetCityId = getCityPresetFromQuery();
        const presetCity = presetCityId ? cities.find((city) => city.id === presetCityId) ?? null : null;
        if (presetCity) {
          setActiveCityId(presetCity.id);
          setDefaultView([
            Number(presetCity.default_view[0]),
            Number(presetCity.default_view[1]),
            Number(presetCity.default_view[2])
          ]);
          setMapBbox([
            Number(presetCity.bbox[0]),
            Number(presetCity.bbox[1]),
            Number(presetCity.bbox[2]),
            Number(presetCity.bbox[3])
          ]);
        } else {
          setActiveCityId(null);
          setDefaultView(null);
          setMapBbox(null);
        }
      } catch (err) {
        if (!active) {
          return;
        }
        const message = err instanceof Error ? err.message : errorsRef.current.unknownError;
        setError(errorsRef.current.metadataLoadFailed(message));
        setCities([]);
        setActiveCityId(null);
        setDefaultView(null);
        setMapBbox(null);
      } finally {
        if (active) {
          setMetadataLoading(false);
        }
      }
    }

    void loadMetadata();
    return () => {
      active = false;
    };
  }, [
    messages.errors,
    setActiveCityId,
    setCities,
    setDefaultView,
    setError,
    setMapBbox,
    setMetadataLoading
  ]);
}
